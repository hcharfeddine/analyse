#!/usr/bin/env python3
"""
Optimize the processed graph for web visualization.
Converts the massive JSON into an indexed SQLite database for efficient querying.
"""

import json
import sqlite3
from pathlib import Path
import sys

def optimize_graph():
    """Convert JSON to SQLite for efficient querying."""
    data_dir = Path("public/data")
    json_file = data_dir / "processed_graph.json"
    db_file = data_dir / "graph.db"
    
    if not json_file.exists():
        print(f"Error: {json_file} not found", file=sys.stderr)
        sys.exit(1)
    
    print("Creating optimized database...", file=sys.stderr)
    
    # Create database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            paper_id TEXT PRIMARY KEY,
            title TEXT,
            year INTEGER,
            authors TEXT,
            abstract TEXT,
            field_of_study TEXT,
            in_degree INTEGER,
            out_degree INTEGER,
            cluster_id INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            source TEXT,
            target TEXT,
            PRIMARY KEY (source, target),
            FOREIGN KEY (source) REFERENCES nodes(paper_id),
            FOREIGN KEY (target) REFERENCES nodes(paper_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Read and insert data in chunks
    print("Reading JSON and inserting data...", file=sys.stderr)
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Insert nodes
    node_count = 0
    for node in data.get('nodes', []):
        try:
            cursor.execute('''
                INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                node.get('paper_id'),
                node.get('title'),
                node.get('year'),
                json.dumps(node.get('authors', [])),
                node.get('abstract', '')[:1000],  # Limit abstract size
                node.get('field_of_study'),
                node.get('in_degree', 0),
                node.get('out_degree', 0),
                node.get('cluster_id', -1)
            ))
            node_count += 1
            
            if node_count % 100000 == 0:
                print(f"  Inserted {node_count} nodes...", file=sys.stderr)
                conn.commit()
        except Exception as e:
            print(f"  Error inserting node {node.get('paper_id')}: {e}", file=sys.stderr)
    
    conn.commit()
    
    # Insert edges
    edge_count = 0
    for edge in data.get('edges', []):
        try:
            cursor.execute('''
                INSERT INTO edges VALUES (?, ?)
            ''', (edge.get('source'), edge.get('target')))
            edge_count += 1
            
            if edge_count % 100000 == 0:
                print(f"  Inserted {edge_count} edges...", file=sys.stderr)
                conn.commit()
        except Exception as e:
            if 'UNIQUE constraint failed' not in str(e):
                print(f"  Error inserting edge: {e}", file=sys.stderr)
    
    conn.commit()
    
    # Insert metadata
    stats = data.get('statistics', {})
    cursor.execute('INSERT INTO metadata VALUES (?, ?)', ('total_nodes', str(node_count)))
    cursor.execute('INSERT INTO metadata VALUES (?, ?)', ('total_edges', str(edge_count)))
    cursor.execute('INSERT INTO metadata VALUES (?, ?)', ('clusters', str(len(data.get('clusters', {})))))
    
    conn.commit()
    
    # Create indexes
    print("Creating indexes...", file=sys.stderr)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cluster ON nodes(cluster_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_year ON nodes(year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_degree ON nodes(in_degree, out_degree)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON edges(source)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_target ON edges(target)')
    
    conn.commit()
    conn.close()
    
    db_size = db_file.stat().st_size / 1024 / 1024
    print(f"Optimization complete!", file=sys.stderr)
    print(f"Database: {db_file}", file=sys.stderr)
    print(f"Size: {db_size:.1f} MB", file=sys.stderr)
    print(f"Nodes: {node_count}", file=sys.stderr)
    print(f"Edges: {edge_count}", file=sys.stderr)

if __name__ == '__main__':
    optimize_graph()
