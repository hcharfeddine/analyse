import logging
import os
import queue
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Set, Tuple

from config import PipelineConfig
from utils.checkpoint import CheckpointManager
from utils.data_loader import PaperDataLoader
from utils.db_schema import create_optimized_schema, reset_database
from utils.node_mapping import NodeMapping, FieldMapping

logger = logging.getLogger(__name__)

# Producer-consumer: parse workers push to this queue; single writer thread drains it.
# Maxsize limits RAM: at most 64 pending batches in flight before parsers back-pressure.
_QUEUE_MAXSIZE = 64


def _parse_file(
    json_file: Path,
    data_loader: PaperDataLoader,
    node_mapping: NodeMapping,
    field_mapping: FieldMapping,
    write_queue: queue.Queue,
    batch_size: int,
) -> Tuple[str, int, int]:
    """
    Parse one JSON file. Push record batches to write_queue.
    No SQLite access — zero lock contention with other parse workers.
    """
    node_buf:     List = []
    metadata_buf: List = []
    edge_buf:     List = []
    degree_acc:   Dict[int, Tuple[int, int]] = {}
    file_papers = 0
    file_edges  = 0

    def enqueue_batch():
        if node_buf or metadata_buf or edge_buf:
            write_queue.put(("batch", list(node_buf), list(metadata_buf), list(edge_buf)))
            node_buf.clear()
            metadata_buf.clear()
            edge_buf.clear()

    for paper in data_loader._iter_papers_from_file(json_file):
        paper_id = paper["id"]
        pid_int  = node_mapping.get_or_create_node_id(paper_id)
        field_id = field_mapping.get_or_create_field_id(paper.get("field_of_study", ""))
        year     = paper.get("year")

        node_buf.append((pid_int, year, field_id))
        metadata_buf.append((
            pid_int, paper_id,
            paper.get("title", ""),
            ";".join(paper.get("authors", [])),
            paper.get("abstract", ""),
            paper.get("cited_by_count", 0),
        ))

        for ref_id in paper.get("citations", []):
            if ref_id == paper_id:
                continue
            ref_int = node_mapping.get_or_create_node_id(ref_id)
            edge_buf.append((pid_int, ref_int))

            in_d, out_d = degree_acc.get(ref_int, (0, 0))
            degree_acc[ref_int] = (in_d + 1, out_d)
            in_d, out_d = degree_acc.get(pid_int, (0, 0))
            degree_acc[pid_int] = (in_d, out_d + 1)
            file_edges += 1

        file_papers += 1
        if file_papers % batch_size == 0:
            enqueue_batch()
            logger.info(f"[Parser] {json_file.name}: {file_papers:,} papers, {file_edges:,} edges")

    enqueue_batch()

    # Send degree map and completion marker; writer handles DB updates
    write_queue.put(("degrees",   degree_acc))
    write_queue.put(("file_done", json_file.name, file_papers, file_edges))

    logger.info(f"[Parser] Done {json_file.name}: {file_papers:,} papers, {file_edges:,} edges")
    return (json_file.name, file_papers, file_edges)


