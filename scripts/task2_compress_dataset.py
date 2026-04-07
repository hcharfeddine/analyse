"""
Task 2: Compress 140GB JSON dataset into multiple archives (max 10GB each)
Groups files together until reaching ~10GB, then starts a new archive
"""

import os
import json
import gzip
from pathlib import Path
from typing import List, Tuple

# === CONFIGURATION ===
INPUT_DIR = "output_filtered/modified_per_year"
OUTPUT_DIR = "output_filtered/compressed"
MAX_ARCHIVE_SIZE_GB = 10
COMPRESSION_LEVEL = 9  # Maximum gzip compression (1-9)


def get_file_size_gb(file_path: str) -> float:
    """Get file size in GB"""
    return os.path.getsize(file_path) / (1024 ** 3)


def get_files_with_sizes(input_dir: str) -> List[Tuple[Path, float]]:
    """Get all JSON files with their sizes in GB, sorted by name"""
    input_path = Path(input_dir)
    files_with_sizes = []
    
    for file_path in sorted(input_path.glob("papers_*.json")):
        size_gb = get_file_size_gb(str(file_path))
        files_with_sizes.append((file_path, size_gb))
    
    return files_with_sizes


def group_files_into_bins(files_with_sizes: List[Tuple[Path, float]], max_size_gb: float) -> List[List[Path]]:
    """
    Group files into bins where each bin's total size is <= max_size_gb
    Uses a simple greedy approach: add files to current bin until full, then start new bin
    """
    bins = []
    current_bin = []
    current_bin_size = 0.0
    
    for file_path, size_gb in files_with_sizes:
        # If single file exceeds max size, it goes in its own bin
        if size_gb >= max_size_gb:
            if current_bin:
                bins.append(current_bin)
                current_bin = []
                current_bin_size = 0.0
            bins.append([file_path])
            print(f"  {file_path.name}: {size_gb:.2f} GB -> alone (exceeds max)")
            continue
        
        # If adding this file would exceed max, start new bin
        if current_bin_size + size_gb > max_size_gb:
            if current_bin:
                bins.append(current_bin)
                print(f"  Bin closed at {current_bin_size:.2f} GB")
            current_bin = [file_path]
            current_bin_size = size_gb
        else:
            current_bin.append(file_path)
            current_bin_size += size_gb
    
    # Don't forget the last bin
    if current_bin:
        bins.append(current_bin)
        print(f"  Final bin: {current_bin_size:.2f} GB")
    
    return bins


def compress_files_to_archive(files: List[Path], output_file: str):
    """
    Compress multiple JSON files into a single gzipped JSON file
    Output format: array of all papers from all files combined
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with gzip.open(output_file, 'wt', encoding='utf-8', compresslevel=COMPRESSION_LEVEL) as f_out:
        f_out.write("[\n")
        first_paper = True
        total_papers = 0
        
        for file_path in files:
            print(f"    Adding: {file_path.name}")
            
            # Read and stream papers from this file
            with open(file_path, 'r', encoding='utf-8') as f_in:
                papers = json.load(f_in)
            
            for paper in papers:
                if not first_paper:
                    f_out.write(",\n")
                f_out.write(json.dumps(paper, separators=(',', ':')))
                first_paper = False
                total_papers += 1
        
        f_out.write("\n]")
    
    return total_papers


def compress_dataset(input_dir: str, output_dir: str, max_archive_size_gb: float):
    """
    Main function: groups files into bins and compresses each bin
    """
    print("Scanning input files...")
    files_with_sizes = get_files_with_sizes(input_dir)
    
    if not files_with_sizes:
        print("No JSON files found!")
        return
    
    total_size = sum(size for _, size in files_with_sizes)
    print(f"Found {len(files_with_sizes)} files, total size: {total_size:.2f} GB")
    print(f"Max archive size: {max_archive_size_gb} GB")
    print()
    
    # Show file sizes
    print("File sizes:")
    for file_path, size_gb in files_with_sizes:
        print(f"  {file_path.name}: {size_gb:.2f} GB")
    print()
    
    # Group files into bins
    print("Grouping files into archives...")
    bins = group_files_into_bins(files_with_sizes, max_archive_size_gb)
    print(f"\nCreated {len(bins)} archive groups")
    print()
    
    # Compress each bin
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    for i, bin_files in enumerate(bins, 1):
        # Determine output filename based on years in this bin
        years = []
        for f in bin_files:
            # Extract year from filename like "papers_1980.json"
            name = f.stem
            if "_" in name:
                year_part = name.split("_")[-1]
                if year_part.isdigit():
                    years.append(int(year_part))
        
        if years:
            if len(years) == 1:
                archive_name = f"papers_{years[0]}.json.gz"
            else:
                archive_name = f"papers_{min(years)}-{max(years)}.json.gz"
        else:
            archive_name = f"papers_archive_{i}.json.gz"
        
        output_file = output_path / archive_name
        
        bin_size = sum(get_file_size_gb(str(f)) for f in bin_files)
        print(f"Archive {i}/{len(bins)}: {archive_name}")
        print(f"  Files: {len(bin_files)}, Original size: {bin_size:.2f} GB")
        
        total_papers = compress_files_to_archive(bin_files, str(output_file))
        
        compressed_size_gb = get_file_size_gb(str(output_file))
        print(f"  Compressed size: {compressed_size_gb:.2f} GB")
        print(f"  Papers: {total_papers:,}")
        print(f"  Compression ratio: {bin_size / compressed_size_gb:.1f}x")
        print()
    
    # Summary
    print("=" * 60)
    print("COMPRESSION COMPLETE")
    print("=" * 60)
    
    total_compressed = sum(
        get_file_size_gb(str(f)) 
        for f in output_path.glob("*.json.gz")
    )
    
    print(f"Original total: {total_size:.2f} GB")
    print(f"Compressed total: {total_compressed:.2f} GB")
    print(f"Number of archives: {len(bins)}")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    print("=" * 60)
    print("TASK 2: Compress JSON Files Into Archives (Max 10GB each)")
    print("=" * 60)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Max archive size: {MAX_ARCHIVE_SIZE_GB} GB")
    print()
    
    compress_dataset(INPUT_DIR, OUTPUT_DIR, MAX_ARCHIVE_SIZE_GB)
