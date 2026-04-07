"""
Task 3: Add abstracts to papers in fos_from_abstract.json
Reads paper IDs from fos_from_abstract.json and looks up their abstracts
from the JSON files in output_filtered/modified_per_year
"""

import os
import json
from pathlib import Path
from typing import Dict, Set, Optional
import ijson

# === CONFIGURATION ===
FOS_FILE = "output_filtered/fos_fill_sources/fos_from_abstract.json"
PAPERS_DIR = "output_filtered/modified_per_year"
OUTPUT_FILE = "output_filtered/fos_fill_sources/fos_from_abstract_with_abstracts.json"

def load_paper_ids(fos_file: str) -> Set[str]:
    """Load paper IDs from the fos_from_abstract.json file"""
    with open(fos_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    paper_ids = set(data.get("paper_ids", []))
    print(f"Loaded {len(paper_ids)} paper IDs from {fos_file}")
    return paper_ids

def stream_json_objects(file_path: str):
    """Stream JSON objects from a large JSON array file"""
    with open(file_path, 'rb') as f:
        for obj in ijson.items(f, 'item'):
            yield obj

def find_abstracts_in_file(file_path: str, paper_ids: Set[str]) -> Dict[str, Dict]:
    """
    Search a JSON file for papers matching the given IDs
    Returns dict of paper_id -> {paper_id, abstract, title, year}
    """
    found = {}
    processed = 0
    
    for paper in stream_json_objects(file_path):
        processed += 1
        paper_id = paper.get("paper_id")
        
        if paper_id and paper_id in paper_ids:
            abstract = paper.get("abstract", "")
            if abstract and abstract != "Abstract not available":
                found[paper_id] = {
                    "paper_id": paper_id,
                    "title": paper.get("title", ""),
                    "year": paper.get("year"),
                    "abstract": abstract
                }
        
        if processed % 100000 == 0:
            print(f"    Processed {processed} papers, found {len(found)} matches...")
    
    return found

def add_abstracts_to_fos(fos_file: str, papers_dir: str, output_file: str):
    """
    Main function to add abstracts from papers to the FOS file
    """
    # Load paper IDs we need to find
    paper_ids = load_paper_ids(fos_file)
    
    if not paper_ids:
        print("No paper IDs found in the FOS file.")
        return
    
    # Find all JSON files in the papers directory
    papers_path = Path(papers_dir)
    json_files = sorted(papers_path.glob("papers_*.json"))
    
    if not json_files:
        # Try with _modified suffix
        json_files = sorted(papers_path.glob("papers_*_modified.json"))
    
    if not json_files:
        print(f"No JSON files found in {papers_dir}")
        return
    
    print(f"\nSearching through {len(json_files)} JSON files...")
    
    # Collect all found papers
    all_found: Dict[str, Dict] = {}
    remaining_ids = paper_ids.copy()
    
    for file_path in json_files:
        if not remaining_ids:
            print("All paper IDs found!")
            break
        
        print(f"\nSearching in: {file_path.name}")
        print(f"  Looking for {len(remaining_ids)} remaining papers...")
        
        found = find_abstracts_in_file(str(file_path), remaining_ids)
        
        if found:
            all_found.update(found)
            remaining_ids -= set(found.keys())
            print(f"  Found {len(found)} papers, {len(remaining_ids)} remaining")
    
    # Prepare output
    print("\n" + "="*60)
    print("BUILDING OUTPUT FILE")
    print("="*60)
    
    # Create output structure
    output_data = {
        "count": len(paper_ids),
        "found_count": len(all_found),
        "not_found_count": len(remaining_ids),
        "papers": list(all_found.values()),
        "not_found_ids": list(remaining_ids)
    }
    
    # Ensure output directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nOutput saved to: {output_file}")
    print(f"  Total paper IDs: {len(paper_ids)}")
    print(f"  Found with abstracts: {len(all_found)}")
    print(f"  Not found: {len(remaining_ids)}")

def add_abstracts_streaming(fos_file: str, papers_dir: str, output_file: str):
    """
    Memory-efficient version: streams output for very large datasets
    """
    paper_ids = load_paper_ids(fos_file)
    
    if not paper_ids:
        print("No paper IDs found in the FOS file.")
        return
    
    papers_path = Path(papers_dir)
    json_files = sorted(papers_path.glob("papers_*.json"))
    
    if not json_files:
        json_files = sorted(papers_path.glob("papers_*_modified.json"))
    
    if not json_files:
        print(f"No JSON files found in {papers_dir}")
        return
    
    # Ensure output directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    remaining_ids = paper_ids.copy()
    found_count = 0
    
    with open(output_file, 'w', encoding='utf-8') as f_out:
        f_out.write('{"papers": [\n')
        first = True
        
        for file_path in json_files:
            if not remaining_ids:
                break
            
            print(f"\nSearching in: {file_path.name}")
            print(f"  Looking for {len(remaining_ids)} remaining papers...")
            
            file_found = 0
            for paper in stream_json_objects(str(file_path)):
                paper_id = paper.get("paper_id")
                
                if paper_id and paper_id in remaining_ids:
                    abstract = paper.get("abstract", "")
                    if abstract and abstract != "Abstract not available":
                        entry = {
                            "paper_id": paper_id,
                            "title": paper.get("title", ""),
                            "year": paper.get("year"),
                            "abstract": abstract
                        }
                        
                        if not first:
                            f_out.write(",\n")
                        f_out.write(json.dumps(entry, ensure_ascii=False))
                        first = False
                        
                        remaining_ids.discard(paper_id)
                        found_count += 1
                        file_found += 1
            
            print(f"  Found {file_found} papers in this file")
        
        f_out.write('\n],\n')
        f_out.write(f'"count": {len(paper_ids)},\n')
        f_out.write(f'"found_count": {found_count},\n')
        f_out.write(f'"not_found_count": {len(remaining_ids)},\n')
        f_out.write(f'"not_found_ids": {json.dumps(list(remaining_ids))}\n')
        f_out.write('}')
    
    print("\n" + "="*60)
    print("COMPLETE")
    print("="*60)
    print(f"Output saved to: {output_file}")
    print(f"  Total paper IDs: {len(paper_ids)}")
    print(f"  Found with abstracts: {found_count}")
    print(f"  Not found: {len(remaining_ids)}")

if __name__ == "__main__":
    print("="*60)
    print("TASK 3: Add Abstracts to FOS Paper IDs")
    print("="*60)
    print(f"FOS file: {FOS_FILE}")
    print(f"Papers directory: {PAPERS_DIR}")
    print(f"Output file: {OUTPUT_FILE}")
    print()
    
    # Use streaming version for memory efficiency with large datasets
    add_abstracts_streaming(FOS_FILE, PAPERS_DIR, OUTPUT_FILE)
