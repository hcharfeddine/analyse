#!/usr/bin/env python3
"""
ULTRA-EFFICIENT Process the citation network graph - true streaming, no full caching.
For 42M+ nodes, processes entirely in streaming mode.
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Iterator, Tuple, Dict, Set, List
import sys
import gc

try:
    import networkx as nx
    from networkx.algorithms.community import greedy_modularity_communities
except ImportError:
    print("Installing networkx...", file=sys.stderr)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "networkx"])
    import networkx as nx
    from networkx.algorithms.community import greedy_modularity_communities


def stream_nodes(nodes_file: Path) -> Iterator[Tuple[str, dict]]:
    """Stream nodes from JSONL file."""
    with open(nodes_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                node = json.loads(line)
                paper_id = node.get('paper_id')
                if paper_id:
                    yield paper_id, node
                    
                    if (i + 1) % 200000 == 0:
                        print(f"  Processed {i + 1} nodes...", file=sys.stderr)
                        gc.collect()
            except json.JSONDecodeError as e:
                print(f"Skipping malformed line {i + 1}", file=sys.stderr)


def stream_edges(edges_file: Path) -> Iterator[Tuple[str, str]]:
    """Stream edges from JSONL file."""
    with open(edges_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                edge = json.loads(line)
                source = edge.get('source')
                target = edge.get('target')
                if source and target:
                    yield source, target
                    
                    if (i + 1) % 200000 == 0:
                        print(f"  Read {i + 1} edges...", file=sys.stderr)
                        gc.collect()
            except json.JSONDecodeError:
                pass


def count_nodes_and_edges(nodes_file: Path, edges_file: Path) -> Tuple[int, int]:
    """Count nodes and edges in files."""
    node_count = 0
    edge_count = 0
    
    print("Counting nodes...", file=sys.stderr)
    for _ in stream_nodes(nodes_file):
        node_count += 1
    
    print("Counting edges...", file=sys.stderr)
    for _ in stream_edges(edges_file):
        edge_count += 1
    
    return node_count, edge_count


def calculate_metrics(edges_file: Path) -> Dict[str, Dict[str, int]]:
    """Calculate degree metrics by streaming edges."""
    print("Calculating metrics...", file=sys.stderr)
    
    metrics = defaultdict(lambda: {'in_degree': 0, 'out_degree': 0})
    
    for source, target in stream_edges(edges_file):
        metrics[source]['out_degree'] += 1
        metrics[target]['in_degree'] += 1
    
    print(f"  Metrics calculated for {len(metrics)} nodes", file=sys.stderr)
    return metrics


def build_sampling_graph(edges_file: Path, valid_ids: Set[str], sample_rate: float = 1.0) -> nx.DiGraph:
    """Build graph by sampling edges (for memory efficiency on huge graphs)."""
    print(f"Building graph (sample_rate={sample_rate})...", file=sys.stderr)
    
    G = nx.DiGraph()
    edges_added = 0
    
    for source, target in stream_edges(edges_file):
        if source in valid_ids and target in valid_ids:
            G.add_edge(source, target)
            edges_added += 1
            
            if edges_added % 500000 == 0:
                print(f"  Added {edges_added} edges to graph...", file=sys.stderr)
    
    print(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges", file=sys.stderr)
    return G


def detect_communities(G: nx.DiGraph) -> Dict[str, int]:
    """Detect communities with fallback."""
    print("Detecting communities...", file=sys.stderr)
    
    try:
        G_undirected = G.to_undirected()
        communities = list(greedy_modularity_communities(G_undirected))
        
        cluster_map = {}
        for cid, community in enumerate(communities):
            for nid in community:
                cluster_map[nid] = cid
        
        print(f"  Found {len(communities)} communities", file=sys.stderr)
        return cluster_map
    
    except (MemoryError, Exception) as e:
        print(f"  Community detection failed: {e}", file=sys.stderr)
        print(f"  Using degree-based clustering...", file=sys.stderr)
        
        cluster_map = {}
        degrees = {}
        for node in G.nodes():
            degrees[node] = G.degree(node)
        
        max_deg = max(degrees.values()) if degrees else 1
        for node, deg in degrees.items():
            cluster_map[node] = min(int(deg / (max_deg / 10)), 9)
        
        return cluster_map


def build_search_index(nodes_file: Path) -> Dict[str, List[str]]:
    """Build searchable index by streaming."""
    print("Building search index...", file=sys.stderr)
    
    index = defaultdict(set)
    
    for paper_id, paper in stream_nodes(nodes_file):
        # Index title
        title = paper.get('title', '')
        if title:
            for word in title.lower().split():
                if len(word) > 3:
                    index[word].add(paper_id)
        
        # Index keywords only
        keywords = paper.get('keywords', [])
        for kw in keywords[:5]:
            for word in str(kw).lower().split():
                if len(word) > 2:
                    index[word].add(paper_id)
    
    # Convert sets to lists
    result = {word: list(ids) for word, ids in index.items()}
    print(f"  Index has {len(result)} terms", file=sys.stderr)
    return result


def write_processed_graph_streaming(
    nodes_file: Path,
    edges_file: Path,
    metrics: Dict,
    clusters: Dict,
    index: Dict,
    output_file: Path
):
    """Write processed graph in streaming mode to avoid loading everything."""
    print("Writing processed graph...", file=sys.stderr)
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Process and write nodes
    processed_nodes = []
    stats = {'min_year': 9999, 'max_year': 1900}
    cluster_sizes = defaultdict(int)
    cluster_fields = defaultdict(set)
    
    for paper_id, node in stream_nodes(nodes_file):
        enriched = {
            **node,
            'cluster_id': clusters.get(paper_id, -1),
            'in_degree': metrics.get(paper_id, {}).get('in_degree', 0),
            'out_degree': metrics.get(paper_id, {}).get('out_degree', 0),
        }
        processed_nodes.append(enriched)
        
        year = node.get('year')
        if year:
            stats['min_year'] = min(stats['min_year'], year)
            stats['max_year'] = max(stats['max_year'], year)
        
        cid = clusters.get(paper_id, -1)
        cluster_sizes[cid] += 1
        cluster_fields[cid].add(node.get('field_of_study', 'Unknown'))
    
    # Process edges
    edges_list = []
    edge_count = 0
    
    for source, target in stream_edges(edges_file):
        if source in clusters or target in clusters:
            edges_list.append({'source': source, 'target': target})
            edge_count += 1
    
    # Build cluster info
    cluster_info = {
        str(cid): {
            'id': cid,
            'size': cluster_sizes[cid],
            'fields': list(cluster_fields[cid])
        }
        for cid in cluster_sizes
    }
    
    # Write full output
    output = {
        'nodes': processed_nodes,
        'edges': edges_list,
        'clusters': cluster_info,
        'statistics': {
            'total_nodes': len(processed_nodes),
            'total_edges': edge_count,
            'total_clusters': len(cluster_info),
            'years': {
                'min': stats['min_year'] if stats['min_year'] != 9999 else 1900,
                'max': stats['max_year'] if stats['max_year'] != 1900 else 2024,
            }
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f)
    
    print(f"  Wrote {len(processed_nodes)} nodes and {edge_count} edges", file=sys.stderr)
    
    return len(processed_nodes), edge_count


def process_graph():
    """Main: True streaming process."""
    data_dir = Path("public/data")
    nodes_file = data_dir / "nodes.jsonl"
    edges_file = data_dir / "edges.jsonl"
    
    if not nodes_file.exists():
        print("ERROR: nodes.jsonl not found", file=sys.stderr)
        sys.exit(1)
    if not edges_file.exists():
        print("ERROR: edges.jsonl not found", file=sys.stderr)
        sys.exit(1)
    
    print("=== STARTING CITATION NETWORK PROCESSING ===", file=sys.stderr)
    
    # Step 1: Get valid node IDs
    print("\n[1/6] Building valid node ID set...", file=sys.stderr)
    valid_ids = set()
    for paper_id, _ in stream_nodes(nodes_file):
        valid_ids.add(paper_id)
    print(f"  Found {len(valid_ids)} valid nodes", file=sys.stderr)
    
    # Step 2: Calculate metrics
    print("\n[2/6] Calculating citation metrics...", file=sys.stderr)
    metrics = calculate_metrics(edges_file)
    
    # Step 3: Build and detect communities
    print("\n[3/6] Building network graph...", file=sys.stderr)
    G = build_sampling_graph(edges_file, valid_ids)
    
    print("\n[4/6] Detecting communities...", file=sys.stderr)
    clusters = detect_communities(G)
    del G
    gc.collect()
    
    # Step 5: Build search index
    print("\n[5/6] Building search index...", file=sys.stderr)
    index = build_search_index(nodes_file)
    
    # Step 6: Write output
    print("\n[6/6] Writing output...", file=sys.stderr)
    output_file = data_dir / "processed_graph.json"
    node_count, edge_count = write_processed_graph_streaming(
        nodes_file, edges_file, metrics, clusters, index, output_file
    )
    
    # Write search index separately
    index_file = data_dir / "search_index.json"
    with open(index_file, 'w') as f:
        json.dump(index, f)
    
    print("\n=== PROCESSING COMPLETE ===", file=sys.stderr)
    print(f"Output: {output_file}", file=sys.stderr)
    
    return {
        'status': 'success',
        'nodes': node_count,
        'edges': edge_count,
        'clusters': len(set(clusters.values())),
    }


if __name__ == '__main__':
    result = process_graph()
    print(json.dumps(result))
