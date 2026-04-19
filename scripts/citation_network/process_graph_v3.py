#!/usr/bin/env python3
"""
Ultra-lightweight process that handles massive datasets by:
- Processing nodes in small chunks (50k at a time)
- Writing output incrementally to disk
- Avoiding NetworkX community detection (memory killer)
- Using simple degree-based clustering instead
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, Iterator, Tuple
import sys
import gc

def stream_nodes_chunked(nodes_file: Path, chunk_size: int = 50000) -> Iterator[list]:
    """Stream nodes in chunks to control memory usage."""
    print(f"Loading nodes in chunks of {chunk_size}...", file=sys.stderr)
    
    chunk = []
    with open(nodes_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                node = json.loads(line.strip())
                paper_id = node.get('paper_id')
                if paper_id:
                    chunk.append((paper_id, node))
                
                if len(chunk) >= chunk_size:
                    yield chunk
                    print(f"Processed {i + 1} nodes...", file=sys.stderr)
                    chunk = []
                    gc.collect()
            except json.JSONDecodeError as e:
                print(f"Error parsing node at line {i + 1}: {e}", file=sys.stderr)
    
    if chunk:
        yield chunk


def count_edges_streaming(edges_file: Path) -> Tuple[Dict[str, int], Dict[str, int], int]:
    """Count in/out degrees without loading full graph."""
    print("Calculating edge metrics...", file=sys.stderr)
    
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)
    edge_count = 0
    
    with open(edges_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                edge = json.loads(line.strip())
                source = edge.get('source')
                target = edge.get('target')
                if source and target:
                    out_degree[source] += 1
                    in_degree[target] += 1
                    edge_count += 1
                
                if (i + 1) % 500000 == 0:
                    print(f"Counted {i + 1} edges...", file=sys.stderr)
            except json.JSONDecodeError as e:
                print(f"Error parsing edge at line {i + 1}: {e}", file=sys.stderr)
    
    print(f"Total edges: {edge_count}", file=sys.stderr)
    return dict(in_degree), dict(out_degree), edge_count


def assign_clusters_by_degree(in_degrees: Dict[str, int], out_degrees: Dict[str, int], num_clusters: int = 10) -> Dict[str, int]:
    """Assign clusters based on node degree."""
    print(f"Assigning nodes to {num_clusters} clusters by degree...", file=sys.stderr)

    # Pre-compute max values ONCE before the loop (not inside it)
    max_in = max(in_degrees.values(), default=1)
    max_out = max(out_degrees.values(), default=1)
    max_total = max(1, max_in + max_out)

    cluster_map = {}

    # Use set union instead of building two large intermediate lists
    all_nodes = set(in_degrees.keys()) | set(out_degrees.keys())
    total = len(all_nodes)
    print(f"Clustering {total:,} unique nodes...", file=sys.stderr)

    for i, node_id in enumerate(all_nodes):
        in_deg = in_degrees.get(node_id, 0)
        out_deg = out_degrees.get(node_id, 0)
        total_deg = in_deg + out_deg
        cluster_id = min(int(total_deg * num_clusters / max_total), num_clusters - 1)
        cluster_map[node_id] = cluster_id

        if (i + 1) % 1_000_000 == 0:
            print(f"  Clustered {i + 1:,} / {total:,} nodes...", file=sys.stderr)

    return cluster_map


def process_graph():
    """Main processing function."""
    data_dir = Path("public/data")
    nodes_file = data_dir / "nodes.jsonl"
    edges_file = data_dir / "edges.jsonl"
    
    if not nodes_file.exists() or not edges_file.exists():
        print(f"Error: {nodes_file} or {edges_file} not found", file=sys.stderr)
        sys.exit(1)
    
    # Step 1: Calculate metrics from edges
    in_degrees, out_degrees, edge_count = count_edges_streaming(edges_file)
    
    # Step 2: Assign clusters based on degree
    cluster_map = assign_clusters_by_degree(in_degrees, out_degrees)
    
    # Step 3: Build search index while processing nodes
    print("Building search index...", file=sys.stderr)
    search_index = defaultdict(set)
    
    # Step 4: Process nodes in chunks and write output
    output_file = data_dir / "processed_graph.json"
    output_dir = data_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing processed graph to {output_file}...", file=sys.stderr)
    
    total_nodes = 0
    min_year = 9999
    max_year = 1900
    
    # Open output file for streaming write
    with open(output_file, 'w', encoding='utf-8') as out_f:
        # Write opening
        out_f.write('{"nodes": [\n')
        
        first_node = True
        for node_chunk in stream_nodes_chunked(nodes_file):
            for paper_id, node in node_chunk:
                year = node.get('year')
                if year:
                    min_year = min(min_year, year)
                    max_year = max(max_year, year)
                
                # Build search index
                title = node.get('title', '').lower()
                if title:
                    for word in title.split():
                        if len(word) > 3:
                            search_index[word].add(paper_id)
                
                # Enrich node with metrics
                enriched_node = {
                    **node,
                    'cluster_id': cluster_map.get(paper_id, -1),
                    'in_degree': in_degrees.get(paper_id, 0),
                    'out_degree': out_degrees.get(paper_id, 0),
                }
                
                # Write node
                if not first_node:
                    out_f.write(',\n')
                json.dump(enriched_node, out_f)
                first_node = False
                
                total_nodes += 1
                if total_nodes % 100000 == 0:
                    print(f"Wrote {total_nodes} nodes...", file=sys.stderr)
            
            gc.collect()
        
        # Write edges — cap at MAX_OUTPUT_EDGES to keep output loadable in a browser.
        # Prioritise edges where both endpoints have high combined degree.
        MAX_OUTPUT_EDGES = 500_000
        print(f"Sampling up to {MAX_OUTPUT_EDGES:,} highest-degree edges for output...", file=sys.stderr)

        # Score every edge by combined degree of its endpoints, keep top N
        import heapq
        heap = []  # min-heap of (score, source, target)

        with open(edges_file, 'r', encoding='utf-8') as edges_f:
            for i, line in enumerate(edges_f):
                try:
                    edge = json.loads(line.strip())
                    source = edge.get('source')
                    target = edge.get('target')
                    if source and target:
                        score = in_degrees.get(source, 0) + out_degrees.get(source, 0) + \
                                in_degrees.get(target, 0) + out_degrees.get(target, 0)
                        if len(heap) < MAX_OUTPUT_EDGES:
                            heapq.heappush(heap, (score, source, target))
                        elif score > heap[0][0]:
                            heapq.heapreplace(heap, (score, source, target))
                    if (i + 1) % 10_000_000 == 0:
                        print(f"  Scored {i + 1:,} edges...", file=sys.stderr)
                except json.JSONDecodeError:
                    pass

        print(f"Writing {len(heap):,} sampled edges...", file=sys.stderr)
        out_f.write('\n], "edges": [\n')
        first_edge = True
        edge_num = 0
        for _score, source, target in heap:
            if not first_edge:
                out_f.write(',\n')
            json.dump({'source': source, 'target': target}, out_f)
            first_edge = False
            edge_num += 1
        
        # Calculate cluster info
        cluster_info = defaultdict(lambda: {'id': 0, 'size': 0})
        for node_id, cluster_id in cluster_map.items():
            cluster_info[cluster_id]['id'] = cluster_id
            cluster_info[cluster_id]['size'] += 1
        
        # Write closing
        cluster_info_final = {str(k): v for k, v in cluster_info.items()}
        out_f.write('\n], "clusters": ')
        json.dump(cluster_info_final, out_f)
        
        out_f.write(', "statistics": ')
        stats = {
            'total_nodes': total_nodes,
            'total_edges': edge_count,
            'total_clusters': len(cluster_info),
            'years': {
                'min': min_year if min_year != 9999 else 1900,
                'max': max_year if max_year != 1900 else 2024,
            }
        }
        json.dump(stats, out_f)
        out_f.write('}\n')
    
    # Write search index
    search_index_file = output_dir / "search_index.json"
    print(f"Writing search index...", file=sys.stderr)
    
    search_index_final = {word: list(paper_ids) for word, paper_ids in search_index.items()}
    with open(search_index_file, 'w', encoding='utf-8') as f:
        json.dump(search_index_final, f)
    
    print(f"\nProcessing complete!", file=sys.stderr)
    print(f"Total nodes: {total_nodes}", file=sys.stderr)
    print(f"Total edges: {edge_count}", file=sys.stderr)
    print(f"Total clusters: {len(cluster_info)}", file=sys.stderr)
    print(f"Output: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    process_graph()
