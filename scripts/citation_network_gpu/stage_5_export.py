"""Stage 5: Export processed graph for web visualization.

NOTE: Exporting ALL nodes+edges to a single JSON file won't work for large graphs
(50M papers would produce ~500 GB of JSON the browser can't load).

This stage instead produces:
  1. graph_preview.json  — top 500K papers by citation count (browser-loadable)
  2. map_manifest.json   — bounds + metadata for the tile-map view
  3. spatial_index.json  — lightweight position index for the API

For the full graph the Express API server in artifacts/api-server handles
paginated queries directly against the SQLite DB.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List

from config import PipelineConfig
from utils.checkpoint import CheckpointManager, StageProgress

logger = logging.getLogger(__name__)

CLUSTER_COLOURS = [
    "#4F8EF7", "#7C6AF7", "#EC4899", "#06B6D4", "#10B981",
    "#F59E0B", "#EF4444", "#14B8A6", "#F97316", "#6366F1",
    "#84CC16", "#D946EF",
]


def export_stage(config: PipelineConfig) -> Dict:
    """
    Stage 5: Export graph data for the web app.

    Args:
        config: Pipeline configuration.
    Returns:
        Results dictionary with export statistics.
    """
    logger.info("=" * 60)
    logger.info("STAGE 5: EXPORT")
    logger.info("=" * 60)

    checkpoint_manager = CheckpointManager(config.checkpoint_dir, config.enable_checkpointing)
    if checkpoint_manager.checkpoint_exists("export"):
        logger.info("Found existing checkpoint, loading...")
        cp = checkpoint_manager.load_checkpoint("export")
        return cp.get("data", {})

    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA cache_size=-512000")
    cursor = conn.cursor()

    # ── Counts ────────────────────────────────────────────────────────────────
    total_nodes = cursor.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    total_edges = cursor.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    logger.info(f"Total: {total_nodes:,} nodes, {total_edges:,} edges")

    # ── 1. graph_preview.json  (top N papers for the browser network view) ──────
    # ALL papers are in the SQLite DB and shown via the tile map.
    # The network view (Sigma.js WebGL) has a practical browser limit of ~2M nodes.
    # Raise --preview-limit to include more, lower it for slower machines.
    PREVIEW_LIMIT = config.preview_limit
    logger.info(f"Building graph_preview.json (top {PREVIEW_LIMIT:,} papers by citation count) ...")
    logger.info(f"  (ALL {total_nodes:,} papers are in {config.db_path} for tile map + API queries)")

    rows = cursor.execute(f"""
        SELECT n.paper_id, n.title, n.authors, n.year, n.cited_by_count,
               n.community_id, n.field_of_study,
               COALESCE(c.x, n.x) AS x,
               COALESCE(c.y, n.y) AS y
        FROM nodes n
        LEFT JOIN node_coordinates c ON n.paper_id = c.paper_id
        WHERE x IS NOT NULL
        ORDER BY n.cited_by_count DESC
        LIMIT {PREVIEW_LIMIT}
    """).fetchall()

    node_map: Dict[str, int] = {}
    nodes_out: List[Dict] = []
    for row in rows:
        pid = row["paper_id"]
        node_map[pid] = len(nodes_out)
        nodes_out.append({
            "id": pid,
            "label": (row["title"] or "")[:120],
            "year": row["year"],
            "cited_by_count": row["cited_by_count"] or 0,
            "community": row["community_id"],
            "field": row["field_of_study"] or "",
            "authors": (row["authors"] or "").split(";")[:3],
            "x": row["x"],
            "y": row["y"],
        })

    logger.info(f"  {len(nodes_out):,} nodes exported")

    # Edges between preview nodes only
    logger.info("  Building edges for preview nodes ...")
    edges_out: List[Dict] = []
    BATCH = 2_000_000
    offset = 0
    EDGE_LIMIT = config.preview_edge_limit
    while len(edges_out) < EDGE_LIMIT:
        edge_rows = cursor.execute(
            f"SELECT source_id, target_id FROM edges LIMIT {BATCH} OFFSET {offset}"
        ).fetchall()
        if not edge_rows:
            break
        for src, dst in edge_rows:
            si = node_map.get(src)
            di = node_map.get(dst)
            if si is not None and di is not None:
                edges_out.append({"source": si, "target": di})
        offset += BATCH
        logger.info(f"  {len(edges_out):,} preview edges so far (offset={offset:,}) ...")

    # Community colours
    community_ids = sorted({n["community"] for n in nodes_out if n["community"] is not None})
    communities = {
        str(cid): {"name": f"Community {cid}", "color": CLUSTER_COLOURS[i % len(CLUSTER_COLOURS)]}
        for i, cid in enumerate(community_ids)
    }

    preview_data = {
        "metadata": {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "preview_nodes": len(nodes_out),
            "preview_edges": len(edges_out),
            "num_communities": len(communities),
        },
        "nodes": nodes_out,
        "edges": edges_out,
        "communities": communities,
    }

    preview_path = config.output_dir / "graph_preview.json"
    with open(preview_path, "w", encoding="utf-8") as f:
        json.dump(preview_data, f, separators=(",", ":"))

    preview_size_mb = preview_path.stat().st_size / 1e6
    logger.info(f"  graph_preview.json: {preview_size_mb:.1f} MB")

    # ── 2. map_manifest.json ──────────────────────────────────────────────────
    meta_rows = dict(cursor.execute("SELECT key, value FROM metadata").fetchall())
    min_x = float(meta_rows.get("layout_min_x", -1))
    max_x = float(meta_rows.get("layout_max_x", 1))
    min_y = float(meta_rows.get("layout_min_y", -1))
    max_y = float(meta_rows.get("layout_max_y", 1))

    # If no metadata, compute from DB
    if min_x == max_x:
        row = cursor.execute("SELECT MIN(x), MAX(x), MIN(y), MAX(y) FROM nodes WHERE x IS NOT NULL").fetchone()
        if row and row[0] is not None:
            min_x, max_x, min_y, max_y = float(row[0]), float(row[1]), float(row[2]), float(row[3])

    manifest = {
        "available": True,
        "paper_count": total_nodes,
        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
        "max_zoom": 6,
        "tile_size": 256,
        "url_template": "/data/tiles/{z}/{x}/{y}.png",
        "db": str(config.db_path),
    }
    manifest_path = config.output_dir / "map_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info(f"  map_manifest.json written")

    # ── 3. spatial_index.json  (top 500K for API speed) ──────────────────────
    spatial_rows = cursor.execute(f"""
        SELECT n.paper_id, n.cited_by_count, n.community_id, n.year,
               COALESCE(c.x, n.x) AS x, COALESCE(c.y, n.y) AS y
        FROM nodes n
        LEFT JOIN node_coordinates c ON n.paper_id = c.paper_id
        WHERE x IS NOT NULL
        ORDER BY n.cited_by_count DESC
        LIMIT 500000
    """).fetchall()

    spatial_index = [
        {
            "paper_id": r[0],
            "cited_by_count": r[1] or 0,
            "cluster_id": r[2] or 0,
            "year": r[3],
            "x": round(r[4], 6),
            "y": round(r[5], 6),
        }
        for r in spatial_rows if r[4] is not None
    ]

    spatial_path = config.output_dir / "spatial_index.json"
    spatial_path.write_text(json.dumps(spatial_index))
    logger.info(f"  spatial_index.json: {len(spatial_index):,} entries")

    # ── Update DB status ──────────────────────────────────────────────────────
    cursor.execute(
        "INSERT OR REPLACE INTO processing_status (stage, status, timestamp, details) VALUES (?,?,datetime('now'),?)",
        ("export", "completed", f"preview_nodes={len(nodes_out)}, preview_edges={len(edges_out)}"),
    )
    conn.commit()
    conn.close()

    results = {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "preview_nodes_exported": len(nodes_out),
        "preview_edges_exported": len(edges_out),
        "num_communities": len(communities),
        "output_file": str(preview_path),
        "file_size_mb": preview_size_mb,
    }

    logger.info(f"Stage 5 Results: {results}")
    checkpoint_manager.save_checkpoint("export", results, results)
    return results
