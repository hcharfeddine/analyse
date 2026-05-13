#!/usr/bin/env python3
"""
Stream a very large processed_graph.json into:
1. A SQLite database for server-side querying.
2. A small preview JSON for browser visualization.

This script is designed for files that are too large to load with json.load().
"""

import argparse
import heapq
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def iter_array_items(file_path: Path, array_name: str, chunk_size: int = 1024 * 1024) -> Iterator[dict]:
    decoder = json.JSONDecoder()
    target = f'"{array_name}"'
    buffer = ""
    in_array = False
    finished = False

    with file_path.open("r", encoding="utf-8") as handle:
        while not in_array:
            chunk = handle.read(chunk_size)
            if not chunk:
                return
            buffer += chunk
            key_pos = buffer.find(target)
            if key_pos == -1:
                buffer = buffer[-len(target):]
                continue
            colon_pos = buffer.find(":", key_pos + len(target))
            if colon_pos == -1:
                continue
            bracket_pos = buffer.find("[", colon_pos + 1)
            if bracket_pos == -1:
                continue
            buffer = buffer[bracket_pos + 1:]
            in_array = True

        while not finished:
            if not buffer:
                chunk = handle.read(chunk_size)
                if not chunk:
                    return
                buffer += chunk

            buffer = buffer.lstrip()
            if not buffer:
                continue

            if buffer[0] == "]":
                finished = True
                break

            if buffer[0] == ",":
                buffer = buffer[1:]
                continue

            try:
                item, index = decoder.raw_decode(buffer)
                if isinstance(item, dict):
                    yield item
                buffer = buffer[index:]
            except json.JSONDecodeError:
                chunk = handle.read(chunk_size)
                if not chunk:
                    raise
                buffer += chunk


def normalize_authors(authors) -> str:
    if authors is None:
        return "[]"
    try:
        return json.dumps(authors, ensure_ascii=False)
    except TypeError:
        return "[]"


def get_paper_id(node: dict) -> Optional[str]:
    value = node.get("paper_id") or node.get("id")
    return str(value) if value else None


def node_score(node: dict) -> int:
    cited = node.get("cited_by_count") or node.get("citation_count") or 0
    in_degree = node.get("in_degree") or 0
    out_degree = node.get("out_degree") or 0
    try:
        return int(cited) + int(in_degree) + int(out_degree)
    except (TypeError, ValueError):
        return 0


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
            in_degree INTEGER,
            out_degree INTEGER,
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
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            PRIMARY KEY (source, target)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    return conn


