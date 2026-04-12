#!/usr/bin/env python3
"""
Extract citation network data from JSON files.
Streams through papers and outputs nodes and edges in JSONL format.
"""

import json
import os
from pathlib import Path
from typing import Any, Generator
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def get_data_directory() -> Path:
    """Get the data directory path."""
    # Check for output_filtered directory
    repo_root = Path(__file__).parent.parent.parent
    data_dir = repo_root / "output_filtered" / "modified_per_year"
    
    if not data_dir.exists():
        # Try alternative paths
        for alternative in [
            repo_root / "data" / "modified_per_year",
            repo_root / "modified_per_year",
        ]:
            if alternative.exists():
                return alternative
    
    return data_dir


def extract_papers() -> Generator[dict[str, Any], None, None]:
    """
    Extract all papers from JSON files.
    Yields paper objects with full metadata.
    """
    data_dir = get_data_directory()
    
    if not data_dir.exists():
        print(f"Warning: Data directory not found at {data_dir}")
        print(f"Looking for JSON files in current directory...")
        data_dir = Path(".")
    
    # Find all JSON files
    json_files = list(data_dir.glob("*.json")) + list(data_dir.glob("**/*.json"))
    json_files = list(set(json_files))  # Remove duplicates
    
    print(f"Found {len(json_files)} JSON files to process", file=sys.stderr)
    
    total_papers = 0
    
    for json_file in sorted(json_files):
        try:
            print(f"Processing {json_file.name}...", file=sys.stderr)
            
            with open(json_file, 'r', encoding='utf-8') as f:
                # Handle both single JSON object and array of objects
                content = json.load(f)
                
                if isinstance(content, list):
                    papers = content
                elif isinstance(content, dict) and 'papers' in content:
                    papers = content['papers']
                elif isinstance(content, dict) and 'data' in content:
                    papers = content['data']
                else:
                    # Single paper object
                    papers = [content]
            
            for paper in papers:
                if isinstance(paper, dict) and 'paper_id' in paper:
                    yield paper
                    total_papers += 1
                    
                    if total_papers % 100000 == 0:
                        print(f"Extracted {total_papers} papers...", file=sys.stderr)
        
        except json.JSONDecodeError as e:
            print(f"Error decoding {json_file}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {json_file}: {e}", file=sys.stderr)
    
    print(f"Total papers extracted: {total_papers}", file=sys.stderr)


def extract_nodes_and_edges():
    """
    Extract nodes and edges from papers.
    Outputs to JSONL files.
    """
    output_dir = Path("public/data")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    nodes_file = output_dir / "nodes.jsonl"
    edges_file = output_dir / "edges.jsonl"
    
    paper_ids = set()
    edge_count = 0
    
    print(f"Writing nodes to {nodes_file}", file=sys.stderr)
    print(f"Writing edges to {edges_file}", file=sys.stderr)
    
    with open(nodes_file, 'w', encoding='utf-8') as nf, \
         open(edges_file, 'w', encoding='utf-8') as ef:
        
        for i, paper in enumerate(extract_papers()):
            paper_id = paper.get('paper_id')
            
            if not paper_id:
                continue
            
            paper_ids.add(paper_id)
            
            # Write node with all metadata
            node_data = {
                'paper_id': paper_id,
                'title': paper.get('title', ''),
                'authors': paper.get('authors', []),
                'year': paper.get('year'),
                'cited_by_count': paper.get('cited_by_count', 0),
                'doi': paper.get('doi', ''),
                'publisher': paper.get('publisher', ''),
                'abstract': paper.get('abstract', ''),
                'publication_type': paper.get('publication_type', ''),
                'journal_name': paper.get('journal_name', ''),
                'venue': paper.get('venue', ''),
                'field_of_study': paper.get('field_of_study', ''),
                'keywords': paper.get('keywords', []),
                'pdf_url': paper.get('pdf_url', ''),
                'references': paper.get('references', []),
            }
            
            nf.write(json.dumps(node_data) + '\n')
            
            # Write edges for references
            references = paper.get('references', [])
            if references:
                for ref_id in references:
                    edge = {
                        'source': paper_id,
                        'target': ref_id
                    }
                    ef.write(json.dumps(edge) + '\n')
                    edge_count += 1
            
            if (i + 1) % 100000 == 0:
                print(f"Processed {i + 1} papers, {edge_count} edges", file=sys.stderr)
    
    print(f"Extraction complete: {len(paper_ids)} nodes, {edge_count} edges", file=sys.stderr)
    
    return {
        'node_count': len(paper_ids),
        'edge_count': edge_count,
        'nodes_file': str(nodes_file),
        'edges_file': str(edges_file),
    }


if __name__ == '__main__':
    result = extract_nodes_and_edges()
    print(json.dumps(result))
