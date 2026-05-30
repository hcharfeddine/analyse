"""Stage 1 OPTIMIZED: Parallel ingest with integer mappings and filtering.

OPTIMIZATIONS:
  1. Create integer mappings for paper IDs and field names
  2. Filter out papers with no citations (in_degree=0 AND out_degree=0)
  3. Store only minimal graph data (node_id, year, field_id, degrees)
  4. Separate full metadata into paper_metadata table
  5. Parallel processing with ThreadPoolExecutor for fast ingestion

Expected improvements:
  - Memory: 70-80% reduction (storing integers instead of text)
  - Speed: 50-80% faster graph operations (O(1) integer lookups vs string hashing)
"""

import logging
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Set, Tuple

from config import PipelineConfig
from utils.checkpoint import CheckpointManager
from utils.data_loader import PaperDataLoader
from utils.db_schema import create_optimized_schema, reset_database
from utils.node_mapping import NodeMapping, FieldMapping

logger = logging.getLogger(__name__)


def _process_single_file_optimized(
    json_file: Path,
    db_path: Path,
    data_loader: PaperDataLoader,
    node_mapping: NodeMapping,
    field_mapping: FieldMapping,
    commit_every: int,
) -> Tuple[str, int, int, Set[str]]:
    """
    Process a single JSON file in a worker thread with integer mappings.
    
    Args:
        json_file: Path to JSON file
        db_path: Path to SQLite database
        data_loader: PaperDataLoader instance
        node_mapping: NodeMapping instance for paper ID → node_id conversion
        field_mapping: FieldMapping instance for field name → field_id conversion
        commit_every: Commit batch size (reduced from 50k to 10k for better throughput)
    
    Returns:
        (filename, num_papers, num_edges, paper_ids_with_edges)
    """
    conn = sqlite3.connect(str(db_path))
    # FIXED: Optimized SQLite pragmas for write-heavy Stage 1 processing
    # Changed from safety-first to performance-first configuration
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging: better concurrency
    conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety & speed (not FULL during bulk insert)
    conn.execute("PRAGMA cache_size=-1024000")  # Increased from 512MB to 1GB memory cache
    conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables (much faster)
    conn.execute("PRAGMA mmap_size=30000000")  # Memory-mapped I/O: 30MB for faster reads/writes
    conn.execute("PRAGMA page_size=4096")  # Standard 4KB pages
    conn.execute("PRAGMA busy_timeout=30000")  # Wait up to 30s for locks
    cursor = conn.cursor()
    
    size_gb = json_file.stat().st_size / 1e9
    logger.info(f"[Worker] Processing: {json_file.name} ({size_gb:.2f} GB)")
    
    INSERT_GRAPH_NODE = """
        INSERT INTO graph_nodes (node_id, year, field_id)
        VALUES (?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            year=COALESCE(excluded.year, graph_nodes.year)
    """
    INSERT_METADATA = """
        INSERT INTO paper_metadata (node_id, paper_id, title, authors, abstract, cited_by_count)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            title=COALESCE(excluded.title, paper_metadata.title),
            cited_by_count=COALESCE(excluded.cited_by_count, paper_metadata.cited_by_count)
    """
    INSERT_EDGE = "INSERT OR IGNORE INTO graph_edges (source_id, target_id) VALUES (?, ?)"
    
    node_buf = []
    metadata_buf = []
    edge_buf = []
    degree_acc: Dict[int, Tuple[int, int]] = {}  # node_id -> (in_degree, out_degree)
    file_papers = 0
    file_edges = 0
    paper_ids_with_edges: Set[str] = set()
    
    def flush():
        if node_buf:
            cursor.executemany(INSERT_GRAPH_NODE, node_buf)
            node_buf.clear()
        if metadata_buf:
            cursor.executemany(INSERT_METADATA, metadata_buf)
            metadata_buf.clear()
        if edge_buf:
            cursor.executemany(INSERT_EDGE, edge_buf)
            edge_buf.clear()
        conn.commit()
    
    # Process all papers from this file
    for paper in data_loader._iter_papers_from_file(json_file):
        paper_id = paper["id"]
        pid_int = node_mapping.get_or_create_node_id(paper_id)
        
        # Get or create field ID
        field_name = paper.get("field_of_study", "")
        field_id = field_mapping.get_or_create_field_id(field_name)
        
        year = paper.get("year")
        
        # Add to graph_nodes (lightweight)
        node_buf.append((pid_int, year, field_id))
        
        # Add to paper_metadata (full data)
        authors_str = ";".join(paper.get("authors", []))
        metadata_buf.append((
            pid_int,
            paper_id,
            paper.get("title", ""),
            authors_str,
            paper.get("abstract", ""),
            paper.get("cited_by_count", 0),
        ))
        
        # Process citations (edges)
        out_degree = 0
        for ref_id in paper.get("citations", []):
            if ref_id != paper_id:  # Skip self-loops
                ref_int = node_mapping.get_or_create_node_id(ref_id)
                edge_buf.append((pid_int, ref_int))
                
                # Track degree
                if ref_int not in degree_acc:
                    degree_acc[ref_int] = (0, 0)
                in_d, out_d = degree_acc[ref_int]
                degree_acc[ref_int] = (in_d + 1, out_d)
                
                if pid_int not in degree_acc:
                    degree_acc[pid_int] = (0, 0)
                in_d, out_d = degree_acc[pid_int]
                degree_acc[pid_int] = (in_d, out_d + 1)
                
                out_degree += 1
                file_edges += 1
                paper_ids_with_edges.add(paper_id)
                paper_ids_with_edges.add(ref_id)
        
        file_papers += 1
        # FIXED: More frequent commits (every 10k papers instead of 50k) for better throughput
        # Smaller batches allow better interleaving of write operations across threads
        if file_papers % max(1, commit_every // 5) == 0:  # Default: commit_every=50k → 10k papers
            flush()
            logger.info(f"[Worker] {json_file.name}: {file_papers:,} papers, {file_edges:,} edges")
    
    # Final flush
    flush()
    
    # Update degree information
    for node_id, (in_deg, out_deg) in degree_acc.items():
        cursor.execute(
            "UPDATE graph_nodes SET in_degree = in_degree + ?, out_degree = out_degree + ? WHERE node_id = ?",
            (in_deg, out_deg, node_id)
        )
    conn.commit()
    
    # Record completion
    cursor.execute(
        "INSERT OR REPLACE INTO processed_files (filename, papers, edges, finished_at) VALUES (?, ?, ?, datetime('now'))",
        (json_file.name, file_papers, file_edges),
    )
    conn.commit()
    conn.close()
    
    logger.info(f"[Worker] Done {json_file.name}: {file_papers:,} papers, {file_edges:,} edges")
    return (json_file.name, file_papers, file_edges, paper_ids_with_edges)


def ingest_stage_optimized(config: PipelineConfig) -> Dict:
    """
    Stage 1 OPTIMIZED: Ingest papers with integer mappings and filtering.

    Process:
      1. Load/initialize node_id and field_id mappings
      2. Process JSON files in parallel, creating integer-based graph structure
      3. Filter out papers with no edges (isolated nodes)
      4. Store mappings and graph data to database

    Args:
        config: Pipeline configuration.
    Returns:
        Results dictionary with graph statistics.
    """
    logger.info("=" * 60)
    logger.info("STAGE 1 OPTIMIZED: INGEST (INTEGER MAPPINGS + FILTERING)")
    logger.info("=" * 60)

    checkpoint_manager = CheckpointManager(config.checkpoint_dir, config.enable_checkpointing)
    if checkpoint_manager.checkpoint_exists("ingest_optimized"):
        logger.info("Found existing checkpoint, verifying completion...")
        cp = checkpoint_manager.load_checkpoint("ingest_optimized")
        
        # FIXED: Verify that checkpoint is valid by checking database completion status
        # This ensures resume doesn't return stale data if processing was interrupted
        try:
            temp_conn = sqlite3.connect(str(config.db_path))
            temp_cursor = temp_conn.cursor()
            
            # Check if all expected files were processed
            expected_files = sorted([f.name for f in PaperDataLoader(config.input_dir).json_files])
            processed_files = {
                r[0] for r in temp_cursor.execute(
                    "SELECT filename FROM processed_files"
                ).fetchall()
            }
            temp_conn.close()
            
            if processed_files >= set(expected_files):
                logger.info(f"Checkpoint valid: All {len(expected_files)} files processed.")
                return cp.get("data", {})
            else:
                missing = set(expected_files) - processed_files
                logger.info(f"Checkpoint incomplete: {len(missing)} files not yet processed ({missing}). Resuming...")
        except Exception as e:
            logger.warning(f"Could not verify checkpoint status: {e}. Resuming fresh...")

    # Reset or create optimized database
    if config.reset_db:
        reset_database(config.db_path)
    conn = create_optimized_schema(config.db_path)
    cursor = conn.cursor()

    # Initialize mappings
    node_mapping = NodeMapping(config.db_path)
    node_mapping.ensure_tables(conn)
    node_mapping.load_mappings(conn)
    
    field_mapping = FieldMapping(config.db_path)
    field_mapping.ensure_tables(conn)
    field_mapping.load_mappings(conn)
    
    logger.info(f"Existing mappings: {node_mapping.stats()['total_mappings']} paper IDs, "
                f"{field_mapping.stats()['total_fields']} fields")

    # Track already-processed files
    done_files = {r[0] for r in cursor.execute("SELECT filename FROM processed_files").fetchall()}
    if done_files:
        logger.info(f"Resuming — skipping {len(done_files)} already-processed files")

    data_loader = PaperDataLoader(config.input_dir)
    pending_files = [f for f in data_loader.json_files if f.name not in done_files]
    logger.info(f"Files to process: {len(pending_files)}")
    conn.close()  # Close before spawning workers

    # ────── PARALLEL PROCESSING ──────────────────────────────────────────
    cpu_count = os.cpu_count() or 4
    num_workers = max(8, min(cpu_count * 2, len(pending_files)))
    logger.info(f"Starting parallel ingest with {num_workers} workers")
    
    file_results = {}
    all_paper_ids_with_edges: Set[str] = set()
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(
                _process_single_file_optimized,
                json_file,
                config.db_path,
                data_loader,
                node_mapping,
                field_mapping,
                config.commit_every,
            ): json_file.name
            for json_file in pending_files
        }
        
        for future in as_completed(futures):
            filename, num_papers, num_edges, paper_ids = future.result()
            file_results[filename] = {"papers": num_papers, "edges": num_edges}
            all_paper_ids_with_edges.update(paper_ids)
            logger.info(f"Completed: {filename}")

    # ────── FLUSH MAPPINGS TO DATABASE ──────────────────────────────────────
    conn = sqlite3.connect(str(config.db_path))
    node_mapping.flush_to_db(conn)
    field_mapping.flush_to_db(conn)
    conn.close()

    # ────── FILTER PAPERS WITH NO EDGES ──────────────────────────────────────
    logger.info("Filtering papers with no forward or backward citations...")
    conn = sqlite3.connect(str(config.db_path))
    cursor = conn.cursor()
    
    # Find papers with in_degree=0 AND out_degree=0
    isolated = cursor.execute(
        "SELECT node_id FROM graph_nodes WHERE in_degree = 0 AND out_degree = 0"
    ).fetchall()
    isolated_ids = [r[0] for r in isolated]
    
    logger.info(f"Found {len(isolated_ids):,} papers with no citations (in/out degree = 0)")
    
    # Delete isolated nodes in batches
    CHUNK = 50000
    for start in range(0, len(isolated_ids), CHUNK):
        chunk = isolated_ids[start:start + CHUNK]
        placeholders = ",".join("?" * len(chunk))
        cursor.execute(f"DELETE FROM graph_nodes WHERE node_id IN ({placeholders})", chunk)
        cursor.execute(f"DELETE FROM paper_metadata WHERE node_id IN ({placeholders})", chunk)
    conn.commit()

    # ────── CREATE INDEXES AND FINALIZE ──────────────────────────────────────
    logger.info("Creating indexes...")
    for stmt in [
        "CREATE INDEX IF NOT EXISTS idx_graph_nodes_year ON graph_nodes(year)",
        "CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_id)",
        "CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_id)",
    ]:
        cursor.execute(stmt)
    conn.commit()

    # Get final statistics
    node_count = cursor.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
    edge_count = cursor.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
    
    cursor.execute(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
        ("total_nodes_after_filtering", str(node_count))
    )
    cursor.execute(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
        ("total_edges", str(edge_count))
    )
    cursor.execute(
        "INSERT OR REPLACE INTO processing_status (stage, status, timestamp, details) VALUES (?, ?, datetime('now'), ?)",
        ("ingest_optimized", "completed", 
         f"nodes={node_count}, edges={edge_count}, isolated_removed={len(isolated_ids)}")
    )
    conn.commit()
    conn.close()

    results = {
        "total_nodes_after_filtering": node_count,
        "total_edges": edge_count,
        "isolated_nodes_removed": len(isolated_ids),
        "node_mappings_created": node_mapping.stats()["total_mappings"],
        "field_mappings_created": field_mapping.stats()["total_fields"],
        "files_processed": len(file_results),
    }

    logger.info("")
    logger.info("Stage 1 Results:")
    for key, value in results.items():
        logger.info(f"  {key}: {value:,}")

    checkpoint_manager.save_checkpoint("ingest_optimized", results, results)
    return results


def ingest_papers(config: PipelineConfig) -> Dict:
    """
    Wrapper function for main_stages_1_2.py compatibility.
    
    This is an alias for ingest_stage_optimized() that matches the expected
    function signature in main_stages_1_2.py.
    """
    return ingest_stage_optimized(config)
