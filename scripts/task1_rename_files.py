"""
Task 1: Rename JSON files from papers_(year)_modified.json to papers_(year).json
in output_filtered/modified_per_year folder
"""

import os
import re
from pathlib import Path

# === CONFIGURATION ===
INPUT_DIR = "output_filtered/modified_per_year"

def rename_modified_files(input_dir: str, dry_run: bool = True):
    """
    Rename files from papers_(year)_modified.json to papers_(year).json
    
    Args:
        input_dir: Directory containing the JSON files
        dry_run: If True, only print what would be done without renaming
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Error: Directory '{input_dir}' does not exist.")
        return
    
    # Pattern to match papers_YYYY_modified.json
    pattern = re.compile(r'^papers_(\d{4})_modified\.json$')
    
    files_found = 0
    files_renamed = 0
    
    for file_path in sorted(input_path.glob("papers_*_modified.json")):
        filename = file_path.name
        match = pattern.match(filename)
        
        if match:
            year = match.group(1)
            new_filename = f"papers_{year}.json"
            new_file_path = file_path.parent / new_filename
            
            files_found += 1
            
            if dry_run:
                print(f"  [DRY RUN] Would rename: {filename} -> {new_filename}")
            else:
                # Check if target file already exists
                if new_file_path.exists():
                    print(f"  [SKIP] Target file already exists: {new_filename}")
                    continue
                
                try:
                    file_path.rename(new_file_path)
                    print(f"  [RENAMED] {filename} -> {new_filename}")
                    files_renamed += 1
                except Exception as e:
                    print(f"  [ERROR] Failed to rename {filename}: {e}")
    
    print("\n" + "="*60)
    if dry_run:
        print(f"DRY RUN COMPLETE: {files_found} files would be renamed")
        print("Run with dry_run=False to actually rename files")
    else:
        print(f"RENAME COMPLETE: {files_renamed}/{files_found} files renamed")
    print("="*60)

if __name__ == "__main__":
    print("="*60)
    print("TASK 1: Rename papers_(year)_modified.json to papers_(year).json")
    print("="*60)
    print(f"Input directory: {INPUT_DIR}\n")
    
    # First do a dry run to show what will happen
    print("--- DRY RUN ---")
    rename_modified_files(INPUT_DIR, dry_run=True)
    
    # Uncomment the following lines to actually rename files:
    # print("\n--- ACTUAL RENAME ---")
    # rename_modified_files(INPUT_DIR, dry_run=False)
