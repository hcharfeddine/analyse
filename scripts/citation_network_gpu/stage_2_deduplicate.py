"""Stage 2 OPTIMIZED: Deduplicate edges using integer operations.

This optimized version works with integer node IDs, which are much faster to
process than text paper IDs. Since duplicates are already prevented by the
PRIMARY KEY constraint on graph_edges, this stage mainly:
  1. Validates edge consistency
  2. Removes self-loops
  3. Ensures all edge endpoints exist
  4. Updates degree counters
"""

import logging
import sqlite3
from typing import Dict

from config import PipelineConfig
from utils.checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


def deduplicate_stage_optimized(config: PipelineConfig) -> Dict:
    """
    Stage 2 OPTIMIZED: Clean and validate edges using integer operations.

    Args:
        config: Pipeline configuration.
    Returns:
        Results dictionary with deduplication statistics.
    """
    logger.info("=" * 60)
    logger.info("STAGE 2 OPTIMIZED: DEDUPLICATE (INTEGER OPERATIONS)")
    logger.info("=" * 60)

    checkpoint_manager = CheckpointManager(config.checkpoint_dir, config.enable_checkpointing)
    if checkpoint_manager.checkpoint_exists("deduplicate_optimized"):
        logger.info("Found existing checkpoint, loading...")
        cp = checkpoint_manager.load_checkpoint("deduplicate_optimized")
        return cp.get("data", {})

    conn = sqlite3.connect(str(config.db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-512000")
    conn.execute("PRAGMA wal_autocheckpoint=50000")
    conn.execute("PRAGMA busy_timeout=5000")
    cursor = conn.cursor()

    # Get initial statistics
    total_nodes_before = cursor.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
    total_edges_before = cursor.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
    logger.info(f"Before dedup: {total_nodes_before:,} nodes, {total_edges_before:,} edges")

    # ────── REMOVE SELF-LOOPS ──────────────────────────────────────────
    logger.info("Removing self-loop edges...")
    cursor.execute("DELETE FROM graph_edges WHERE source_id = target_id")
    self_loops_removed = cursor.rowcount
    conn.commit()
    logger.info(f"  Removed {self_loops_removed:,} self-loop edges")

    # ────── REMOVE EDGES WITH MISSING ENDPOINTS ────────────────────────
    logger.info("Removing edges with missing endpoints...")
    cursor.execute("""
        DELETE FROM graph_edges
        WHERE source_id NOT IN (SELECT node_id FROM graph_nodes)
           OR target_id NOT IN (SELECT node_id FROM graph_nodes)
    """)
    dangling_removed = cursor.rowcount
    conn.commit()
    logger.info(f"  Removed {dangling_removed:,} dangling edges")

    # ────── UPDATE DEGREE COUNTERS ─────────────────────────────────────
    logger.info("Updating degree counters...")
    
    # Reset degree counters
    cursor.execute("UPDATE graph_nodes SET in_degree = 0, out_degree = 0")
    
    # Recalculate in-degrees and out-degrees from edges
    cursor.execute("""
        UPDATE graph_nodes SET out_degree = (
            SELECT COUNT(*) FROM graph_edges WHERE source_id = graph_nodes.node_id
        )
    """)
    
    cursor.execute("""
        UPDATE graph_nodes SET in_degree = (
            SELECT COUNT(*) FROM graph_edges WHERE target_id = graph_nodes.node_id
        )
    """)
    conn.commit()
    logger.info("  Degree counters updated")

    # ────── GET FINAL STATISTICS ──────────────────────────────────────
    total_nodes_after = cursor.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
    total_edges_after = cursor.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
    
    # Statistics on degree distribution
    avg_in_degree = cursor.execute("SELECT AVG(in_degree) FROM graph_nodes").fetchone()[0] or 0
    avg_out_degree = cursor.execute("SELECT AVG(out_degree) FROM graph_nodes").fetchone()[0] or 0
    
    cursor.execute(
        "INSERT OR REPLACE INTO processing_status (stage, status, timestamp, details) VALUES (?, ?, datetime('now'), ?)",
        ("deduplicate_optimized", "completed", 
         f"nodes={total_nodes_after}, edges={total_edges_after}, "
         f"avg_in_degree={avg_in_degree:.2f}, avg_out_degree={avg_out_degree:.2f}"),
    )
    conn.commit()
    conn.close()

    results = {
        "total_nodes_before": total_nodes_before,
        "total_edges_before": total_edges_before,
        "self_loops_removed": self_loops_removed,
        "dangling_edges_removed": dangling_removed,
        "total_nodes_after": total_nodes_after,
        "total_edges_after": total_edges_after,
        "avg_in_degree": round(avg_in_degree, 2),
        "avg_out_degree": round(avg_out_degree, 2),
    }

    logger.info("")
    logger.info("Stage 2 Results:")
    for key, value in results.items():
        logger.info(f"  {key}: {value}")

    checkpoint_manager.save_checkpoint("deduplicate_optimized", results, results)
    return results
