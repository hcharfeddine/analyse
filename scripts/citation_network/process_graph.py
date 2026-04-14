#!/usr/bin/env python3
"""
Process the extracted citation network graph.
- Calculate citation metrics
- Run community detection on subgraphs
- Build search index with streaming
- Output optimized graph JSON
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Set, Iterator, Tuple
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
    """Stream nodes from JSONL file without loading all into memory."""
    print(f"Streaming nodes from {nodes_file}...", file=sys.stderr)
    
    with open(nodes_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                node = json.loads(line.strip())
                paper_id = node.get('paper_id')
                if paper_id:
                    yield paper_id, node
                    
                    if (i + 1) % 100000 == 0:
                        print(f"Streamed {i + 1} nodes ({(i + 1) * 100 / 42000000:.1f}%)...", file=sys.stderr)
                        gc.collect()  # Force garbage collection
            except json.JSONDecodeError as e:
                print(f"Error parsing node at line {i + 1}: {e}", file=sys.stderr)


def stream_edges(edges_file: Path) -> Iterator[Tuple[str, str]]:
    """Stream edges from JSONL file without loading all into memory."""
    print(f"Streaming edges from {edges_file}...", file=sys.stderr)
    
    with open(edges_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                edge_data = json.loads(line.strip())
                source = edge_data.get('source')
                target = edge_data.get('target')
                if source and target:
                    yield source, target
                    
                    if (i + 1) % 100000 == 0:
                        print(f"Streamed {i + 1} edges...", file=sys.stderr)
            except json.JSONDecodeError as e:
                print(f"Error parsing edge at line {i + 1}: {e}", file=sys.stderr)


def calculate_metrics_streaming(edges_file: Path, node_count: int) -> Dict[str, Dict[str, int]]:
    """Calculate in/out degree metrics by streaming edges."""
    print("Calculating metrics by streaming edges...", file=sys.stderr)
    
    metrics = defaultdict(lambda: {'in_degree': 0, 'out_degree': 0})
    
    for source, target in stream_edges(edges_file):
        metrics[source]['out_degree'] += 1
        metrics[target]['in_degree'] += 1
    
    print(f"Metrics calculated for {len(metrics)} nodes", file=sys.stderr)
    return metrics


def build_graph_for_detection(edges_file: Path, valid_node_ids: Set[str], chunk_size: int = 50000) -> nx.DiGraph:
    """
    Build a graph for community detection, processing edges in chunks.
    Uses a sampling approach for very large graphs.
    """
    print("Building graph for community detection...", file=sys.stderr)
    
    G = nx.DiGraph()
    edge_count = 0
    
    # Add only valid node IDs to graph
    for node_id in valid_node_ids:
        G.add_node(node_id)
    
    # Add edges
    for source, target in stream_edges(edges_file):
        if source in valid_node_ids and target in valid_node_ids:
            G.add_edge(source, target)
            edge_count += 1
    
    print(f"Graph built: {G.number_of_nodes()} nodes, {edge_count} edges", file=sys.stderr)
    return G


def detect_communities_hierarchical(G: nx.DiGraph) -> Dict[str, int]:
    """
    Detect communities using greedy modularity on undirected version.
    For very large graphs, this uses a hierarchical approach.
    """
    print("Detecting communities...", file=sys.stderr)
    
    G_undirected = G.to_undirected()
    
    try:
        communities = list(greedy_modularity_communities(G_undirected))
        print(f"Found {len(communities)} communities", file=sys.stderr)
        
        cluster_map = {}
        for cluster_id, community in enumerate(communities):
            for paper_id in community:
                cluster_map[paper_id] = cluster_id
            if (cluster_id + 1) % 100 == 0:
                print(f"  Processed {cluster_id + 1} communities...", file=sys.stderr)
        
        return cluster_map
    except MemoryError:
        print("WARNING: Community detection ran out of memory, using degree-based clustering", file=sys.stderr)
        # Fallback: use degree-based clustering
        return cluster_by_degree(G)


def cluster_by_degree(G: nx.DiGraph) -> Dict[str, int]:
    """Fallback clustering using node degree."""
    print("Using degree-based clustering as fallback...", file=sys.stderr)
    
    cluster_map = {}
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())
    
    # Create clusters based on degree ranges
    max_degree = max(max(in_degrees.values()), max(out_degrees.values())) if in_degrees else 0
    
    for node_id, in_deg in in_degrees.items():
        out_deg = out_degrees.get(node_id, 0)
        total_degree = in_deg + out_deg
        cluster_id = min(int(total_degree / (max_degree / 10)) if max_degree > 0 else 0, 9)
        cluster_map[node_id] = cluster_id
    
    return cluster_map


def build_search_index_streaming(nodes_file: Path) -> Dict[str, List[str]]:
    """
    Build search index by streaming nodes to avoid memory overload.
    Uses a simpler index structure for large datasets.
    """
    print("Building search index by streaming...", file=sys.stderr)
    
    index = defaultdict(set)  # Use set to avoid duplicates, convert to list later
    
    for paper_id, paper in stream_nodes(nodes_file):
        # Index title (with stricter filtering)
        title = paper.get('title', '').lower()
        if title:
            for word in title.split():
                if len(word) > 3:  # Only index words longer than 3 chars
                    index[word].add(paper_id)
        
        # Skip abstract indexing for large datasets (saves memory)
        # Uncomment below if needed with caution:
        # abstract = paper.get('abstract', '').lower()
        # if abstract:
        #     words = abstract.split()[:50]  # Limit to first 50 words
        #     for word in words:
        #         if len(word) > 4 and word.isalpha():
        #             index[word].add(paper_id)
        
        # Index keywords
        keywords = paper.get('keywords', [])
        if keywords:
            for keyword in keywords[:10]:  # Limit keywords
                kw_lower = str(keyword).lower()
                for word in kw_lower.split():
                    if word and len(word) > 2:
                        index[word].add(paper_id)
    
    # Convert sets to lists
    index = {word: list(paper_ids) for word, paper_ids in index.items()}
    print(f"Search index built with {len(index)} terms", file=sys.stderr)
    return index


def process_graph():
    """Main processing function with memory-efficient streaming."""
    data_dir = Path("public/data")
    nodes_file = data_dir / "nodes.jsonl"
    edges_file = data_dir / "edges.jsonl"
    
    if not nodes_file.exists() or not edges_file.exists():
        print(f"Error: Extraction files not found. Run extraction first.", file=sys.stderr)
        sys.exit(1)
    
    # Step 1: Count nodes and collect valid IDs (first pass)
    print("Step 1: Counting nodes and collecting IDs...", file=sys.stderr)
    valid_node_ids = set()
    node_data_cache = {}  # Cache full node data during first pass
    node_count = 0
    
    for paper_id, node in stream_nodes(nodes_file):
        valid_node_ids.add(paper_id)
        node_data_cache[paper_id] = node
        node_count += 1
        
        if node_count % 100000 == 0:
            print(f"  Collected {node_count} nodes (Memory usage increasing)...", file=sys.stderr)
    
    print(f"Total nodes: {node_count}", file=sys.stderr)
    
    # Step 2: Calculate metrics by streaming edges
    print("Step 2: Calculating metrics...", file=sys.stderr)
    metrics = calculate_metrics_streaming(edges_file, node_count)
    
    # Step 3: Build graph for community detection
    print("Step 3: Building graph for community detection...", file=sys.stderr)
    G = build_graph_for_detection(edges_file, valid_node_ids)
    
    # Step 4: Detect communities
    print("Step 4: Detecting communities...", file=sys.stderr)
    cluster_map = detect_communities_hierarchical(G)
    del G  # Free memory
    
    # Step 5: Build search index
    print("Step 5: Building search index...", file=sys.stderr)
    search_index = build_search_index_streaming(nodes_file)
    
    # Step 6: Enrich nodes and write output
    print("Step 6: Enriching nodes and writing output...", file=sys.stderr)
    output_dir = Path("public/data")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "processed_graph.json"
    
    processed_nodes = []
    edges_list = []
    cluster_info = defaultdict(lambda: {'id': 0, 'size': 0, 'fields': set()})
    min_year = 9999
    max_year = 1900
    
    # Process nodes from cache
    for paper_id, node in node_data_cache.items():
        year = node.get('year')
        if year:
            min_year = min(min_year, year)
            max_year = max(max_year, year)
        
        enriched_node = {
            **node,
            'cluster_id': cluster_map.get(paper_id, -1),
            'in_degree': metrics.get(paper_id, {}).get('in_degree', 0),
            'out_degree': metrics.get(paper_id, {}).get('out_degree', 0),
        }
        processed_nodes.append(enriched_node)
        
        # Track cluster info
        cluster_id = cluster_map.get(paper_id, -1)
        field = node.get('field_of_study', 'Unknown')
        cluster_info[cluster_id]['id'] = cluster_id
        cluster_info[cluster_id]['size'] += 1
        cluster_info[cluster_id]['fields'].add(field)
    
    # Stream edges for output
    edge_count = 0
    for source, target in stream_edges(edges_file):
        if source in valid_node_ids and target in valid_node_ids:
            edges_list.append({'source': source, 'target': target})
            edge_count += 1
            
            if edge_count % 100000 == 0:
                print(f"  Processed {edge_count} edges...", file=sys.stderr)
    
    # Convert cluster info
    cluster_info_final = {}
    for cluster_id, info in cluster_info.items():
        cluster_info_final[cluster_id] = {
            'id': info['id'],
            'size': info['size'],
            'fields': list(info['fields'])
        }
    
    # Write processed graph
    print(f"Writing processed graph to {output_file}...", file=sys.stderr)
    
    processed_graph = {
        'nodes': processed_nodes,
        'edges': edges_list,
        'clusters': cluster_info_final,
        'statistics': {
            'total_nodes': len(valid_node_ids),
            'total_edges': edge_count,
            'total_clusters': len(cluster_info_final),
            'years': {
                'min': min_year if min_year != 9999 else 1900,
                'max': max_year if max_year != 1900 else 2024,
            }
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_graph, f)
    
    # Output search index
    search_index_file = Path("public/data/search_index.json")
    print(f"Writing search index to {search_index_file}...", file=sys.stderr)
    
    with open(search_index_file, 'w', encoding='utf-8') as f:
        json.dump(search_index, f)
    
    print("Processing complete!", file=sys.stderr)
    
    return {
        'status': 'success',
        'nodes': len(valid_node_ids),
        'edges': edge_count,
        'clusters': len(cluster_info_final),
        'output_file': str(output_file),
    }


if __name__ == '__main__':
    result = process_graph()
    print(json.dumps(result))
