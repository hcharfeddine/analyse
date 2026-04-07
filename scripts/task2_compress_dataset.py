"""
Task 2: Compress 140GB JSON dataset to max 10GB
Combines all JSON files into a single compressed archive
"""

import os
import json
import gzip
from pathlib import Path
from typing import Generator, Dict, Any
import ijson

# === CONFIGURATION ===
INPUT_DIR = "output_filtered/modified_per_year"
OUTPUT_FILE = "output_filtered/compressed/all_papers.json.gz"
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
    for file_path in Path(directory).rglob("*.json"):
        if file_path.is_file():
            total_size += file_path.stat().st_size
    return total_size / (1024 ** 3)


def stream_json_objects(file_path: str) -> Generator[Dict[Any, Any], None, None]:
    """Stream JSON objects from a large JSON array file"""
    with open(file_path, 'rb') as f:
        for obj in ijson.items(f, 'item'):
            yield obj


def minimize_paper(paper: Dict[Any, Any]) -> Dict[Any, Any]:
    """Reduce paper size by keeping only essential fields"""
    minimized = {}
    
    for field in ESSENTIAL_FIELDS:
        if field in paper:
            if field == "authors":
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


def compress_all_to_single_file(input_dir: str, output_file: str, target_size_gb: float = 10.0):
    """
    Compress all JSON files into a single gzipped JSON file.
    If the result exceeds target size, applies sampling.
    """
    input_path = Path(input_dir)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get original size
    print("Calculating original dataset size...")
    original_size_gb = get_directory_size_gb(input_dir)
    print(f"Original size: {original_size_gb:.2f} GB")
    print(f"Target size: {target_size_gb:.2f} GB")
    
    # Find all JSON files sorted by year
    json_files = sorted(input_path.glob("papers_*.json"))
    if not json_files:
        print("No JSON files found!")
        return
    
    print(f"Found {len(json_files)} JSON files to combine and compress")
    
    # Estimate sampling ratio needed
    # Gzip typically achieves 5-10x compression on JSON, let's assume 7x
    estimated_compression_ratio = 7
    estimated_compressed_gb = original_size_gb / estimated_compression_ratio
    
    sample_ratio = 1.0
    if estimated_compressed_gb > target_size_gb:
        sample_ratio = target_size_gb / estimated_compressed_gb
        print(f"Estimated compressed size ({estimated_compressed_gb:.1f} GB) exceeds target.")
        print(f"Will sample {sample_ratio:.1%} of papers to fit in {target_size_gb} GB")
    
    keep_every_n = max(1, int(1 / sample_ratio)) if sample_ratio < 1.0 else 1
    
    # Compress all files into one
    print(f"\nCompressing all files into: {output_file}")
    print("=" * 60)
    
    total_papers = 0
    kept_papers = 0
    
    with gzip.open(output_file, 'wt', encoding='utf-8', compresslevel=COMPRESSION_LEVEL) as f_out:
        f_out.write("[\n")
        first_paper = True
        
        for file_path in json_files:
            print(f"Processing: {file_path.name}")
            file_papers = 0
            file_kept = 0
            
            for paper in stream_json_objects(str(file_path)):
                total_papers += 1
                file_papers += 1
                
                # Apply sampling if needed
                if sample_ratio < 1.0 and total_papers % keep_every_n != 0:
                    continue
                
                # Minimize paper fields
                paper = minimize_paper(paper)
                
                # Write to output
                if not first_paper:
                    f_out.write(",\n")
                f_out.write(json.dumps(paper, separators=(',', ':')))
                first_paper = False
                kept_papers += 1
                file_kept += 1
                
                if kept_papers % 100000 == 0:
                    print(f"  Written {kept_papers:,} papers...")
            
            print(f"  -> {file_kept:,} / {file_papers:,} papers kept")
        
        f_out.write("\n]")
    
    # Report results
    final_size_bytes = os.path.getsize(output_file)
    final_size_gb = final_size_bytes / (1024 ** 3)
    
    print("\n" + "=" * 60)
    print("COMPRESSION COMPLETE")
    print("=" * 60)
    print(f"Output file: {output_file}")
    print(f"Original size: {original_size_gb:.2f} GB")
    print(f"Compressed size: {final_size_gb:.2f} GB")
    print(f"Compression ratio: {original_size_gb / final_size_gb:.1f}x")
    print(f"Total papers processed: {total_papers:,}")
    print(f"Papers in output: {kept_papers:,}")
    
    # Check if we need to re-compress with more aggressive sampling
    if final_size_gb > target_size_gb:
        print(f"\nWARNING: Output ({final_size_gb:.2f} GB) exceeds target ({target_size_gb} GB)")
        print("Re-running with more aggressive sampling...")
        
        # Calculate actual sampling needed
        actual_sample_ratio = target_size_gb / final_size_gb * sample_ratio
        os.remove(output_file)
        
        # Re-run with new sampling ratio
        keep_every_n = max(1, int(1 / actual_sample_ratio))
        print(f"New sampling: keeping every {keep_every_n}th paper")
        
        total_papers = 0
        kept_papers = 0
        
        with gzip.open(output_file, 'wt', encoding='utf-8', compresslevel=COMPRESSION_LEVEL) as f_out:
            f_out.write("[\n")
            first_paper = True
            
            for file_path in json_files:
                print(f"Processing: {file_path.name}")
                
                for paper in stream_json_objects(str(file_path)):
                    total_papers += 1
                    
                    if total_papers % keep_every_n != 0:
                        continue
                    
                    paper = minimize_paper(paper)
                    
                    if not first_paper:
                        f_out.write(",\n")
                    f_out.write(json.dumps(paper, separators=(',', ':')))
                    first_paper = False
                    kept_papers += 1
            
            f_out.write("\n]")
        
        final_size_gb = os.path.getsize(output_file) / (1024 ** 3)
        print(f"\nFinal size after re-sampling: {final_size_gb:.2f} GB")
        print(f"Papers in output: {kept_papers:,}")


if __name__ == "__main__":
    print("=" * 60)
    print("TASK 2: Compress All JSON Files Into Single Archive")
    print("=" * 60)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Target size: {TARGET_SIZE_GB} GB")
    print()
    
    compress_all_to_single_file(INPUT_DIR, OUTPUT_FILE, TARGET_SIZE_GB)