def _writer_loop(db_path: Path, write_queue: queue.Queue, total_files: int) -> Dict:
    """
    Single writer thread — the ONLY thread that touches SQLite.
    No lock contention; parsers run fully in parallel without waiting for this.
    """
    conn = sqlite3.connect(str(db_path))
    # synchronous=OFF is safe during bulk ingest: if process crashes, re-run from source files.
    # Gives 3-5x faster writes vs NORMAL. Restored to NORMAL when ingest finishes.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-1048576")   # 1 GB page cache
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")   # 256 MB mmap
    conn.execute("PRAGMA busy_timeout=60000")
    cursor = conn.cursor()

    INSERT_NODE = """
        INSERT INTO graph_nodes (node_id, year, field_id) VALUES (?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET year=COALESCE(excluded.year, graph_nodes.year)
    """
    INSERT_META = """
        INSERT INTO paper_metadata (node_id, paper_id, title, authors, abstract, cited_by_count)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            title=COALESCE(excluded.title, paper_metadata.title),
            cited_by_count=COALESCE(excluded.cited_by_count, paper_metadata.cited_by_count)
    """
    INSERT_EDGE = "INSERT OR IGNORE INTO graph_edges (source_id, target_id) VALUES (?, ?)"

    files_done   = 0
    file_results = {}
    pending: List[Tuple] = []   # accumulated (node_buf, meta_buf, edge_buf) tuples

    def flush():
        if not pending:
            return
        nodes, meta, edges = [], [], []
        for nb, mb, eb in pending:
            nodes.extend(nb)
            meta.extend(mb)
            edges.extend(eb)
        if nodes:  cursor.executemany(INSERT_NODE, nodes)
        if meta:   cursor.executemany(INSERT_META, meta)
        if edges:  cursor.executemany(INSERT_EDGE, edges)
        conn.commit()
        pending.clear()

    while files_done < total_files:
        try:
            item = write_queue.get(timeout=120)
        except queue.Empty:
            logger.warning("[Writer] No data for 120 s — possible parser stall")
            continue

        kind = item[0]

        if kind == "batch":
            _, node_buf, meta_buf, edge_buf = item
            pending.append((node_buf, meta_buf, edge_buf))
            # Commit every 20 accumulated batches to keep memory bounded
            if len(pending) >= 20:
                flush()

        elif kind == "degrees":
            _, degree_acc = item
            flush()
            for node_id, (in_deg, out_deg) in degree_acc.items():
                cursor.execute(
                    "UPDATE graph_nodes SET in_degree=in_degree+?, out_degree=out_degree+? WHERE node_id=?",
                    (in_deg, out_deg, node_id),
                )
            conn.commit()

        elif kind == "file_done":
            _, filename, papers, edges = item
            flush()
            cursor.execute(
                "INSERT OR REPLACE INTO processed_files (filename, papers, edges, finished_at) "
                "VALUES (?, ?, ?, datetime('now'))",
                (filename, papers, edges),
            )
            conn.commit()
            file_results[filename] = {"papers": papers, "edges": edges}
            files_done += 1
            logger.info(f"[Writer] {files_done}/{total_files} files written to DB")

    flush()
    conn.execute("PRAGMA synchronous=NORMAL")   # restore after bulk ingest
    conn.close()
    return file_results


