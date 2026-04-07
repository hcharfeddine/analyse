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

def is_valid_fos(fos_name: str) -> bool:
    """
    Check if a string looks like a valid field of study name.
    Valid FOS names are short, don't contain HTML entities, 
    don't look like abstracts, etc.
    """
    if not fos_name:
        return False
    
    fos_name = fos_name.strip()
    
    # Too short or too long
    if len(fos_name) < 2 or len(fos_name) > 100:
        return False
    
    # Skip default/placeholder values
    invalid_values = {"Field not classified", "Unknown", "N/A", "None", "null", "", "-", ".", "...", "*"}
    if fos_name in invalid_values:
        return False
    
    # Skip if it contains HTML entities
    if "&#x" in fos_name or "&lt;" in fos_name or "&gt;" in fos_name or "&amp;" in fos_name:
        return False
    
    # Skip if it looks like a sentence (has too many spaces - likely abstract)
    if fos_name.count(' ') > 8:
        return False
    
    # Skip if starts with quotes (likely abstract excerpt)
    if fos_name.startswith('"') or fos_name.startswith("'"):
        return False
    
    # Skip if contains numbers patterns that look like dates/codes
    if fos_name.startswith("(") or fos_name.startswith("1") or fos_name.startswith("0"):
        return False
    
    # Skip non-ASCII heavy strings (likely corrupted data)
    ascii_chars = sum(1 for c in fos_name if ord(c) < 128)
    if len(fos_name) > 5 and ascii_chars / len(fos_name) < 0.5:
        return False
    
    return True

def normalize_fos(fos_value) -> List[str]:
    """
    Normalize field_of_study to a list of strings
    Handles: string, list of strings, list of dicts, None
    """
    if not fos_value:
        return []
    
    if isinstance(fos_value, str):
        if is_valid_fos(fos_value):
            return [fos_value.strip()]
        return []
    
    if isinstance(fos_value, list):
        normalized = []
        for item in fos_value:
            if isinstance(item, str):
                if is_valid_fos(item):
                    normalized.append(item.strip())
            elif isinstance(item, dict):
                name = item.get("name") or item.get("display_name") or item.get("field")
                if name and is_valid_fos(name):
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
