"""
Task 2: Compress JSON files into tar.gz archives (max 10GB per archive)
Groups files together until reaching ~10GB, then starts a new archive.
Each JSON file stays separate inside the archive.
"""

import os
import tarfile
from pathlib import Path

# === CONFIGURATION ===
INPUT_DIR = "output_filtered/modified_per_year"
OUTPUT_DIR = "output_filtered/compressed"
MAX_ARCHIVE_SIZE_GB = 10


def get_file_size_gb(file_path: str) -> float:
    """Get file size in GB"""
    return os.path.getsize(file_path) / (1024 ** 3)


def group_files_by_size(files_with_sizes: list, max_size_gb: float) -> list:
    """
    Group files into bins where each bin total size is <= max_size_gb.
    Each JSON file stays separate - they are just grouped into the same archive.
    """
    groups = []
    current_group = []
    current_size = 0
    
    for file_path, size_gb in files_with_sizes:
        # If this single file is >= max_size, it gets its own group
        if size_gb >= max_size_gb:
            if current_group:
                groups.append(current_group)
                current_group = []
                current_size = 0
            groups.append([(file_path, size_gb)])
            continue
        
        # If adding this file would exceed max, start new group
        if current_size + size_gb > max_size_gb and current_group:
            groups.append(current_group)
            current_group = []
            current_size = 0
        
        current_group.append((file_path, size_gb))
        current_size += size_gb
    
    # Don't forget the last group
    if current_group:
        groups.append(current_group)
    
    return groups


def create_tar_gz(files: list, output_file: Path):
    """Create a tar.gz archive with multiple JSON files inside"""
    with tarfile.open(output_file, "w:gz", compresslevel=9) as tar:
        for file_path, _ in files:
            # Add file to archive with just its filename (not full path)
            tar.add(file_path, arcname=Path(file_path).name)


def compress_dataset(input_dir: str, output_dir: str, max_size_gb: float):
    """Compress JSON files into grouped tar.gz archives"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all JSON files and get their sizes
    json_files = sorted(input_path.glob("papers_*.json"))
    
    if not json_files:
        print("No JSON files found!")
        return
    
    files_with_sizes = []
    for f in json_files:
        size = get_file_size_gb(str(f))
        files_with_sizes.append((str(f), size))
        print(f"  {f.name}: {size:.2f} GB")
    
    total_size = sum(s for _, s in files_with_sizes)
    print(f"\nTotal: {len(json_files)} files, {total_size:.2f} GB")
    print(f"Max archive size: {max_size_gb} GB")
    print()
    
    # Group files by size
    groups = group_files_by_size(files_with_sizes, max_size_gb)
    
    print(f"Will create {len(groups)} archive(s):")
    print()
    
    # Create archives
    for i, group in enumerate(groups, 1):
        # Get year range for naming
        years = []
        for file_path, _ in group:
            filename = Path(file_path).stem  # papers_1980
            year = filename.replace("papers_", "")
            years.append(year)
        
        # Name the archive based on year range
        if len(years) == 1:
            archive_name = f"papers_{years[0]}.tar.gz"
        else:
            archive_name = f"papers_{years[0]}-{years[-1]}.tar.gz"
        
        output_file = output_path / archive_name
        group_size = sum(s for _, s in group)
        
        print(f"Archive {i}: {archive_name}")
        print(f"  Files: {len(group)}")
        for file_path, size in group:
            print(f"    - {Path(file_path).name} ({size:.2f} GB)")
        print(f"  Total size (uncompressed): {group_size:.2f} GB")
        
        print(f"  Creating archive...")
        create_tar_gz(group, output_file)
        
        compressed_size = get_file_size_gb(str(output_file))
        ratio = group_size / compressed_size if compressed_size > 0 else 0
        print(f"  Compressed size: {compressed_size:.2f} GB")
        print(f"  Compression ratio: {ratio:.1f}x")
        print()
    
    # Summary
    print("=" * 60)
    print("COMPRESSION COMPLETE")
    print("=" * 60)
    print(f"Created {len(groups)} archive(s) in {output_dir}")


if __name__ == "__main__":
    print("=" * 60)
    print("TASK 2: Compress JSON Files (Max 10GB per Archive)")
    print("=" * 60)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    compress_dataset(INPUT_DIR, OUTPUT_DIR, MAX_ARCHIVE_SIZE_GB)
