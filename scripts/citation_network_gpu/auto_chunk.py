#!/usr/bin/env python3
"""
auto_chunk.py — Automatically split JSON paper files larger than MAX_SIZE_MB.

Scans an input directory for *.json files. Any file exceeding the size limit
is stream-split into sequential chunks:
  <stem>_chunk_000.json, <stem>_chunk_001.json, ...

The original oversized file is kept by default (use --remove-originals to delete it).
Files already under the limit are left untouched.

Usage:
    python auto_chunk.py --input-dir /path/to/papers
    python auto_chunk.py --input-dir /path/to/papers --max-size 400
    python auto_chunk.py --input-dir /path/to/papers --remove-originals

Can also be called from Python:
    from auto_chunk import auto_chunk_directory
    result = auto_chunk_directory(Path("/path/to/papers"), max_mb=500)
"""

import argparse
import json
import logging
import sys
from pathlib import Path

try:
    import ijson
    HAS_IJSON = True
except ImportError:
    HAS_IJSON = False

logger = logging.getLogger(__name__)

DEFAULT_MAX_MB = 500
BYTES_PER_MB = 1024 * 1024
# Leave a small buffer so chunks stay safely under the limit
CHUNK_TARGET_FRACTION = 0.92


def _flush_chunk(records: list, stem: str, idx: int, output_dir: Path) -> Path:
    """Write a list of records as a JSON array chunk file."""
    out_path = output_dir / f"{stem}_chunk_{idx:03d}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False)
    size_mb = out_path.stat().st_size / BYTES_PER_MB
    logger.info(f"  Wrote chunk {idx:03d}: {out_path.name}  "
                f"({len(records):,} records, {size_mb:.1f} MB)")
    return out_path


def split_json_file(src: Path, max_bytes: int, output_dir: Path) -> list:
    """
    Stream-split a large JSON array file into chunks of at most max_bytes each.
    Returns a list of written chunk Paths.
    """
    target_bytes = int(max_bytes * CHUNK_TARGET_FRACTION)
    chunks: list = []
    chunk_idx = 0
    current_records: list = []
    current_size = 0

    # Strip any existing _chunk_NNN suffix to avoid double-chunking
    stem = src.stem
    if "_chunk_" in stem:
        stem = stem[:stem.rfind("_chunk_")]

    if HAS_IJSON:
        with open(src, "rb") as fh:
            for record in ijson.items(fh, "item"):
                encoded = json.dumps(record, ensure_ascii=False).encode("utf-8")
                record_bytes = len(encoded)
                if current_size + record_bytes > target_bytes and current_records:
                    chunks.append(_flush_chunk(current_records, stem, chunk_idx, output_dir))
                    chunk_idx += 1
                    current_records = []
                    current_size = 0
                current_records.append(record)
                current_size += record_bytes
    else:
        logger.warning("ijson not available — loading whole file into memory for splitting "
                       "(install ijson for true streaming: pip install ijson)")
        with open(src, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            logger.warning(f"  {src.name}: top-level value is not a JSON array — skipping split")
            return []
        for record in data:
            encoded = json.dumps(record, ensure_ascii=False).encode("utf-8")
            record_bytes = len(encoded)
            if current_size + record_bytes > target_bytes and current_records:
                chunks.append(_flush_chunk(current_records, stem, chunk_idx, output_dir))
                chunk_idx += 1
                current_records = []
                current_size = 0
            current_records.append(record)
            current_size += record_bytes

    if current_records:
        chunks.append(_flush_chunk(current_records, stem, chunk_idx, output_dir))

    return chunks


def auto_chunk_directory(input_dir: Path, max_mb: float = DEFAULT_MAX_MB,
                          remove_originals: bool = False) -> dict:
    """
    Scan input_dir for JSON files exceeding max_mb and split them automatically.

    Args:
        input_dir:        Directory to scan (only *.json files are checked).
        max_mb:           Size limit in MB. Files above this are split.
        remove_originals: If True, delete the original after successful splitting.

    Returns:
        Summary dict: {files_checked, files_split, chunks_created, skipped}
    """
    if not input_dir.is_dir():
        raise ValueError(f"Input directory does not exist: {input_dir}")

    max_bytes = int(max_mb * BYTES_PER_MB)
    json_files = sorted(input_dir.glob("*.json"))

    # Exclude files that are already chunks (avoid re-splitting)
    non_chunk_files = [f for f in json_files if "_chunk_" not in f.stem]
    oversized = [f for f in non_chunk_files if f.stat().st_size > max_bytes]

    if not oversized:
        logger.info(
            f"[auto_chunk] All {len(non_chunk_files)} JSON file(s) in {input_dir} "
            f"are within the {max_mb} MB limit. No splitting needed."
        )
        return {
            "files_checked": len(json_files),
            "files_split": 0,
            "chunks_created": 0,
            "skipped": 0,
        }

    logger.info(
        f"[auto_chunk] Found {len(oversized)} oversized file(s) "
        f"(>{max_mb} MB) in {input_dir} — splitting..."
    )

    total_chunks = 0
    skipped = 0

    for f in oversized:
        size_mb = f.stat().st_size / BYTES_PER_MB
        logger.info(f"[auto_chunk] Splitting: {f.name}  ({size_mb:.0f} MB → ~{max_mb} MB chunks)")
        try:
            chunks = split_json_file(f, max_bytes, input_dir)
            if not chunks:
                logger.warning(f"[auto_chunk] No chunks produced for {f.name} — skipping")
                skipped += 1
                continue
            total_chunks += len(chunks)
            if remove_originals:
                f.unlink()
                logger.info(f"[auto_chunk] Removed original: {f.name}")
            else:
                logger.info(f"[auto_chunk] Original kept: {f.name}  "
                            f"(use --remove-originals to delete after splitting)")
        except Exception as exc:
            logger.error(f"[auto_chunk] Error splitting {f.name}: {exc}")
            skipped += 1

    logger.info(
        f"[auto_chunk] Done. Split {len(oversized) - skipped} file(s) into "
        f"{total_chunks} chunk(s). Skipped {skipped}."
    )
    return {
        "files_checked": len(json_files),
        "files_split": len(oversized) - skipped,
        "chunks_created": total_chunks,
        "skipped": skipped,
    }


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    parser = argparse.ArgumentParser(
        description="Auto-split JSON paper files larger than MAX_SIZE_MB into chunks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input-dir", type=Path, required=True,
        help="Directory containing JSON paper files to check",
    )
    parser.add_argument(
        "--max-size", type=float, default=DEFAULT_MAX_MB,
        metavar="MB",
        help=f"Maximum file size in MB before splitting (default: {DEFAULT_MAX_MB})",
    )
    parser.add_argument(
        "--remove-originals", action="store_true", default=False,
        help="Delete original oversized files after successful splitting",
    )

    args = parser.parse_args()

    if not args.input_dir.exists():
        logger.error(f"Input directory does not exist: {args.input_dir}")
        sys.exit(1)

    result = auto_chunk_directory(
        input_dir=args.input_dir,
        max_mb=args.max_size,
        remove_originals=args.remove_originals,
    )

    print(f"\nSummary:")
    print(f"  Files checked : {result['files_checked']}")
    print(f"  Files split   : {result['files_split']}")
    print(f"  Chunks created: {result['chunks_created']}")
    print(f"  Skipped       : {result['skipped']}")


if __name__ == "__main__":
    main()
