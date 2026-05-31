import argparse
import json
import logging
import re
import sys
from pathlib import Path

try:
    import ijson
    HAS_IJSON = True
except ImportError:
    HAS_IJSON = False

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

BYTES_PER_MB = 1024 * 1024


def _extract_year_from_filename(name: str) -> int | None:
    """Parse the year from filenames like papers_2000.json or 2020_papers.json."""
    m = re.search(r"\b(1[89]\d\d|20[0-2]\d)\b", name)
    return int(m.group(1)) if m else None


def _stream_papers(src: Path):
    """Yield paper dicts from a JSON file, auto-detecting array vs dict-wrapped."""
    with open(src, "rb") as fh:
        peek = fh.read(4096).lstrip()
        fh.seek(0)
        if peek.startswith(b"["):
            yield from ijson.items(fh, "item")
            return
        for key in ("papers", "nodes", "data", "results"):
            fh.seek(0)
            try:
                first = next(ijson.items(fh, f"{key}.item"), None)
                if first is not None:
                    fh.seek(0)
                    yield from ijson.items(fh, f"{key}.item")
                    return
            except Exception:
                continue
    logger.warning(f"Could not find a paper array in {src.name}")


def make_subset(src: Path, dst: Path, max_mb: float = 500.0, max_count: int = None) -> dict:
    if not HAS_IJSON:
        logger.error("ijson is required. pip install ijson")
        sys.exit(1)

    max_bytes      = int(max_mb * BYTES_PER_MB)
    source_size_mb = src.stat().st_size / BYTES_PER_MB
    logger.info(f"  {src.name}  ({source_size_mb:.0f} MB)  →  {dst.name}")

    written   = 0
    out_bytes = 0
    first     = True

    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as out_fh:
        out_fh.write("[\n")
        for paper in _stream_papers(src):
            if not isinstance(paper, dict):
                continue
            encoded      = json.dumps(paper, ensure_ascii=False)
            record_bytes = len(encoded.encode("utf-8"))
            if out_bytes + record_bytes > max_bytes:
                logger.info(f"    Reached {max_mb} MB limit at {written:,} papers")
                break
            if max_count and written >= max_count:
                logger.info(f"    Reached {max_count:,} paper limit")
                break
            if not first:
                out_fh.write(",\n")
            out_fh.write(encoded)
            first      = False
            written    += 1
            out_bytes  += record_bytes
            if written % 50000 == 0:
                logger.info(f"    {written:,} papers, {out_bytes/BYTES_PER_MB:.1f} MB so far")
        out_fh.write("\n]\n")

    actual_mb = dst.stat().st_size / BYTES_PER_MB
    return {"file": src.name, "papers_written": written, "output_mb": round(actual_mb, 1), "source_mb": round(source_size_mb, 1)}


def process_directory(
    input_dir: Path,
    output_dir: Path,
    max_mb: float,
    min_size_mb: float,
    year_min: int | None,
    year_max: int | None,
    max_count: int | None,
) -> list:
    json_files = sorted(input_dir.glob("*.json"))
    # Exclude already-created samples / chunks
    candidates = [f for f in json_files if "_sample" not in f.stem and "_chunk_" not in f.stem]

    selected = []
    for f in candidates:
        size_mb = f.stat().st_size / BYTES_PER_MB
        year    = _extract_year_from_filename(f.name)

        if min_size_mb and size_mb < min_size_mb:
            continue
        if year_min and (year is None or year < year_min):
            continue
        if year_max and (year is not None and year > year_max):
            continue
        selected.append(f)

    if not selected:
        logger.warning("No files matched the filters. Check --min-size / --year-min / --year-max.")
        return []

    logger.info(f"Processing {len(selected)} file(s) from {input_dir}")
    results = []
    for f in selected:
        dst  = output_dir / f"{f.stem}_sample.json"
        result = make_subset(src=f, dst=dst, max_mb=max_mb, max_count=max_count)
        results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Create size-limited subsets from large JSON paper files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input: single file or directory
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--input",     type=Path, help="Single source JSON file")
    src_group.add_argument("--input-dir", type=Path, help="Directory containing JSON paper files")

    # Output
    parser.add_argument("--output",     type=Path, default=None, help="Output path (single-file mode only)")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory (directory mode)")

    # Subset size
    parser.add_argument("--max-size", type=float, default=500.0, metavar="MB",
                        help="Maximum output size per file in MB (default: 500)")
    parser.add_argument("--count",    type=int,   default=None,  metavar="N",
                        help="Stop after N papers regardless of size")

    # Directory-mode filters
    parser.add_argument("--min-size",  type=float, default=None, metavar="MB",
                        help="Only process files larger than this MB (e.g. 2000 for 2 GB+)")
    parser.add_argument("--year-min",  type=int,   default=None,
                        help="Only process files whose year (from filename) >= this value (e.g. 2000)")
    parser.add_argument("--year-max",  type=int,   default=None,
                        help="Only process files whose year (from filename) <= this value (e.g. 2024)")

    args = parser.parse_args()

    if not HAS_IJSON:
        logger.error("ijson is required. pip install ijson")
        sys.exit(1)

    # ── Single-file mode ──────────────────────────────────────────────────────
    if args.input:
        if not args.input.exists():
            logger.error(f"File not found: {args.input}")
            sys.exit(1)
        dst = args.output or args.input.parent / f"{args.input.stem}_sample.json"
        result = make_subset(src=args.input, dst=dst, max_mb=args.max_size, max_count=args.count)
        print(f"\n{result['source_mb']:.0f} MB  →  {result['output_mb']:.0f} MB  ({result['papers_written']:,} papers)")
        print(f"\nBenchmark:")
        print(f"  mkdir -p /tmp/subset && cp {dst} /tmp/subset/")
        print(f"  time python main_stages_1_2.py --input-dir /tmp/subset/ --no-auto-chunk")
        return

    # ── Directory mode ────────────────────────────────────────────────────────
    if not args.input_dir.exists():
        logger.error(f"Directory not found: {args.input_dir}")
        sys.exit(1)

    output_dir = args.output_dir or args.input_dir

    results = process_directory(
        input_dir=args.input_dir,
        output_dir=output_dir,
        max_mb=args.max_size,
        min_size_mb=args.min_size,
        year_min=args.year_min,
        year_max=args.year_max,
        max_count=args.count,
    )

    if not results:
        return

    print(f"\n{'File':<35} {'Source':>10} {'Subset':>10} {'Papers':>12}")
    print("-" * 70)
    for r in results:
        print(f"{r['file']:<35} {r['source_mb']:>8.0f} MB {r['output_mb']:>8.0f} MB {r['papers_written']:>12,}")

    total_papers = sum(r["papers_written"] for r in results)
    print(f"\nTotal subset papers: {total_papers:,}  in  {output_dir}")
    print(f"\nBenchmark:")
    print(f"  time python main_stages_1_2.py --input-dir {output_dir} --no-auto-chunk")


if __name__ == "__main__":
    main()