def ingest_stage_optimized(config: PipelineConfig) -> Dict:
    logger.info("=" * 60)
    logger.info("STAGE 1: INGEST (PRODUCER-CONSUMER, INTEGER MAPPINGS)")
    logger.info("=" * 60)

    checkpoint_manager = CheckpointManager(config.checkpoint_dir, config.enable_checkpointing)
    if checkpoint_manager.checkpoint_exists("ingest_optimized"):
        logger.info("Found existing checkpoint, verifying completion...")
        cp = checkpoint_manager.load_checkpoint("ingest_optimized")
        try:
            temp_conn = sqlite3.connect(str(config.db_path))
            expected  = sorted(f.name for f in PaperDataLoader(config.input_dir).json_files)
            processed = {r[0] for r in temp_conn.execute("SELECT filename FROM processed_files").fetchall()}
            temp_conn.close()
            if processed >= set(expected):
                logger.info(f"Checkpoint valid: all {len(expected)} files processed.")
                return cp.get("data", {})
            missing = set(expected) - processed
            logger.info(f"Checkpoint incomplete: {len(missing)} file(s) missing. Resuming...")
        except Exception as e:
            logger.warning(f"Could not verify checkpoint: {e}. Starting fresh...")

    if config.reset_db:
        reset_database(config.db_path)
    conn = create_optimized_schema(config.db_path)
    cursor = conn.cursor()

    node_mapping  = NodeMapping(config.db_path)
    field_mapping = FieldMapping(config.db_path)
    node_mapping.ensure_tables(conn)
    field_mapping.ensure_tables(conn)
    node_mapping.load_mappings(conn)
    field_mapping.load_mappings(conn)
    logger.info(
        f"Existing mappings: {node_mapping.stats()['total_mappings']:,} papers, "
        f"{field_mapping.stats()['total_fields']:,} fields"
    )

    done_files    = {r[0] for r in cursor.execute("SELECT filename FROM processed_files").fetchall()}
    data_loader   = PaperDataLoader(config.input_dir)
    pending_files = [f for f in data_loader.json_files if f.name not in done_files]
    conn.close()

    if done_files:
        logger.info(f"Resuming — skipping {len(done_files)} already-processed file(s)")
    logger.info(f"Files to process: {len(pending_files)}")

    if not pending_files:
        logger.info("Nothing to do.")
        return {}

    # ── Producer-consumer ────────────────────────────────────────────────────
    # N parse threads (CPU-bound, fully parallel, zero SQLite access)
    # 1 write thread  (I/O-bound, exclusive SQLite owner, no lock contention)
    # ────────────────────────────────────────────────────────────────────────
    cpu_count  = os.cpu_count() or 4
    num_parsers = min(cpu_count, len(pending_files))   # one worker per file, up to CPU count
    logger.info(f"Starting {num_parsers} parse workers + 1 write thread")

    write_queue        = queue.Queue(maxsize=_QUEUE_MAXSIZE)
    file_results_store = {}

    def _run_writer():
        file_results_store.update(
            _writer_loop(config.db_path, write_queue, len(pending_files))
        )

    writer_thread = threading.Thread(target=_run_writer, name="sqlite-writer", daemon=True)
    writer_thread.start()

    with ThreadPoolExecutor(max_workers=num_parsers) as executor:
        futures = {
            executor.submit(
                _parse_file,
                f,
                data_loader,
                node_mapping,
                field_mapping,
                write_queue,
                config.batch_size,
            ): f.name
            for f in pending_files
        }
        for future in as_completed(futures):
            filename, n_papers, n_edges = future.result()
            logger.info(f"Parsed: {filename}  ({n_papers:,} papers, {n_edges:,} edges)")

    writer_thread.join()
    file_results = file_results_store

    # ── Flush mappings + filter isolated + index ─────────────────────────────
    conn = sqlite3.connect(str(config.db_path))
    node_mapping.flush_to_db(conn)
    field_mapping.flush_to_db(conn)
    cursor = conn.cursor()

    logger.info("Filtering isolated papers (in_degree=0 AND out_degree=0)...")
    isolated_ids = [r[0] for r in cursor.execute(
        "SELECT node_id FROM graph_nodes WHERE in_degree=0 AND out_degree=0"
    ).fetchall()]
    logger.info(f"Removing {len(isolated_ids):,} isolated papers...")
    CHUNK = 50000
    for start in range(0, len(isolated_ids), CHUNK):
        chunk = isolated_ids[start : start + CHUNK]
        ph = ",".join("?" * len(chunk))
        cursor.execute(f"DELETE FROM graph_nodes    WHERE node_id IN ({ph})", chunk)
        cursor.execute(f"DELETE FROM paper_metadata WHERE node_id IN ({ph})", chunk)
    conn.commit()

    logger.info("Creating indexes...")
    for stmt in [
        "CREATE INDEX IF NOT EXISTS idx_graph_nodes_year    ON graph_nodes(year)",
        "CREATE INDEX IF NOT EXISTS idx_graph_edges_source  ON graph_edges(source_id)",
        "CREATE INDEX IF NOT EXISTS idx_graph_edges_target  ON graph_edges(target_id)",
    ]:
        cursor.execute(stmt)
    conn.commit()

    node_count = cursor.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
    edge_count = cursor.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
    cursor.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", ("total_nodes_after_filtering", str(node_count)))
    cursor.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", ("total_edges", str(edge_count)))
    cursor.execute(
        "INSERT OR REPLACE INTO processing_status VALUES (?, ?, datetime('now'), ?)",
        ("ingest_optimized", "completed", f"nodes={node_count}, edges={edge_count}, isolated_removed={len(isolated_ids)}"),
    )
    conn.commit()
    conn.close()

    results = {
        "total_nodes_after_filtering": node_count,
        "total_edges":                 edge_count,
        "isolated_nodes_removed":      len(isolated_ids),
        "node_mappings_created":       node_mapping.stats()["total_mappings"],
        "field_mappings_created":      field_mapping.stats()["total_fields"],
        "files_processed":             len(file_results),
    }
    logger.info("Stage 1 Results:")
    for k, v in results.items():
        logger.info(f"  {k}: {v:,}")

    checkpoint_manager.save_checkpoint("ingest_optimized", results, results)
    return results


def ingest_papers(config: PipelineConfig) -> Dict:
    return ingest_stage_optimized(config)
