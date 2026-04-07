"""
Task 4: Summarize unique fields of study from all JSON files
in output_filtered/modified_per_year
"""

import os
import json
from pathlib import Path
from typing import Dict, Set, List
from collections import Counter
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
        # Skip if it looks like an abstract (too long)
        if len(fos_value) > 200:
            return []
        return [fos_value.strip()]
    
    if isinstance(fos_value, list):
        normalized = []
        for item in fos_value:
            if isinstance(item, str):
                if len(item) <= 200:  # Skip long strings (abstracts)
                    normalized.append(item.strip())
            elif isinstance(item, dict):
                # Handle dict format like {"name": "Computer Science"}
                name = item.get("name") or item.get("display_name") or item.get("field")
                if name and len(name) <= 200:
                    normalized.append(name.strip())
        return normalized
    
    return []

def extract_fos_from_file(file_path: str) -> tuple:
    """
    Extract all unique fields of study from a JSON file
    Returns (fos_counter, paper_count, fos_by_year)
    """
    fos_counter = Counter()
    paper_count = 0
    papers_with_fos = 0
    
    for paper in stream_json_objects(file_path):
        paper_count += 1
        
        fos_list = normalize_fos(paper.get("field_of_study"))
        
        if fos_list:
            papers_with_fos += 1
            for fos in fos_list:
                fos_counter[fos] += 1
        
        if paper_count % 100000 == 0:
            print(f"    Processed {paper_count} papers, found {len(fos_counter)} unique FOS...")
    
    return fos_counter, paper_count, papers_with_fos

def summarize_fos(input_dir: str, output_file: str):
    """
    Main function to summarize all unique fields of study
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
    
    # Aggregate FOS across all files
    global_fos_counter = Counter()
    fos_by_year: Dict[str, Counter] = {}
    total_papers = 0
    total_with_fos = 0
    
    for file_path in json_files:
        # Extract year from filename
        filename = file_path.name
        year = "unknown"
        if "papers_" in filename:
            parts = filename.replace("papers_", "").replace("_modified.json", "").replace(".json", "")
            if parts.isdigit():
                year = parts
        
        print(f"Processing: {file_path.name} (Year: {year})")
        
        fos_counter, paper_count, papers_with_fos = extract_fos_from_file(str(file_path))
        
        global_fos_counter.update(fos_counter)
        fos_by_year[year] = fos_counter
        total_papers += paper_count
        total_with_fos += papers_with_fos
        
        print(f"  Papers: {paper_count}, With FOS: {papers_with_fos}, Unique FOS: {len(fos_counter)}\n")
    
    # Build summary output
    print("="*60)
    print("BUILDING SUMMARY")
    print("="*60)
    
    # Sort FOS by frequency
    sorted_fos = global_fos_counter.most_common()
    
    # Create output structure
    output_data = {
        "summary": {
            "total_papers": total_papers,
            "papers_with_fos": total_with_fos,
            "papers_without_fos": total_papers - total_with_fos,
            "unique_fos_count": len(global_fos_counter),
            "years_covered": sorted([y for y in fos_by_year.keys() if y != "unknown"])
        },
        "top_100_fos": [
            {"field": fos, "count": count}
            for fos, count in sorted_fos[:100]
        ],
        "all_unique_fos": [
            {"field": fos, "count": count}
            for fos, count in sorted_fos
        ],
        "fos_by_year": {
            year: {
                "unique_count": len(counter),
                "top_20": [
                    {"field": fos, "count": count}
                    for fos, count in counter.most_common(20)
                ]
            }
            for year, counter in sorted(fos_by_year.items())
        }
    }
    
    # Ensure output directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\nSummary saved to: {output_file}")
    print(f"\n--- STATISTICS ---")
    print(f"Total papers processed: {total_papers:,}")
    print(f"Papers with FOS: {total_with_fos:,} ({total_with_fos/total_papers*100:.1f}%)")
    print(f"Unique fields of study: {len(global_fos_counter):,}")
    print(f"\n--- TOP 20 FIELDS OF STUDY ---")
    for i, (fos, count) in enumerate(sorted_fos[:20], 1):
        print(f"  {i:2}. {fos}: {count:,}")

def summarize_fos_memory_efficient(input_dir: str, output_file: str, top_n: int = 10000):
    """
    Memory-efficient version: only keeps top N FOS in memory
    Use this for extremely large datasets
    """
    input_path = Path(input_dir)
    
    json_files = sorted(input_path.glob("papers_*.json"))
    if not json_files:
        json_files = sorted(input_path.glob("papers_*_modified.json"))
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to process (memory-efficient mode)\n")
    
    fos_counter = Counter()
    total_papers = 0
    total_with_fos = 0
    years_seen = set()
    
    for file_path in json_files:
        filename = file_path.name
        year = "unknown"
        if "papers_" in filename:
            parts = filename.replace("papers_", "").replace("_modified.json", "").replace(".json", "")
            if parts.isdigit():
                year = parts
                years_seen.add(year)
        
        print(f"Processing: {file_path.name}")
        
        file_papers = 0
        file_with_fos = 0
        
        for paper in stream_json_objects(str(file_path)):
            file_papers += 1
            
            fos_list = normalize_fos(paper.get("field_of_study"))
            if fos_list:
                file_with_fos += 1
                fos_counter.update(fos_list)
            
            if file_papers % 100000 == 0:
                print(f"    {file_papers} papers processed...")
        
        total_papers += file_papers
        total_with_fos += file_with_fos
        print(f"  Done: {file_papers} papers, {file_with_fos} with FOS\n")
        
        # Keep only top N to manage memory
        if len(fos_counter) > top_n * 2:
            fos_counter = Counter(dict(fos_counter.most_common(top_n)))
    
    # Build and save output
    sorted_fos = fos_counter.most_common()
    
    output_data = {
        "summary": {
            "total_papers": total_papers,
            "papers_with_fos": total_with_fos,
            "unique_fos_count": len(fos_counter),
            "years_covered": sorted(list(years_seen)),
            "note": f"Memory-efficient mode: only top {top_n} FOS retained"
        },
        "top_fos": [
            {"field": fos, "count": count}
            for fos, count in sorted_fos
        ]
    }
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print("="*60)
    print(f"Summary saved to: {output_file}")
    print(f"Total papers: {total_papers:,}")
    print(f"Unique FOS (top {top_n}): {len(fos_counter):,}")
    print("="*60)

if __name__ == "__main__":
    print("="*60)
    print("TASK 4: Summarize Unique Fields of Study")
    print("="*60)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output file: {OUTPUT_FILE}")
    print()
    
    # Use standard version (use memory_efficient for very large datasets)
    summarize_fos(INPUT_DIR, OUTPUT_FILE)
    
    # Uncomment for memory-efficient version:
    # summarize_fos_memory_efficient(INPUT_DIR, OUTPUT_FILE, top_n=10000)
