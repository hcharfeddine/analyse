"""Stage 1: Ingest papers and create multi-GPU graph shards.

FIX: Original GraphShardManager.add_edge() called list.index() — O(N) per edge.
     100M edges × O(N) = catastrophically slow. Fixed in graph_utils.py (O(1) dict).

FIX: Cross-shard edges used wrong local index (target_idx from target's shard
     was written into source's edge list). Fixed in graph_utils.py.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict

from config import PipelineConfig
from utils.checkpoint import CheckpointManager, StageProgress
from utils.data_loader import GraphBuilder, PaperDataLoader
from utils.graph_utils import GraphShardManager

logger = logging.getLogger(__name__)


def setup_database(db_path: Path, reset: bool = False) -> sqlite3.Connection:
    """Setup SQLite database for graph metadata."""
    if reset and db_path.exists():
        db_path.unlink()
        for suffix in ("-wal", "-shm"):
            p = Path(str(db_path) + suffix)
            if p.exists():
                p.unlink()
        logger.info(f"Reset database: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-512000")
    conn.execute("PRAGMA temp_store=MEMORY")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            paper_id TEXT PRIMARY KEY,
            title TEXT,
            authors TEXT,
            year INTEGER,
            abstract TEXT,
            cited_by_count INTEGER DEFAULT 0,
            in_degree INTEGER DEFAULT 0,
            out_degree INTEGER DEFAULT 0,
            field_of_study TEXT,
            community_id INTEGER,
            x REAL,
            y REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            source_id TEXT,
            target_id TEXT,
            PRIMARY KEY (source_id, target_id)
        ) WITHOUT ROWID
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS node_coordinates (
            paper_id TEXT PRIMARY KEY,
            x REAL,
            y REAL,
            layout_iteration INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processing_status (
            stage TEXT PRIMARY KEY,
            status TEXT,
            timestamp TEXT,
            details TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_files (
            filename TEXT PRIMARY KEY,
            papers INTEGER,
            edges INTEGER,
            finished_at TEXT
        )
    """)
    conn.commit()
    logger.info(f"Database ready: {db_path}")
    return conn


