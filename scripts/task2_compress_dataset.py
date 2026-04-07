"""
Task 2: Compress 140GB JSON dataset to max 10GB
Uses multiple strategies: gzip compression, field reduction, and sampling
"""

import os
import json
import gzip
import shutil
from pathlib import Path
from typing import Generator, Dict, Any, List, Optional
import ijson

# === CONFIGURATION ===
INPUT_DIR = "output_filtered/modified_per_year"
OUTPUT_DIR = "output_filtered/compressed"
TARGET_SIZE_GB = 10
COMPRESSION_LEVEL = 9  # Maximum gzip compression (1-9)

# Fields to keep (remove verbose fields to reduce size)
ESSENTIAL_FIELDS = [
    "paper_id",
    "title",
    "year",
    "cited_by_count",
    "doi",
    "publisher",
    "abstract",
    "publication_type",
    "journal_name",
    "venue",
    "field_of_study",
    "keywords",
    "authors",
    "references",
    "pdf_url"
]

# Fields to keep for authors (reduce author data)
AUTHOR_ESSENTIAL_FIELDS = [
    "author_id",
    "affiliations",
    "countries",
    "citation_count"
]

def get_directory_size_gb(directory: str) -> float:
    """Get total size of directory in GB"""
    total_size = 0
    for file_path in Path(directory).rglob("*"):
        if file_path.is_file():
            total_size += file_path.stat().st_size
    return total_size / (1024 ** 3)

def stream_json_objects(file_path: str) -> Generator[Dict[Any, Any], None, None]:
    """Stream JSON objects from a large JSON array file"""
    with open(file_path, 'rb') as f:
        for obj in ijson.items(f, 'item'):
            yield obj

def minimize_paper(paper: Dict[Any, Any], keep_abstract: bool = True) -> Dict[Any, Any]:
    """Reduce paper size by keeping only essential fields"""
    minimized = {}
    
    for field in ESSENTIAL_FIELDS:
        if field in paper:
            if field == "abstract" and not keep_abstract:
                # Truncate abstract to first 500 chars if needed
                abstract = paper.get("abstract", "")
                minimized[field] = abstract[:500] if len(abstract) > 500 else abstract
            elif field == "authors":
                # Minimize author data
                minimized["authors"] = [
                    {k: v for k, v in author.items() if k in AUTHOR_ESSENTIAL_FIELDS}
                    for author in paper.get("authors", [])
                ]
            elif field == "references":
                # Keep only first 50 references
                refs = paper.get("references", [])
                minimized["references"] = refs[:50] if len(refs) > 50 else refs
            else:
                minimized[field] = paper[field]
    
    return minimized

def compress_file_gzip(input_file: str, output_file: str, minimize: bool = True) -> tuple:
    """
    Compress a JSON file using gzip with optional field minimization
    Returns (original_size, compressed_size, paper_count)
    """
    original_size = os.path.getsize(input_file)
    paper_count = 0
    
    with gzip.open(output_file, 'wt', encoding='utf-8', compresslevel=COMPRESSION_LEVEL) as f_out:
        f_out.write("[\n")
        first = True
        
        for paper in stream_json_objects(input_file):
            if minimize:
                paper = minimize_paper(paper)
            
            if not first:
                f_out.write(",\n")
            f_out.write(json.dumps(paper, separators=(',', ':')))  # Compact JSON
            first = False
            paper_count += 1
            
            if paper_count % 10000 == 0:
                print(f"    Processed {paper_count} papers...")
        
        f_out.write("\n]")
    
    compressed_size = os.path.getsize(output_file)
    return original_size, compressed_size, paper_count

def calculate_sampling_ratio(current_size_gb: float, target_size_gb: float) -> float:
    """Calculate what percentage of papers to keep to meet target size"""
    if current_size_gb <= target_size_gb:
        return 1.0
    return target_size_gb / current_size_gb