def insert_node(conn: sqlite3.Connection, node: dict) -> None:
    paper_id = get_paper_id(node)
    if not paper_id:
        return
    conn.execute(
        """
        INSERT OR IGNORE INTO nodes (
            paper_id, title, year, cited_by_count, in_degree, out_degree,
            cluster_id, field_of_study, authors, abstract, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            paper_id,
            node.get("title") or "Untitled paper",
            node.get("year"),
            node.get("cited_by_count") or node.get("citation_count") or 0,
            node.get("in_degree") or 0,
            node.get("out_degree") or 0,
            node.get("cluster_id") if node.get("cluster_id") is not None else -1,
            node.get("field_of_study") or node.get("primary_field") or "",
            normalize_authors(node.get("authors")),
            (node.get("abstract") or "")[:4000],
            json.dumps(node, ensure_ascii=False),
        ),
    )


def insert_edge(conn: sqlite3.Connection, edge: dict) -> Optional[Tuple[str, str]]:
    source = edge.get("source") or edge.get("from")
    target = edge.get("target") or edge.get("to")
    if not source or not target:
        return None
    source = str(source)
    target = str(target)
    conn.execute("INSERT OR IGNORE INTO edges (source, target) VALUES (?, ?)", (source, target))
    return source, target


def create_indexes(conn: sqlite3.Connection) -> None:
    log("Creating indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_year ON nodes(year)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_cluster ON nodes(cluster_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_cited ON nodes(cited_by_count DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target)")
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(paper_id, title, abstract, field_of_study)")
        conn.execute("DELETE FROM nodes_fts")
        conn.execute("INSERT INTO nodes_fts (paper_id, title, abstract, field_of_study) SELECT paper_id, title, abstract, field_of_study FROM nodes")
    except sqlite3.OperationalError as exc:
        log(f"FTS search index skipped: {exc}")
    conn.commit()


def write_preview(preview_path: Path, preview_nodes: Dict[str, dict], preview_edges: List[dict], total_nodes: int, total_edges: int) -> None:
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    nodes = list(preview_nodes.values())
    clusters: Dict[str, dict] = {}
    for node in nodes:
        cluster_id = str(node.get("cluster_id", -1))
        clusters.setdefault(cluster_id, {"id": node.get("cluster_id", -1), "size": 0})
        clusters[cluster_id]["size"] += 1

    payload = {
        "nodes": nodes,
        "edges": preview_edges,
        "clusters": clusters,
        "statistics": {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "visible_nodes": len(nodes),
            "visible_edges": len(preview_edges),
            "total_clusters": len(clusters),
            "source": "processed_graph.json preview index",
        },
    }
    with preview_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


def build_index(input_path: Path, db_path: Path, preview_path: Path, max_preview_nodes: int, max_preview_edges: int, commit_every: int) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    conn = open_database(db_path)
    top_heap: List[Tuple[int, str]] = []
    top_nodes: Dict[str, dict] = {}

    already_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    already_edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    if already_nodes:
        log(f"Resuming: {already_nodes:,} nodes already in database, will skip them.")
    if already_edges:
        log(f"Resuming: {already_edges:,} edges already in database, will skip them.")

    total_nodes = already_nodes
    seen_nodes = 0

    log(f"Reading nodes from {input_path}...")
    for node in iter_array_items(input_path, "nodes"):
        paper_id = get_paper_id(node)
        if not paper_id:
            continue
        seen_nodes += 1
        if seen_nodes <= already_nodes:
            if seen_nodes % 1_000_000 == 0:
                log(f"Skipping previously processed nodes: {seen_nodes:,}/{already_nodes:,}")
            continue
        insert_node(conn, node)
        total_nodes += 1

        score = node_score(node)
        preview_node = {
            "paper_id": paper_id,
            "title": node.get("title") or "Untitled paper",
            "year": node.get("year"),
            "cited_by_count": node.get("cited_by_count") or node.get("citation_count") or 0,
            "field_of_study": node.get("field_of_study") or node.get("primary_field") or "",
            "cluster_id": node.get("cluster_id") if node.get("cluster_id") is not None else -1,
            "in_degree": node.get("in_degree") or 0,
            "out_degree": node.get("out_degree") or 0,
            "abstract": (node.get("abstract") or "")[:1000],
            "keywords": node.get("keywords") or [],
        }

        if len(top_heap) < max_preview_nodes:
            heapq.heappush(top_heap, (score, paper_id))
            top_nodes[paper_id] = preview_node
        elif score > top_heap[0][0]:
            _, removed_id = heapq.heappushpop(top_heap, (score, paper_id))
            top_nodes.pop(removed_id, None)
            top_nodes[paper_id] = preview_node

        if total_nodes % commit_every == 0:
            conn.commit()
            log(f"Indexed {total_nodes:,} nodes...")

    conn.commit()
    preview_ids = set(top_nodes.keys())
    preview_edges: List[dict] = []
    total_edges = already_edges
    seen_edges = 0

    log("Reading edges...")
    for edge in iter_array_items(input_path, "edges"):
        seen_edges += 1
        if seen_edges <= already_edges:
            if seen_edges % 5_000_000 == 0:
                log(f"Skipping previously processed edges: {seen_edges:,}/{already_edges:,}")
            continue
        inserted = insert_edge(conn, edge)
        if not inserted:
            continue
        total_edges += 1
        source, target = inserted
        if len(preview_edges) < max_preview_edges and source in preview_ids and target in preview_ids:
            preview_edges.append({"source": source, "target": target})

        if total_edges % commit_every == 0:
            conn.commit()
            log(f"Indexed {total_edges:,} edges...")

    conn.commit()
    create_indexes(conn)

    log("Rebuilding preview from database (connected subgraph from actual edges)...")
    from collections import Counter

    # Step 1: scan the edges table directly to compute the REAL degree of every paper.
    # We can't trust in_degree/out_degree fields stored on nodes if they don't match
    # the actual edges. With ~500K edges this fits comfortably in memory.
    log("  Scanning edges table to compute real paper degree...")
    degree: Counter = Counter()
    edge_count = 0
    for s, t in conn.execute("SELECT source, target FROM edges"):
        degree[s] += 1
        degree[t] += 1
        edge_count += 1
    log(f"  Edges scanned: {edge_count:,}; papers with at least one edge: {len(degree):,}")

    # Step 2: pick the most-connected papers (these are guaranteed to have edges).
    if degree:
        ranked = [pid for pid, _ in degree.most_common(max_preview_nodes)]
    else:
        # Fallback: dataset has no edges at all - just pick top by citation count
        log("  WARNING: no edges in dataset, falling back to top-cited papers")
        ranked_rows = conn.execute(
            "SELECT paper_id FROM nodes ORDER BY COALESCE(cited_by_count,0) DESC LIMIT ?",
            (max_preview_nodes,),
        ).fetchall()
        ranked = [r[0] for r in ranked_rows]
    preview_ids = set(ranked)

    # Step 3: collect edges where both endpoints are in the preview set.
    preview_edges = []
    seen_pairs = set()
    for s, t in conn.execute("SELECT source, target FROM edges"):
        if s in preview_ids and t in preview_ids:
            key = (s, t) if s < t else (t, s)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            preview_edges.append({"source": s, "target": t})
            if len(preview_edges) >= max_preview_edges:
                break
    log(f"  Edges in preview subgraph: {len(preview_edges):,}")

    # Step 4: if the dataset is so sparse that we got few edges, pull in direct
    # neighbors of the top hubs to densify the visualization.
    if len(preview_edges) < max_preview_edges // 4 and degree:
        log("  Sparse subgraph - adding neighbors of top hubs to densify...")
        top_hubs = ranked[: max(50, max_preview_nodes // 20)]
        chunk = 500
        candidate_neighbors: Counter = Counter()
        for i in range(0, len(top_hubs), chunk):
            batch = top_hubs[i:i + chunk]
            placeholders = ",".join("?" for _ in batch)
            rows = conn.execute(
                f"SELECT source, target FROM edges WHERE source IN ({placeholders}) OR target IN ({placeholders})",
                batch + batch,
            ).fetchall()
            for s, t in rows:
                if s in preview_ids and t not in preview_ids:
                    candidate_neighbors[t] += 1
                elif t in preview_ids and s not in preview_ids:
                    candidate_neighbors[s] += 1
        # Add the most-connected neighbors until we hit the node cap
        budget = max_preview_nodes - len(preview_ids)
        for pid, _ in candidate_neighbors.most_common(budget):
            preview_ids.add(pid)
        log(f"  Preview now has {len(preview_ids):,} nodes after densification")

        # Re-collect edges with the expanded set
        preview_edges = []
        seen_pairs = set()
        for s, t in conn.execute("SELECT source, target FROM edges"):
            if s in preview_ids and t in preview_ids:
                key = (s, t) if s < t else (t, s)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                preview_edges.append({"source": s, "target": t})
                if len(preview_edges) >= max_preview_edges:
                    break
        log(f"  Edges after densification: {len(preview_edges):,}")

    # Step 4: load full node attributes for the chosen preview ids.
    top_nodes = {}
    if preview_ids:
        placeholders = ",".join("?" for _ in preview_ids)
        node_rows = conn.execute(
            f"""
            SELECT paper_id, title, year, cited_by_count, in_degree, out_degree,
                   cluster_id, field_of_study, abstract
            FROM nodes
            WHERE paper_id IN ({placeholders})
            """,
            list(preview_ids),
        ).fetchall()
        for row in node_rows:
            top_nodes[row[0]] = {
                "paper_id": row[0],
                "title": row[1] or "Untitled paper",
                "year": row[2],
                "cited_by_count": row[3] or 0,
                "in_degree": row[4] or 0,
                "out_degree": row[5] or 0,
                "cluster_id": row[6] if row[6] is not None else -1,
                "field_of_study": row[7] or "",
                "abstract": (row[8] or "")[:1000],
                "keywords": [],
            }

    log(f"  Final preview: {len(top_nodes):,} nodes, {len(preview_edges):,} edges")

    conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", ("total_nodes", str(total_nodes)))
    conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", ("total_edges", str(total_edges)))
    conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", ("preview_nodes", str(len(top_nodes))))
    conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", ("preview_edges", str(len(preview_edges))))
    conn.commit()
    conn.close()

    write_preview(preview_path, top_nodes, preview_edges, total_nodes, total_edges)
    log("Done.")
    log(f"Database: {db_path}")
    log(f"Preview JSON: {preview_path}")
    log(f"Nodes indexed: {total_nodes:,}")
    log(f"Edges indexed: {total_edges:,}")
    log(f"Preview nodes: {len(top_nodes):,}")
    log(f"Preview edges: {len(preview_edges):,}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a queryable SQLite index and small browser preview from a huge processed_graph.json file.")
    parser.add_argument("--input", required=True, help="Path to the 150GB processed_graph.json file")
    parser.add_argument("--db", default="public/data/graph_index.db", help="Output SQLite database path")
    parser.add_argument("--preview", default="public/data/graph_preview.json", help="Output small preview JSON path")
    parser.add_argument("--max-preview-nodes", type=int, default=5000, help="Number of top papers to keep in browser preview")
    parser.add_argument("--max-preview-edges", type=int, default=20000, help="Number of preview edges to keep")
    parser.add_argument("--commit-every", type=int, default=50000, help="Rows between database commits")
    args = parser.parse_args()

    build_index(
        input_path=Path(args.input),
        db_path=Path(args.db),
        preview_path=Path(args.preview),
        max_preview_nodes=args.max_preview_nodes,
        max_preview_edges=args.max_preview_edges,
        commit_every=args.commit_every,
    )


if __name__ == "__main__":
    main()
