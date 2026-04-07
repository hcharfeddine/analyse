"""
Task 2: Compress JSON files per year
Each papers_YYYY.json gets compressed to papers_YYYY.json.gz
"""

import os
import json
import gzip
from pathlib import Path

# === CONFIGURATION ===
INPUT_DIR = "output_filtered/modified_per_year"
OUTPUT_DIR = "output_filtered/compressed"
COMPRESSION_LEVEL = 9  # Maximum gzip compression (1-9)


def get_file_size_gb(file_path: str) -> float:
    """Get file size in GB"""
    return os.path.getsize(file_path) / (1024 ** 3)


def compress_file(input_file: Path, output_file: Path):
    """Compress a single JSON file to gzip"""
    with open(input_file, 'rb') as f_in:
        with gzip.open(output_file, 'wb', compresslevel=COMPRESSION_LEVEL) as f_out:
            # Read and write in chunks to handle large files
            while chunk := f_in.read(1024 * 1024 * 10):  # 10MB chunks
                f_out.write(chunk)


def compress_per_year(input_dir: str, output_dir: str):
    """Compress each JSON file individually"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all JSON files
    json_files = sorted(input_path.glob("papers_*.json"))
    
    if not json_files:
        print("No JSON files found!")
        return
    
    print(f"Found {len(json_files)} files to compress")
    print()
    
    total_original = 0
    total_compressed = 0
    
    for i, input_file in enumerate(json_files, 1):
        # Output filename: papers_1980.json -> papers_1980.json.gz
        output_file = output_path / f"{input_file.stem}.json.gz"
        
        original_size = get_file_size_gb(str(input_file))
        total_original += original_size
        
        print(f"[{i}/{len(json_files)}] Compressing {input_file.name}")
        print(f"  Original size: {original_size:.2f} GB")
        
        compress_file(input_file, output_file)
        
        compressed_size = get_file_size_gb(str(output_file))
        total_compressed += compressed_size
        
        ratio = original_size / compressed_size if compressed_size > 0 else 0
        print(f"  Compressed size: {compressed_size:.2f} GB")
        print(f"  Compression ratio: {ratio:.1f}x")
        print()
    
    # Summary
    print("=" * 60)
    print("COMPRESSION COMPLETE")
    print("=" * 60)
    print(f"Total original: {total_original:.2f} GB")
    print(f"Total compressed: {total_compressed:.2f} GB")
    print(f"Overall ratio: {total_original / total_compressed:.1f}x")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    print("=" * 60)
    print("TASK 2: Compress JSON Files Per Year")
    print("=" * 60)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    compress_per_year(INPUT_DIR, OUTPUT_DIR)