def compress_with_sampling(input_file: str, output_file: str, sample_ratio: float) -> tuple:
    """
    Compress file by sampling papers (keep every Nth paper)
    Returns (original_size, compressed_size, paper_count)
    """
    original_size = os.path.getsize(input_file)
    paper_count = 0
    kept_count = 0
    keep_every_n = max(1, int(1 / sample_ratio))
    
    with gzip.open(output_file, 'wt', encoding='utf-8', compresslevel=COMPRESSION_LEVEL) as f_out:
        f_out.write("[\n")
        first = True
        
        for paper in stream_json_objects(input_file):
            paper_count += 1
            
            # Keep every Nth paper
            if paper_count % keep_every_n == 0:
                paper = minimize_paper(paper)
                
                if not first:
                    f_out.write(",\n")
                f_out.write(json.dumps(paper, separators=(',', ':')))
                first = False
                kept_count += 1
            
            if paper_count % 50000 == 0:
                print(f"    Processed {paper_count} papers, kept {kept_count}...")
        
        f_out.write("\n]")
    
    compressed_size = os.path.getsize(output_file)
    return original_size, compressed_size, kept_count

def compress_dataset(input_dir: str, output_dir: str, target_size_gb: float = 10.0):
    """
    Main compression function with multiple strategies:
    1. First pass: gzip + field minimization
    2. If still too large: add sampling
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get original size
    print("Calculating original dataset size...")
    original_size_gb = get_directory_size_gb(input_dir)
    print(f"Original size: {original_size_gb:.2f} GB")
    print(f"Target size: {target_size_gb:.2f} GB")
    
    # Find all JSON files
    json_files = sorted(input_path.glob("papers_*.json"))
    if not json_files:
        json_files = sorted(input_path.glob("papers_*_modified.json"))
    
    if not json_files:
        print("No JSON files found!")
        return
    
    print(f"\nFound {len(json_files)} JSON files to compress")
    
    # Strategy 1: Gzip + Minimization
    print("\n" + "="*60)
    print("STRATEGY 1: Gzip compression + Field minimization")
    print("="*60)
    
    total_original = 0
    total_compressed = 0
    total_papers = 0
    
    for file_path in json_files:
        filename = file_path.name.replace("_modified", "")
        output_file = output_path / f"{filename}.gz"
        
        print(f"\nCompressing: {file_path.name}")
        orig, comp, count = compress_file_gzip(str(file_path), str(output_file), minimize=True)
        
        total_original += orig
        total_compressed += comp
        total_papers += count
        
        ratio = comp / orig * 100 if orig > 0 else 0
        print(f"  {orig / 1e9:.2f} GB -> {comp / 1e9:.2f} GB ({ratio:.1f}%) | {count} papers")
    
    compressed_size_gb = total_compressed / (1024 ** 3)
    print(f"\n--- After Strategy 1 ---")
    print(f"Compressed size: {compressed_size_gb:.2f} GB")
    print(f"Total papers: {total_papers}")
    
    # Strategy 2: If still too large, apply sampling
    if compressed_size_gb > target_size_gb:
        print("\n" + "="*60)
        print("STRATEGY 2: Adding sampling (compressed size still exceeds target)")
        print("="*60)
        
        sample_ratio = calculate_sampling_ratio(compressed_size_gb, target_size_gb)
        print(f"Sampling ratio: {sample_ratio:.2%} (keeping ~{int(total_papers * sample_ratio)} papers)")
        
        # Re-compress with sampling
        sampled_dir = output_path / "sampled"
        sampled_dir.mkdir(parents=True, exist_ok=True)
        
        total_compressed = 0
        total_kept = 0
        
        for file_path in json_files:
            filename = file_path.name.replace("_modified", "")
            output_file = sampled_dir / f"{filename}.gz"
            
            print(f"\nRecompressing with sampling: {file_path.name}")
            orig, comp, kept = compress_with_sampling(str(file_path), str(output_file), sample_ratio)
            
            total_compressed += comp
            total_kept += kept
            
            print(f"  Kept {kept} papers, size: {comp / 1e6:.1f} MB")
        
        final_size_gb = total_compressed / (1024 ** 3)
        print(f"\n--- After Strategy 2 ---")
        print(f"Final size: {final_size_gb:.2f} GB")
        print(f"Papers kept: {total_kept}")
    
    print("\n" + "="*60)
    print("COMPRESSION COMPLETE")
    print("="*60)
    print(f"Output directory: {output_dir}")
    print(f"Original: {original_size_gb:.2f} GB -> Final: {compressed_size_gb:.2f} GB")

if __name__ == "__main__":
    print("="*60)
    print("TASK 2: Compress Large JSON Dataset (Target: 10GB)")
    print("="*60)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Target size: {TARGET_SIZE_GB} GB")
    print(f"Compression level: {COMPRESSION_LEVEL}")
    print()
    
    compress_dataset(INPUT_DIR, OUTPUT_DIR, TARGET_SIZE_GB)
