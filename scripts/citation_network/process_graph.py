#!/usr/bin/env python3
"""
Process the extracted citation network graph.
- Calculate citation metrics
- Run community detection
- Build search index
- Output optimized graph JSON
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Set
import sys

try:
    import networkx as nx
    from networkx.algorithms.community import greedy_modularity_communities
except ImportError:
    print("Installing networkx...", file=sys.stderr)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "networkx"])
    import networkx as nx
    from networkx.algorithms.community import greedy_modularity_communities


def load_nodes(nodes_file: Path) -> Dict[str, dict]:
    """Load nodes from JSONL file."""
    nodes = {}
    print(f"Loading nodes from {nodes_file}...", file=sys.stderr)
    
    with open(nodes_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                node = json.loads(line.strip())
                paper_id = node.get('paper_id')
                if paper_id:
                    nodes[paper_id] = node
                
                if (i + 1) % 100000 == 0:
                    print(f"Loaded {i + 1} nodes...", file=sys.stderr)
            except json.JSONDecodeError as e:
                print(f"Error parsing node at line {i + 1}: {e}", file=sys.stderr)
    
    print(f"Total nodes loaded: {len(nodes)}", file=sys.stderr)
    return nodes


def load_edges(edges_file: Path) -> List[tuple]:
    """Load edges from JSONL file."""
    edges = []
    print(f"Loading edges from {edges_file}...", file=sys.stderr)
    
    with open(edges_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                edge_data = json.loads(line.strip())
                source = edge_data.get('source')
                target = edge_data.get('target')
                if source and target:
                    edges.append((source, target))
                
                if (i + 1) % 100000 == 0:
                    print(f"Loaded {i + 1} edges...", file=sys.stderr)
            except json.JSONDecodeError as e:
                print(f"Error parsing edge at line {i + 1}: {e}", file=sys.stderr)
    
    print(f"Total edges loaded: {len(edges)}", file=sys.stderr)
    return edges


def build_graph(nodes: Dict[str, dict], edges: List[tuple]) -> nx.DiGraph:
    """Build NetworkX graph."""
    print("Building graph...", file=sys.stderr)
    
    G = nx.DiGraph()
    
    # Add nodes
    for paper_id in nodes.keys():
        G.add_node(paper_id)
    
    # Add edges (only if both source and target exist)
    valid_edges = 0
    for source, target in edges:
        if source in nodes and target in nodes:
            G.add_edge(source, target)
            valid_edges += 1
    
    print(f"Graph built: {G.number_of_nodes()} nodes, {valid_edges} edges", file=sys.stderr)
    return G


def detect_communities(G: nx.DiGraph) -> Dict[str, int]:
    """
    Detect communities using Louvain algorithm.
    Returns mapping of paper_id to cluster_id.
    """
    print("Detecting communities...", file=sys.stderr)
    
    # Convert to undirected for community detection
    G_undirected = G.to_undirected()
    
    # Use greedy modularity communities
    communities = list(greedy_modularity_communities(G_undirected))
    
    cluster_map = {}
    for cluster_id, community in enumerate(communities):
        for paper_id in community:
            cluster_map[paper_id] = cluster_id
    
    print(f"Found {len(communities)} communities", file=sys.stderr)
    for i, community in enumerate(communities):
        print(f"  Community {i}: {len(community)} papers", file=sys.stderr)
    
    return cluster_map


def calculate_metrics(nodes: Dict[str, dict], G: nx.DiGraph) -> Dict[str, dict]:
    """Calculate citation metrics for each node."""
    print("Calculating metrics...", file=sys.stderr)
    
    metrics = {}
    
    # Calculate in-degree and out-degree
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())
    
    for paper_id in nodes.keys():
        metrics[paper_id] = {
            'in_degree': in_degrees.get(paper_id, 0),
            'out_degree': out_degrees.get(paper_id, 0),
        }
    
    return metrics


def build_search_index(nodes: Dict[str, dict]) -> Dict[str, List[str]]:
    """
    Build a searchable index for titles, abstracts, keywords, and authors.
    """
    print("Building search index...", file=sys.stderr)
    
    index = {}
    
    for paper_id, paper in nodes.items():
        # Index title
        title = paper.get('title', '').lower()
        if title:
            for word in title.split():
                if len(word) > 2:  # Skip very short words
                    if word not in index:
                        index[word] = []
                    if paper_id not in index[word]:
                        index[word].append(paper_id)
        
        # Index abstract
        abstract = paper.get('abstract', '').lower()
        if abstract:
            for word in abstract.split():
                if len(word) > 3 and word.isalpha():  # Skip short words and non-alpha
                    if word not in index:
                        index[word] = []
                    if paper_id not in index[word]:
                        index[word].append(paper_id)
        
        # Index keywords
        keywords = paper.get('keywords', [])
        if keywords:
            for keyword in keywords:
                kw_lower = keyword.lower()
                for word in kw_lower.split():
                    if word:
                        if word not in index:
                            index[word] = []
                        if paper_id not in index[word]:
                            index[word].append(paper_id)
        
        # Index author names
        authors = paper.get('authors', [])
        if authors:
            for author in authors:
                # We'll index by author_id
                author_id = author.get('author_id', '')
                if author_id:
                    if author_id not in index:
                        index[author_id] = []
                    if paper_id not in index[author_id]:
                        index[author_id].append(paper_id)
    
    print(f"Search index built with {len(index)} terms", file=sys.stderr)
    return index


def process_graph():
    """Main processing function."""
    data_dir = Path("public/data")
    nodes_file = data_dir / "nodes.jsonl"
    edges_file = data_dir / "edges.jsonl"
    
    if not nodes_file.exists() or not edges_file.exists():
        print(f"Error: Extraction files not found. Run extraction first.", file=sys.stderr)
        sys.exit(1)
    
    # Load data
    nodes = load_nodes(nodes_file)
    edges = load_edges(edges_file)
    
    # Build graph
    G = build_graph(nodes, edges)
    
    # Detect communities
    cluster_map = detect_communities(G)
    
    # Calculate metrics
    metrics = calculate_metrics(nodes, G)
    
    # Build search index
    search_index = build_search_index(nodes)
    
    # Enrich nodes with metrics and clusters
    print("Enriching nodes with metrics and clusters...", file=sys.stderr)
    processed_nodes = []
    
    for paper_id, node in nodes.items():
        enriched_node = {
            **node,
            'cluster_id': cluster_map.get(paper_id, -1),
            'in_degree': metrics[paper_id]['in_degree'],
            'out_degree': metrics[paper_id]['out_degree'],
        }
        processed_nodes.append(enriched_node)
    
    # Build edges list
    edges_list = []
    for source, target in edges:
        if source in nodes and target in nodes:
            edges_list.append({
                'source': source,
                'target': target
            })
    
    # Create cluster info
    cluster_info = {}
    field_to_cluster = defaultdict(set)
    
    for paper_id, node in nodes.items():
        cluster_id = cluster_map.get(paper_id, -1)
        field = node.get('field_of_study', 'Unknown')
        field_to_cluster[field].add(cluster_id)
        
        if cluster_id not in cluster_info:
            cluster_info[cluster_id] = {
                'id': cluster_id,
                'size': 0,
                'fields': []
            }
        cluster_info[cluster_id]['size'] += 1
    
    for cluster_id in cluster_info:
        fields = list(field_to_cluster.keys())
        cluster_info[cluster_id]['fields'] = [
            f for f in fields 
            if cluster_id in field_to_cluster[f]
        ]
    
    # Output processed graph
    output_file = Path("public/data/processed_graph.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing processed graph to {output_file}...", file=sys.stderr)
    
    processed_graph = {
        'nodes': processed_nodes,
        'edges': edges_list,
        'clusters': dict(cluster_info),
        'statistics': {
            'total_nodes': len(nodes),
            'total_edges': len(edges_list),
            'total_clusters': len(cluster_info),
            'years': {
                'min': min((n.get('year') for n in nodes.values() if n.get('year')), default=1900),
                'max': max((n.get('year') for n in nodes.values() if n.get('year')), default=2024),
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
        'nodes': len(processed_nodes),
        'edges': len(edges_list),
        'clusters': len(cluster_info),
        'output_file': str(output_file),
    }


if __name__ == '__main__':
    result = process_graph()
    print(json.dumps(result))
