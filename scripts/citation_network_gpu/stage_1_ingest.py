"""Stage 1 OPTIMIZED: Parallel ingest papers and create multi-GPU graph shards.

OPTIMIZATION 1: Parallel Multiprocessing Ingest
  Instead of processing JSON files sequentially, use ThreadPoolExecutor
  to process 8 files in parallel (one per GPU available).
)
  
  Key improvements:
  - ThreadPoolExecutor with 8 workers processes 8 JSON files concurrently
  - Each worker gets its own SQLite connection (thread-safe)
  - Batched commits every 50K papers
  - File-level resumability (tracks processed_files)
"""

import logging
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

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
    # Performance optimizations for parallel writes
    conn.execute("PRAGMA wal_autocheckpoint=50000")  # Checkpoint less frequently (default 1000)
    conn.execute("PRAGMA locking_mode=EXCLUSIVE")     # Exclusive lock for isolated writes
    conn.execute("PRAGMA busy_timeout=5000")          # 5 second timeout for locked DB
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


def _process_single_file(
    json_file: Path,
    db_path: Path,
    data_loader: PaperDataLoader,
    commit_every: int,
) -> Tuple[str, int, int]:
    """
    Process a single JSON file in a worker thread.
    
    Args:
        json_file: Path to JSON file
        db_path: Path to SQLite database
        data_loader: PaperDataLoader instance
        commit_every: Commit batch size
    
    Returns:
        (filename, num_papers, num_edges)
    """
    # IMPORTANT: Each worker gets its own DB connection (SQLite is thread-safe)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-512000")
    cursor = conn.cursor()
    
    size_gb = json_file.stat().st_size / 1e9
    logger.info(f"[Worker] Processing: {json_file.name} ({size_gb:.2f} GB)")
    
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
        if file_papers % commit_every == 0:
            flush()
            logger.info(f"[Worker] {json_file.name}: {file_papers:,} papers, {file_edges:,} edges")
    
    flush()
    
    # Record completion
    cursor.execute(
        "INSERT OR REPLACE INTO processed_files (filename, papers, edges, finished_at) VALUES (?, ?, ?, datetime('now'))",
        (json_file.name, file_papers, file_edges),
    )
    conn.commit()
    conn.close()
    
    logger.info(f"[Worker] Done {json_file.name}: {file_papers:,} papers, {file_edges:,} edges")
    return (json_file.name, file_papers, file_edges)


def ingest_stage(config: PipelineConfig) -> Dict:
    """
    Stage 1 OPTIMIZED: Ingest papers from JSON files in PARALLEL.

    Uses ThreadPoolExecutor with 8 workers (one per GPU) to process
    JSON files concurrently. Much faster than sequential processing.

    Args:
        config: Pipeline configuration.
    Returns:
        Results dictionary with graph statistics.
    """
    logger.info("=" * 60)
    logger.info("STAGE 1: INGEST (OPTIMIZED — PARALLEL)")
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
    conn.close()  # Close main connection before spawning workers

    # ── OPTIMIZATION: Parallel processing with ThreadPoolExecutor ──────────────────
    # Use 2x CPU cores for JSON parsing (I/O-bound, releases GIL)
    # JSON parsing is I/O-bound and benefits from more threads than GPUs
    cpu_count = os.cpu_count() or 4
    num_workers = max(8, min(cpu_count * 2, len(pending_files)))
    logger.info(f"Starting parallel ingest with {num_workers} workers (CPUs={cpu_count}, Files={len(pending_files)})")
    
    file_results = {}
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                _process_single_file,
                json_file,
                config.db_path,
                data_loader,
                config.commit_every,
            ): json_file.name
            for json_file in pending_files
        }
        
        # Collect results as they complete
        for future in as_completed(futures):
            filename, num_papers, num_edges = future.result()
            file_results[filename] = {"papers": num_papers, "edges": num_edges}
            logger.info(f"Completed: {filename} ({num_papers:,} papers, {num_edges:,} edges)")
    
    # ── Aggregate results and create indexes ─────────────────────────────────────
    logger.info("Creating indexes ...")
    conn = sqlite3.connect(config.db_path)
    cursor = conn.cursor()
    
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
        ("ingest", "completed", f"nodes={node_total}, edges={edge_total}, parallel_workers={num_workers}"),
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
        "parallel_workers": num_workers,
        "file_results": file_results,
        "shard_stats": shard_manager.get_shard_stats(),
    }

    logger.info(f"Stage 1 OPTIMIZED Results: nodes={node_total:,}, edges={edge_total:,}, workers={num_workers}")
    checkpoint_manager.save_checkpoint("ingest", results, results)
    return results
