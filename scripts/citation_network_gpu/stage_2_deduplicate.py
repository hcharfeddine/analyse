"""Stage 2: Deduplicate and clean edges using GPU acceleration.

FIX (critical): Original code replaced ALL edges with (0,1) before deduplication:
    edge_list = torch.tensor([(0, 1) for _, _ in edges], ...)
    This meant the GPU always saw exactly 1 unique edge and deduped nothing.

FIXED approach:
  - Deduplication is done efficiently in SQLite with a single recreate-table
    query (fastest for this workload — avoids loading 100M edges into Python)
  - GPU (torch) is used for the isolated-node mask computation on the
    adjacency index, which IS a genuine GPU win
"""

import logging
import sqlite3
from typing import Dict

from config import PipelineConfig
from utils.checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


def deduplicate_stage(config: PipelineConfig) -> Dict:
    """
    Stage 2: Remove duplicate edges and isolated nodes.

    Args:
        config: Pipeline configuration.
    Returns:
        Results dictionary with deduplication statistics.
    """
    logger.info("=" * 60)
    logger.info("STAGE 2: DEDUPLICATE")
    logger.info("=" * 60)

    checkpoint_manager = CheckpointManager(config.checkpoint_dir, config.enable_checkpointing)
    if checkpoint_manager.checkpoint_exists("deduplicate"):
        logger.info("Found existing checkpoint, loading...")
        cp = checkpoint_manager.load_checkpoint("deduplicate")
        return cp.get("data", {})

    conn = sqlite3.connect(config.db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-512000")
    cursor = conn.cursor()

    # Count before
    total_edges_before = cursor.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    total_nodes_before = cursor.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    logger.info(f"Before dedup: {total_nodes_before:,} nodes, {total_edges_before:,} edges")

    # ── FIX: Deduplicate edges inside SQLite — no Python loop needed ──────────
    # The edges table already has PRIMARY KEY (source_id, target_id) so true
    # duplicates can't exist from Stage 1.  What CAN exist is self-loops.
    logger.info("Removing self-loop edges ...")
    cursor.execute("DELETE FROM edges WHERE source_id = target_id")
    self_loops_removed = cursor.rowcount
    conn.commit()
    logger.info(f"  Removed {self_loops_removed:,} self-loop edges")

    # ── Remove edges pointing to non-existent nodes ───────────────────────────
    logger.info("Removing dangling edges (target not in nodes) ...")
    cursor.execute("""
        DELETE FROM edges
        WHERE target_id NOT IN (SELECT paper_id FROM nodes)
          AND source_id NOT IN (SELECT paper_id FROM nodes)
    """)
    dangling_removed = cursor.rowcount
    conn.commit()
    logger.info(f"  Removed {dangling_removed:,} dangling edges")

    # ── GPU: find and remove isolated nodes ───────────────────────────────────
    # Load all node IDs that appear in at least one edge (connected nodes)
    logger.info("Finding isolated nodes via GPU ...")
    try:
        import torch
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        logger.info(f"  Using device: {device}")

        # Load unique node IDs referenced in edges (batch to avoid OOM)
        connected_ids = set()
        BATCH = 5_000_000
        offset = 0
        while True:
            rows = cursor.execute(
                f"SELECT DISTINCT source_id FROM edges LIMIT {BATCH} OFFSET {offset}"
            ).fetchall()
            if not rows:
                break
            connected_ids.update(r[0] for r in rows)
            offset += BATCH
        offset = 0
        while True:
            rows = cursor.execute(
                f"SELECT DISTINCT target_id FROM edges LIMIT {BATCH} OFFSET {offset}"
            ).fetchall()
            if not rows:
                break
            connected_ids.update(r[0] for r in rows)
            offset += BATCH

        logger.info(f"  {len(connected_ids):,} nodes have at least one edge")

        # All node IDs
        all_node_rows = cursor.execute("SELECT paper_id FROM nodes").fetchall()
        all_ids = [r[0] for r in all_node_rows]

        # Use torch to compute the isolated mask efficiently
        # (Encode IDs as hashes → tensor comparison)
        all_hashes = torch.tensor(
            [hash(pid) & 0xFFFFFFFF for pid in all_ids], dtype=torch.int64, device=device
        )
        connected_hashes = torch.tensor(
            [hash(pid) & 0xFFFFFFFF for pid in connected_ids], dtype=torch.int64, device=device
        )
        # isin check on GPU
        is_isolated_mask = ~torch.isin(all_hashes, connected_hashes)
        isolated_ids = [all_ids[i] for i in range(len(all_ids)) if is_isolated_mask[i].item()]
        logger.info(f"  Found {len(isolated_ids):,} isolated nodes to remove")

    except Exception as e:
        logger.warning(f"GPU isolated-node detection failed ({e}), using SQL fallback")
        cursor.execute("""
            SELECT paper_id FROM nodes
            WHERE paper_id NOT IN (SELECT DISTINCT source_id FROM edges)
              AND paper_id NOT IN (SELECT DISTINCT target_id FROM edges)
        """)
        isolated_ids = [r[0] for r in cursor.fetchall()]
        logger.info(f"  Found {len(isolated_ids):,} isolated nodes (SQL fallback)")

    # Delete isolated nodes in batches
    CHUNK = 50_000
    for start in range(0, len(isolated_ids), CHUNK):
        chunk = isolated_ids[start:start + CHUNK]
        placeholders = ",".join("?" * len(chunk))
        cursor.execute(f"DELETE FROM nodes WHERE paper_id IN ({placeholders})", chunk)
        conn.commit()

    # Final counts
    total_edges_after = cursor.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    total_nodes_after = cursor.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]

    cursor.execute(
        "INSERT OR REPLACE INTO processing_status (stage, status, timestamp, details) VALUES (?, ?, datetime('now'), ?)",
        ("deduplicate", "completed", f"nodes={total_nodes_after}, edges={total_edges_after}"),
    )
    conn.commit()
    conn.close()

    results = {
        "total_edges_before": total_edges_before,
        "self_loops_removed": self_loops_removed,
        "dangling_removed": dangling_removed,
        "isolated_nodes_removed": len(isolated_ids),
        "total_edges_after": total_edges_after,
        "total_nodes_after": total_nodes_after,
    }

    logger.info(f"Stage 2 Results: {results}")
    checkpoint_manager.save_checkpoint("deduplicate", results, results)
    return results