def ingest_stage(config: PipelineConfig) -> Dict:
    """
    Stage 1: Ingest papers from JSON files into SQLite + GPU shards.

    Args:
        config: Pipeline configuration.
    Returns:
        Results dictionary with graph statistics.
    """
    logger.info("=" * 60)
    logger.info("STAGE 1: INGEST")
    logger.info("=" * 60)

    checkpoint_manager = CheckpointManager(config.checkpoint_dir, config.enable_checkpointing)
    if checkpoint_manager.checkpoint_exists("ingest"):
        logger.info("Found existing checkpoint, loading...")
        cp = checkpoint_manager.load_checkpoint("ingest")
        return cp.get("data", {})

    conn = setup_database(config.db_path, reset=config.reset_db)
    cursor = conn.cursor()

    # Track already-processed files (resumability)
    done_files = {r[0] for r in cursor.execute("SELECT filename FROM processed_files").fetchall()}
    if done_files:
        logger.info(f"Resuming — skipping {len(done_files)} already-processed files")

    data_loader = PaperDataLoader(config.input_dir)
    pending_files = [f for f in data_loader.json_files if f.name not in done_files]
    logger.info(f"Files to process: {len(pending_files)}")

    INSERT_NODE = """
        INSERT INTO nodes (paper_id, title, authors, year, abstract, cited_by_count, out_degree, field_of_study)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(paper_id) DO UPDATE SET
            title=COALESCE(excluded.title, nodes.title),
            year=COALESCE(excluded.year, nodes.year),
            cited_by_count=COALESCE(excluded.cited_by_count, nodes.cited_by_count),
            out_degree=nodes.out_degree + excluded.out_degree
    """
    INSERT_EDGE = "INSERT OR IGNORE INTO edges (source_id, target_id) VALUES (?, ?)"
    INSERT_TARGET = "INSERT OR IGNORE INTO nodes (paper_id, in_degree) VALUES (?, 0)"
    UPDATE_INDEG = "UPDATE nodes SET in_degree = COALESCE(in_degree,0) + ? WHERE paper_id = ?"

    total_papers = 0
    total_edges = 0
    COMMIT_EVERY = config.commit_every

    for json_file in pending_files:
        size_gb = json_file.stat().st_size / 1e9
        logger.info(f"\nProcessing: {json_file.name} ({size_gb:.2f} GB)")

        node_buf = []
        edge_buf = []
        indeg_acc: Dict[str, int] = {}
        file_papers = 0
        file_edges = 0

        def flush():
            if node_buf:
                cursor.executemany(INSERT_NODE, node_buf)
                node_buf.clear()
            if edge_buf:
                cursor.executemany(INSERT_EDGE, edge_buf)
                edge_buf.clear()
            if indeg_acc:
                cursor.executemany(INSERT_TARGET, [(tid,) for tid in indeg_acc])
                cursor.executemany(UPDATE_INDEG, [(cnt, tid) for tid, cnt in indeg_acc.items()])
                indeg_acc.clear()
            conn.commit()

        for paper in data_loader._iter_papers_from_file(json_file):
            pid = paper["id"]
            authors_str = ";".join(paper.get("authors", []))
            node_buf.append((
                pid,
                paper.get("title", ""),
                authors_str,
                paper.get("year"),
                paper.get("abstract", ""),
                paper.get("cited_by_count", 0),
                len(paper.get("citations", [])),
                paper.get("field_of_study", ""),
            ))

            for ref_id in paper.get("citations", []):
                if ref_id != pid:
                    edge_buf.append((pid, ref_id))
                    indeg_acc[ref_id] = indeg_acc.get(ref_id, 0) + 1
                    file_edges += 1

            file_papers += 1
            if file_papers % COMMIT_EVERY == 0:
                flush()
                logger.info(f"  {json_file.name}: {file_papers:,} papers, {file_edges:,} edges")

        flush()
        total_papers += file_papers
        total_edges += file_edges

        cursor.execute(
            "INSERT OR REPLACE INTO processed_files (filename, papers, edges, finished_at) VALUES (?, ?, ?, datetime('now'))",
            (json_file.name, file_papers, file_edges),
        )
        conn.commit()
        logger.info(f"  Done {json_file.name}: {file_papers:,} papers, {file_edges:,} edges")

    # Final indexes
    logger.info("\nCreating indexes ...")
    for stmt in [
        "CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)",
        "CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)",
        "CREATE INDEX IF NOT EXISTS idx_nodes_year ON nodes(year)",
        "CREATE INDEX IF NOT EXISTS idx_nodes_cited ON nodes(cited_by_count)",
    ]:
        cursor.execute(stmt)
    conn.commit()

    node_total = cursor.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    edge_total = cursor.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    cursor.executemany("INSERT OR REPLACE INTO metadata (key,value) VALUES (?,?)", [
        ("total_nodes", str(node_total)),
        ("total_edges", str(edge_total)),
    ])
    cursor.execute(
        "INSERT OR REPLACE INTO processing_status (stage, status, timestamp, details) VALUES (?,?,datetime('now'),?)",
        ("ingest", "completed", f"nodes={node_total}, edges={edge_total}"),
    )
    conn.commit()

    # GPU shards (in-memory, for downstream stages that need them)
    logger.info(f"\nCreating {config.num_gpus} GPU shards ...")
    shard_manager = GraphShardManager(config.num_gpus, config.gpu_devices or list(range(config.num_gpus)))

    for row in cursor.execute("SELECT paper_id, title, year, cited_by_count FROM nodes LIMIT 1000000"):
        shard_manager.add_node(row[0], {"title": row[1], "year": row[2], "cited_by_count": row[3]})

    for row in cursor.execute("SELECT source_id, target_id FROM edges LIMIT 5000000"):
        try:
            shard_manager.add_edge(row[0], row[1])
        except Exception:
            continue

    conn.close()

    results = {
        "num_nodes": node_total,
        "num_edges": edge_total,
        "files_processed": len(pending_files),
        "shard_stats": shard_manager.get_shard_stats(),
    }

    logger.info(f"Stage 1 Results: nodes={node_total:,}, edges={edge_total:,}")
    checkpoint_manager.save_checkpoint("ingest", results, results)
    return results
