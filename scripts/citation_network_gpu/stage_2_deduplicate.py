import logging
import sqlite3
from typing import Dict

from config import PipelineConfig
from utils.checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


def _recalculate_degrees(conn: sqlite3.Connection) -> None:
    """Recalculate in/out degrees using temp-table GROUP BY aggregation — O(E log E)."""
    cursor = conn.cursor()

    cursor.execute("UPDATE graph_nodes SET in_degree = 0, out_degree = 0")
    conn.commit()

    cursor.execute("""
        CREATE TEMPORARY TABLE IF NOT EXISTS _tmp_out_degrees (
            node_id INTEGER PRIMARY KEY,
            cnt     INTEGER NOT NULL
        )
    """)
    cursor.execute("INSERT INTO _tmp_out_degrees (node_id, cnt) SELECT source_id, COUNT(*) FROM graph_edges GROUP BY source_id")
    conn.commit()
    cursor.execute("""
        UPDATE graph_nodes
        SET out_degree = (SELECT cnt FROM _tmp_out_degrees WHERE node_id = graph_nodes.node_id)
        WHERE node_id IN (SELECT node_id FROM _tmp_out_degrees)
    """)
    conn.commit()
    cursor.execute("DROP TABLE IF EXISTS _tmp_out_degrees")

    cursor.execute("""
        CREATE TEMPORARY TABLE IF NOT EXISTS _tmp_in_degrees (
            node_id INTEGER PRIMARY KEY,
            cnt     INTEGER NOT NULL
        )
    """)
    cursor.execute("INSERT INTO _tmp_in_degrees (node_id, cnt) SELECT target_id, COUNT(*) FROM graph_edges GROUP BY target_id")
    conn.commit()
    cursor.execute("""
        UPDATE graph_nodes
        SET in_degree = (SELECT cnt FROM _tmp_in_degrees WHERE node_id = graph_nodes.node_id)
        WHERE node_id IN (SELECT node_id FROM _tmp_in_degrees)
    """)
    conn.commit()
    cursor.execute("DROP TABLE IF EXISTS _tmp_in_degrees")
    conn.commit()


def deduplicate_stage_optimized(config: PipelineConfig) -> Dict:
    logger.info("=" * 60)
    logger.info("STAGE 2: DEDUPLICATE (INTEGER OPERATIONS)")
    logger.info("=" * 60)

    checkpoint_manager = CheckpointManager(config.checkpoint_dir, config.enable_checkpointing)
    if checkpoint_manager.checkpoint_exists("deduplicate_optimized"):
        logger.info("Found existing checkpoint, loading...")
        cp = checkpoint_manager.load_checkpoint("deduplicate_optimized")
        if cp and "data" in cp:
            return cp["data"]

    conn = sqlite3.connect(str(config.db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-512000")
    conn.execute("PRAGMA wal_autocheckpoint=50000")
    conn.execute("PRAGMA busy_timeout=30000")
    cursor = conn.cursor()

    total_nodes_before = cursor.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
    total_edges_before = cursor.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
    logger.info(f"Before: {total_nodes_before:,} nodes, {total_edges_before:,} edges")

    logger.info("Removing self-loops...")
    cursor.execute("DELETE FROM graph_edges WHERE source_id = target_id")
    self_loops_removed = cursor.rowcount
    conn.commit()

    logger.info("Removing edges with missing source nodes...")
    cursor.execute("""
        DELETE FROM graph_edges
        WHERE NOT EXISTS (SELECT 1 FROM graph_nodes WHERE node_id = graph_edges.source_id)
    """)
    dangling_source = cursor.rowcount
    conn.commit()

    logger.info("Removing edges with missing target nodes...")
    cursor.execute("""
        DELETE FROM graph_edges
        WHERE NOT EXISTS (SELECT 1 FROM graph_nodes WHERE node_id = graph_edges.target_id)
    """)
    dangling_target = cursor.rowcount
    conn.commit()
    dangling_removed = dangling_source + dangling_target

    logger.info("Recalculating degree counters...")
    _recalculate_degrees(conn)

    total_nodes_after = cursor.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
    total_edges_after = cursor.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
    avg_in  = cursor.execute("SELECT AVG(in_degree)  FROM graph_nodes").fetchone()[0] or 0
    avg_out = cursor.execute("SELECT AVG(out_degree) FROM graph_nodes").fetchone()[0] or 0

    cursor.execute(
        "INSERT OR REPLACE INTO processing_status (stage, status, timestamp, details) VALUES (?, ?, datetime('now'), ?)",
        (
            "deduplicate_optimized",
            "completed",
            f"nodes={total_nodes_after}, edges={total_edges_after}, avg_in={avg_in:.2f}, avg_out={avg_out:.2f}",
        ),
    )
    conn.commit()
    conn.close()

    results = {
        "total_nodes_before":     total_nodes_before,
        "total_edges_before":     total_edges_before,
        "self_loops_removed":     self_loops_removed,
        "dangling_edges_removed": dangling_removed,
        "total_nodes_after":      total_nodes_after,
        "total_edges_after":      total_edges_after,
        "avg_in_degree":          round(avg_in, 2),
        "avg_out_degree":         round(avg_out, 2),
    }

    logger.info("Stage 2 Results:")
    for key, value in results.items():
        logger.info(f"  {key}: {value}")

    checkpoint_manager.save_checkpoint("deduplicate_optimized", results, results)
    return results


def deduplicate_edges(config: PipelineConfig) -> Dict:
    return deduplicate_stage_optimized(config)
