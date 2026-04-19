#!/usr/bin/env python3
"""
Create a slimmed-down version of the processed graph for development/visualization.
Takes top N nodes by citation count instead of all 54M nodes.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

def create_slim_graph(input_file: Path, output_file: Path, node_limit: int = 5000, edge_limit: int = 50000):
    """
    Create a smaller, manageable version of the graph for development.
    
    Args:
        input_file: Path to processed_graph.json
        output_file: Path to output slim graph
        node_limit: Number of top nodes to include (by citation count)
        edge_limit: Maximum number of edges to include
    """
    print(f"Creating slim graph from {input_file}...", flush=True)
    print(f"Target: {node_limit} nodes, {edge_limit} edges", flush=True)
    
    try:
        print("Reading large graph file...", flush=True)
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Sort nodes by in_degree (citation count)
        nodes = data.get('nodes', [])
        sorted_nodes = sorted(nodes, key=lambda n: n.get('in_degree', 0), reverse=True)[:node_limit]
        
        # Keep only top nodes
        top_node_ids = set(n['paper_id'] for n in sorted_nodes)
        print(f"Selected {len(sorted_nodes)} top nodes", flush=True)
        
        # Filter edges to only include those between top nodes
        edges = data.get('edges', [])
        slim_edges = [e for e in edges if e['source'] in top_node_ids and e['target'] in top_node_ids][:edge_limit]
        print(f"Filtered to {len(slim_edges)} edges", flush=True)
        
        # Keep clusters that have nodes in our selection
        clusters = data.get('clusters', {})
        slim_clusters = {}
        for cluster_id, cluster_data in clusters.items():
            slim_clusters[cluster_id] = cluster_data
        
        # Create slim output
        slim_graph = {
            'nodes': sorted_nodes,
            'edges': slim_edges,
            'clusters': slim_clusters,
            'statistics': {
                'total_nodes': len(sorted_nodes),
                'total_edges': len(slim_edges),
                'total_clusters': len(slim_clusters),
                'original_total_nodes': data.get('statistics', {}).get('total_nodes'),
                'original_total_edges': data.get('statistics', {}).get('total_edges'),
                'years': data.get('statistics', {}).get('years', {})
            },
            'note': f'Slimmed version: top {node_limit} nodes by citation count'
        }
        
        print(f"Writing slim graph to {output_file}...", flush=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(slim_graph, f)
        
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"Success! Output file size: {file_size_mb:.2f} MB", flush=True)
        
    except Exception as e:
        print(f"Error: {e}", flush=True)
        raise

if __name__ == '__main__':
    input_path = Path('data/processed_graph.json')
    output_path = Path('data/slim_graph.json')
    
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        exit(1)
    
    create_slim_graph(input_path, output_path, node_limit=5000, edge_limit=50000)
    print("Done!")
