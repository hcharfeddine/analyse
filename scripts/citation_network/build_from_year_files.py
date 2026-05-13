#!/usr/bin/env python3
"""
Build a fresh graph_index.db from a folder of per-year JSON files.

Each file is expected to contain papers (either as a top-level JSON array or
under a key like 'papers' / 'nodes'). Every paper should have:
    - paper_id (or 'id')
    - title (optional)
    - year (optional)
    - cited_by_count (optional)
    - references (or 'citations' / 'cited_papers' / 'refs') - list of paper IDs it cites

Edges are derived from each paper's references list. The resulting database
has the same schema used by compute_layout.py and render_tiles.py.

Usage:
    python scripts/citation_network/build_from_year_files.py \
        --input-dir "D:\\path\\to\\modified_per_year" \
        --db public/data/graph_index.db \
        [--commit-every 200000] \
        [--reset]

Files are processed in sorted order. If interrupted, simply rerun: files
already marked complete in the `processed_files` table are skipped.
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Iterator, Optional


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


# ---------- streaming JSON reader (handles top-level array OR {"papers": [...]}) ----------

def iter_papers(file_path: Path, chunk_size: int = 1024 * 1024) -> Iterator[dict]:
    """Stream paper dicts out of a JSON file regardless of whether the top level
    is an array or an object containing an array under a known key."""
    decoder = json.JSONDecoder()
    candidate_keys = ('"papers"', '"nodes"', '"data"', '"results"')

    with file_path.open("r", encoding="utf-8") as handle:
        # Read enough of the file to figure out whether it's an array or object
        prefix = ""
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                if not prefix.strip():
                    return
                break
            prefix += chunk
            stripped = prefix.lstrip()
            if not stripped:
                continue
            first_char = stripped[0]
            if first_char == "[":
                # Top-level array - position buffer right after the [
                idx = prefix.find("[")
                buffer = prefix[idx + 1:]
                yield from _stream_items(handle, buffer, decoder, chunk_size)
                return
            if first_char == "{":
                # Object - find one of the candidate keys, then [
                if any(k in prefix for k in candidate_keys):
                    break
                # otherwise keep reading
                continue
            # Not JSON - bail
            return

        # We have an object - locate the candidate key and seek into the array
        for key in candidate_keys:
            key_pos = prefix.find(key)
            if key_pos == -1:
                continue
            colon_pos = prefix.find(":", key_pos + len(key))
            if colon_pos == -1:
                continue
            bracket_pos = prefix.find("[", colon_pos + 1)
            if bracket_pos == -1:
                continue
            buffer = prefix[bracket_pos + 1:]
            yield from _stream_items(handle, buffer, decoder, chunk_size)
            return

        log(f"  WARNING: could not find papers array in {file_path.name}")


def _stream_items(handle, buffer: str, decoder, chunk_size: int) -> Iterator[dict]:
    """Yield dicts from an open JSON array, refilling the buffer as needed."""
    while True:
        if not buffer:
            chunk = handle.read(chunk_size)
            if not chunk:
                return
            buffer += chunk

        buffer = buffer.lstrip()
        if not buffer:
            continue
        if buffer[0] == "]":
            return
        if buffer[0] == ",":
            buffer = buffer[1:]
            continue

        try:
            item, idx = decoder.raw_decode(buffer)
            if isinstance(item, dict):
                yield item
            buffer = buffer[idx:]
        except json.JSONDecodeError:
            chunk = handle.read(chunk_size)
            if not chunk:
                return
            buffer += chunk


# ---------- field extraction helpers ----------

REFERENCE_KEYS = ("references", "citations", "cited_papers", "refs", "outgoing_citations")


def get_paper_id(paper: dict) -> Optional[str]:
    value = paper.get("paper_id") or paper.get("id") or paper.get("openalex_id")
    return str(value).strip() if value else None


def get_references(paper: dict):
    for key in REFERENCE_KEYS:
        refs = paper.get(key)
        if refs:
            for ref in refs:
                if isinstance(ref, str):
                    yield ref.strip()
                elif isinstance(ref, dict):
                    rid = ref.get("paper_id") or ref.get("id") or ref.get("openalex_id")
                    if rid:
                        yield str(rid).strip()
            return


def safe_int(value, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


# ---------- SQLite setup ----------

def open_database(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-200000")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            paper_id TEXT PRIMARY KEY,
            title TEXT,
            year INTEGER,
            cited_by_count INTEGER,
            in_degree INTEGER DEFAULT 0,
            out_degree INTEGER DEFAULT 0,
            cluster_id INTEGER,
            field_of_study TEXT,
            authors TEXT,
            abstract TEXT,
            raw_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS edges (
            source TEXT,
            target TEXT,
            PRIMARY KEY (source, target)
        ) WITHOUT ROWID
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_files (
            filename TEXT PRIMARY KEY,
            papers INTEGER,
            edges INTEGER,
            finished_at TEXT
        )
        """
    )
    conn.commit()
    return conn


def reset_database(db_path: Path) -> None:
    if db_path.exists():
        log(f"Deleting existing database {db_path} (--reset)")
        db_path.unlink()
    # Also wipe wal/shm files if present
    for suffix in ("-wal", "-shm"):
        side = db_path.with_name(db_path.name + suffix)
        if side.exists():
            side.unlink()


# ---------- main processing ----------

