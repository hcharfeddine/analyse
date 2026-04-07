"""
Task 4: Summarize unique fields of study from all JSON files
in output_filtered/modified_per_year
"""

import os
import json
from pathlib import Path
from typing import List, Set
import ijson

# === CONFIGURATION ===
INPUT_DIR = "output_filtered/modified_per_year"
OUTPUT_FILE = "output_filtered/fos_summary.json"

def stream_json_objects(file_path: str):
    """Stream JSON objects from a large JSON array file"""
    with open(file_path, 'rb') as f:
        for obj in ijson.items(f, 'item'):
            yield obj

def normalize_fos(fos_value) -> List[str]:
    """
    Normalize field_of_study to a list of strings
    Handles: string, list of strings, list of dicts, None
    """
    if not fos_value or fos_value == "Field not classified":
        return []
    
    if isinstance(fos_value, str):
        if len(fos_value) > 200:
            return []
        return [fos_value.strip()]
    
    if isinstance(fos_value, list):
        normalized = []
        for item in fos_value:
            if isinstance(item, str):
                if len(item) <= 200:
                    normalized.append(item.strip())
            elif isinstance(item, dict):
                name = item.get("name") or item.get("display_name") or item.get("field")
                if name and len(name) <= 200:
                    normalized.append(name.strip())
        return normalized
    
    return []

def summarize_fos(input_dir: str, output_file: str):
    """
    Extract all unique fields of study from all JSON files
    """
    input_path = Path(input_dir)
    
    # Find all JSON files
    json_files = sorted(input_path.glob("papers_*.json"))
    if not json_files:
        json_files = sorted(input_path.glob("papers_*_modified.json"))
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to process\n")
    
    # Collect all unique FOS
    all_unique_fos: Set[str] = set()
    total_papers = 0
    
    for file_path in json_files:
        print(f"Processing: {file_path.name}")
        
        file_papers = 0
        file_fos_count = 0
        
        for paper in stream_json_objects(str(file_path)):
            file_papers += 1
            
            fos_list = normalize_fos(paper.get("field_of_study"))
            for fos in fos_list:
                all_unique_fos.add(fos)
                file_fos_count += 1
            
            if file_papers % 100000 == 0:
                print(f"    Processed {file_papers} papers...")
        
        total_papers += file_papers
        print(f"  Done: {file_papers} papers\n")
    
    # Build simple output - just the list of unique FOS
    output_data = {
        "total_papers": total_papers,
        "unique_fos_count": len(all_unique_fos),
        "unique_fields_of_study": sorted(list(all_unique_fos))
    }
    
    # Ensure output directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print("="*60)
    print(f"Summary saved to: {output_file}")
    print(f"Total papers processed: {total_papers:,}")
    print(f"Unique fields of study: {len(all_unique_fos):,}")
    print("="*60)

if __name__ == "__main__":
    print("="*60)
    print("TASK 4: Summarize Unique Fields of Study")
    print("="*60)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output file: {OUTPUT_FILE}")
    print()
    
    summarize_fos(INPUT_DIR, OUTPUT_FILE)