def process_file(conn: sqlite3.Connection, file_path: Path, commit_every: int) -> tuple:
    paper_count = 0
    edge_count = 0
    node_buffer = []
    edge_buffer = []
    out_degree_increment = {}
    in_degree_increment = {}

    insert_node_sql = (
        "INSERT INTO nodes (paper_id, title, year, cited_by_count, out_degree) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(paper_id) DO UPDATE SET "
        "  title=COALESCE(excluded.title, nodes.title), "
        "  year=COALESCE(excluded.year, nodes.year), "
        "  cited_by_count=COALESCE(excluded.cited_by_count, nodes.cited_by_count), "
        "  out_degree=nodes.out_degree + excluded.out_degree"
    )
    insert_edge_sql = "INSERT OR IGNORE INTO edges (source, target) VALUES (?, ?)"

    def flush() -> None:
        nonlocal node_buffer, edge_buffer
        if node_buffer:
            conn.executemany(insert_node_sql, node_buffer)
            node_buffer = []
        if edge_buffer:
            conn.executemany(insert_edge_sql, edge_buffer)
            edge_buffer = []
        # Apply in-degree increments (target nodes might not exist yet - ensure they do)
        if in_degree_increment:
            target_rows = [(tid,) for tid in in_degree_increment]
            conn.executemany(
                "INSERT OR IGNORE INTO nodes (paper_id) VALUES (?)",
                target_rows,
            )
            conn.executemany(
                "UPDATE nodes SET in_degree = COALESCE(in_degree, 0) + ? WHERE paper_id = ?",
                [(count, tid) for tid, count in in_degree_increment.items()],
            )
            in_degree_increment.clear()
        conn.commit()

    for paper in iter_papers(file_path):
        pid = get_paper_id(paper)
        if not pid:
            continue
        title = paper.get("title")
        year = safe_int(paper.get("year"))
        cited = safe_int(paper.get("cited_by_count") or paper.get("citation_count"))

        refs = list(get_references(paper))
        out_deg_local = len(refs)
        node_buffer.append((pid, title, year if year else None, cited, out_deg_local))

        for ref_id in refs:
            if ref_id == pid:
                continue
            edge_buffer.append((pid, ref_id))
            in_degree_increment[ref_id] = in_degree_increment.get(ref_id, 0) + 1
            edge_count += 1

        paper_count += 1
        if paper_count % commit_every == 0:
            flush()
            log(f"    {file_path.name}: {paper_count:,} papers, {edge_count:,} edges so far...")

    flush()
    return paper_count, edge_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Build graph_index.db from a folder of per-year paper JSON files")
    parser.add_argument("--input-dir", required=True, help="Directory containing per-year JSON files")
    parser.add_argument("--db", default="public/data/graph_index.db", help="Output SQLite database path")
    parser.add_argument("--commit-every", type=int, default=200000, help="Commit after this many papers per file")
    parser.add_argument("--reset", action="store_true", help="Delete the existing database and start fresh")
    parser.add_argument("--pattern", default="*.json", help="Filename pattern to include")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        log(f"Input directory not found: {input_dir}")
        sys.exit(1)

    db_path = Path(args.db)
    if args.reset:
        reset_database(db_path)

    files = sorted(input_dir.glob(args.pattern))
    if not files:
        log(f"No files matching {args.pattern} in {input_dir}")
        sys.exit(1)
    log(f"Found {len(files)} file(s) in {input_dir}")

    conn = open_database(db_path)
    done = {row[0] for row in conn.execute("SELECT filename FROM processed_files").fetchall()}
    if done:
        log(f"Skipping {len(done)} already-processed file(s) from previous run")

    total_papers = 0
    total_edges = 0
    overall_start = time.time()

    for file_path in files:
        if file_path.name in done:
            continue
        size_gb = file_path.stat().st_size / (1024 ** 3)
        log(f"\nProcessing {file_path.name} ({size_gb:.2f} GB)...")
        start = time.time()
        try:
            papers, edges = process_file(conn, file_path, args.commit_every)
        except Exception as exc:
            log(f"  FAILED on {file_path.name}: {exc}")
            log("  You can rerun this command to skip already-finished files and retry.")
            raise
        elapsed = time.time() - start
        total_papers += papers
        total_edges += edges
        conn.execute(
            "INSERT OR REPLACE INTO processed_files (filename, papers, edges, finished_at) VALUES (?, ?, ?, datetime('now'))",
            (file_path.name, papers, edges),
        )
        conn.commit()
        log(f"  Finished {file_path.name}: {papers:,} papers, {edges:,} edges in {elapsed/60:.1f} min")

    log("\nFinalizing database...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_year ON nodes(year)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_cited ON nodes(cited_by_count)")
    conn.commit()

    node_total = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    edge_total = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('total_nodes', ?)", (str(node_total),))
    conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('total_edges', ?)", (str(edge_total),))
    conn.commit()
    conn.close()

    elapsed = time.time() - overall_start
    log("")
    log("Done.")
    log(f"  Database: {db_path}")
    log(f"  Total papers in DB: {node_total:,}")
    log(f"  Total edges in DB: {edge_total:,}")
    log(f"  Files processed this run: {total_papers:,} papers / {total_edges:,} edges")
    log(f"  Total time this run: {elapsed/60:.1f} min")
    log("")
    log("Next steps:")
    log(f"  python scripts/citation_network/compute_layout.py --db {db_path}")
    log(f"  python scripts/citation_network/render_tiles.py --db {db_path} --max-zoom 6")


if __name__ == "__main__":
    main()
