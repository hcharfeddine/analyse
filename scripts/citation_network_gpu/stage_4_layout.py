"""Stage 4: GPU-accelerated graph layout computation.

FIX (critical — would OOM on any real graph):
  Original: delta = pos.unsqueeze(1) - pos.unsqueeze(0)  # shape [N, N, 2]
  For 1M nodes this = 1M × 1M × 2 × 4 bytes = 8 TERABYTES of GPU memory.
  Even for 3,000 nodes it uses 144 MB per iteration — unusable for production.

  Also: attractive force used a Python `for i, j in edges` loop — for 100M
  edges this would take ~3 days regardless of GPU.

FIXED approach (priority order):
  1. cuGraph ForceAtlas2 (GPU) — production-grade, handles 100M+ nodes
  2. Batched FR on GPU — computes repulsive forces in tiles to cap memory use
  3. igraph DRL (CPU, multi-threaded) — best CPU option for large graphs
"""

import logging
import sqlite3
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from config import PipelineConfig
from utils.checkpoint import CheckpointManager, StageProgress

logger = logging.getLogger(__name__)


# ── 1. cuGraph ForceAtlas2 (GPU) — preferred ─────────────────────────────────

def _layout_cugraph(node_ids: List[str], edges: List[Tuple[str, str]],
                    iterations: int) -> Optional[Dict[str, Tuple[float, float]]]:
    try:
        import cudf
        import cugraph
    except ImportError:
        return None

    logger.info(f"  [GPU] cuGraph ForceAtlas2 ({len(node_ids):,} nodes, {len(edges):,} edges, {iterations} iters)")
    node_to_idx = {nid: i for i, nid in enumerate(node_ids)}

    srcs = [node_to_idx[s] for s, t in edges if s in node_to_idx and t in node_to_idx]
    dsts = [node_to_idx[t] for s, t in edges if s in node_to_idx and t in node_to_idx]

    df = cudf.DataFrame({"src": srcs, "dst": dsts})
    G = cugraph.Graph(directed=False)
    G.from_cudf_edgelist(df, source="src", destination="dst")

    t0 = time.time()
    pos = cugraph.layout.force_atlas2(
        G,
        max_iter=iterations,
        strong_gravity_mode=False,
        outbound_attraction_distribution=True,
        lin_log_mode=True,
        barnes_hut_optimize=True,
        barnes_hut_theta=0.5,
        scaling_ratio=2.0,
    )
    logger.info(f"  cuGraph FA2 done in {(time.time()-t0)/60:.1f} min")

    pos_df = pos.sort_values("vertex").to_pandas()
    xs = pos_df["x"].values.astype(np.float32)
    ys = pos_df["y"].values.astype(np.float32)
    return {node_ids[i]: (float(xs[i]), float(ys[i])) for i in range(len(node_ids))}


# ── 2. Batched FR on GPU — memory-safe ───────────────────────────────────────

def _layout_batched_fr(node_ids: List[str], edges: List[Tuple[str, str]],
                       iterations: int, device) -> Dict[str, Tuple[float, float]]:
    """
    FIX: Instead of the O(N²) delta matrix, compute repulsive forces in
    tiles of size TILE × N so peak GPU memory = TILE × N × 2 × 4 bytes.
    With TILE=1024 and N=1M nodes: 1024 × 1M × 8 bytes = 8 GB — safe.
    """
    import torch
    N = len(node_ids)
    TILE = min(1024, N)
    k = 1.0 / (N ** 0.5)

    logger.info(f"  [GPU] Batched FR layout: {N:,} nodes, tile={TILE}, {iterations} iters, device={device}")

    # Build edge index tensor for vectorised attractive force
    node_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    edge_src = torch.tensor(
        [node_to_idx[s] for s, t in edges if s in node_to_idx and t in node_to_idx],
        dtype=torch.long, device=device
    )
    edge_dst = torch.tensor(
        [node_to_idx[t] for s, t in edges if s in node_to_idx and t in node_to_idx],
        dtype=torch.long, device=device
    )

    # Random initial positions
    pos = torch.randn(N, 2, device=device) * 100.0

    for it in range(iterations):
        temperature = 1.0 - it / iterations  # linear cooling

        # ── Repulsive forces (tiled to avoid N×N alloc) ──────────────────────
        disp = torch.zeros(N, 2, device=device)
        for tile_start in range(0, N, TILE):
            tile_end = min(tile_start + TILE, N)
            tile_pos = pos[tile_start:tile_end]                      # [TILE, 2]
            delta = tile_pos.unsqueeze(1) - pos.unsqueeze(0)         # [TILE, N, 2]
            dist = torch.norm(delta, dim=2, keepdim=True).clamp(min=1e-6)  # [TILE, N, 1]
            rep = (delta / dist) * (k * k / dist)                   # [TILE, N, 2]
            disp[tile_start:tile_end] += rep.sum(dim=1)

        # ── Attractive forces (vectorised over edges) ─────────────────────────
        if edge_src.numel() > 0:
            delta_e = pos[edge_dst] - pos[edge_src]                  # [E, 2]
            dist_e = torch.norm(delta_e, dim=1, keepdim=True).clamp(min=1e-6)
            attr = delta_e / dist_e * (dist_e * dist_e / k)          # [E, 2]
            disp.scatter_add_(0, edge_src.unsqueeze(1).expand_as(attr), attr)
            disp.scatter_add_(0, edge_dst.unsqueeze(1).expand_as(attr), -attr)

        # ── Move with cooling ─────────────────────────────────────────────────
        disp_mag = torch.norm(disp, dim=1, keepdim=True).clamp(min=1e-6)
        pos += disp / disp_mag * temperature * k * 10

        if (it + 1) % 10 == 0:
            logger.info(f"  FR iter {it+1}/{iterations}")

    # Normalise to [0, 1]
    pos_min = pos.min(dim=0).values
    pos_max = pos.max(dim=0).values
    pos_n = (pos - pos_min) / (pos_max - pos_min + 1e-9)
    pos_np = pos_n.cpu().numpy()
    return {node_ids[i]: (float(pos_np[i, 0]), float(pos_np[i, 1])) for i in range(N)}


# ── 3. igraph DRL (CPU, multi-threaded) ──────────────────────────────────────

def _layout_igraph_drl(node_ids: List[str], edges: List[Tuple[str, str]]) -> Dict[str, Tuple[float, float]]:
    try:
        import igraph as ig
    except ImportError:
        raise ImportError("Install with: pip install igraph")

    N = len(node_ids)
    logger.info(f"  [CPU] igraph DRL: {N:,} nodes, {len(edges):,} edges")
    node_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    edge_list = [(node_to_idx[s], node_to_idx[t])
                 for s, t in edges if s in node_to_idx and t in node_to_idx]

    g = ig.Graph(n=N, edges=edge_list, directed=False)
    g.simplify()

    t0 = time.time()
    layout = g.layout_drl()
    logger.info(f"  igraph DRL done in {(time.time()-t0)/60:.1f} min")

    xs = np.array([p[0] for p in layout], dtype=np.float32)
    ys = np.array([p[1] for p in layout], dtype=np.float32)
    xs = (xs - xs.min()) / (xs.ptp() + 1e-9)
    ys = (ys - ys.min()) / (ys.ptp() + 1e-9)
    return {node_ids[i]: (float(xs[i]), float(ys[i])) for i in range(N)}


# ── Stage entry point ─────────────────────────────────────────────────────────

def layout_stage(config: PipelineConfig) -> Dict:
    """
    Stage 4: Compute 2-D graph layout.

    Args:
        config: Pipeline configuration.
    Returns:
        Results dictionary with layout statistics.
    """
    logger.info("=" * 60)
    logger.info("STAGE 4: LAYOUT COMPUTATION")
    logger.info("=" * 60)

    checkpoint_manager = CheckpointManager(config.checkpoint_dir, config.enable_checkpointing)
    if checkpoint_manager.checkpoint_exists("layout"):
        logger.info("Found existing checkpoint, loading...")
        cp = checkpoint_manager.load_checkpoint("layout")
        return cp.get("data", {})

    conn = sqlite3.connect(config.db_path)
    conn.execute("PRAGMA cache_size=-512000")
    cursor = conn.cursor()

    logger.info("Loading nodes from database ...")
    node_ids = [r[0] for r in cursor.execute("SELECT paper_id FROM nodes ORDER BY paper_id")]

    logger.info("Loading edges ...")
    edges: List[Tuple[str, str]] = []
    BATCH = 5_000_000
    offset = 0
    while True:
        rows = cursor.execute(
            f"SELECT source_id, target_id FROM edges LIMIT {BATCH} OFFSET {offset}"
        ).fetchall()
        if not rows:
            break
        edges.extend(rows)
        offset += BATCH
        logger.info(f"  {len(edges):,} edges loaded ...")

    logger.info(f"Layout input: {len(node_ids):,} nodes, {len(edges):,} edges")

    layout: Optional[Dict[str, Tuple[float, float]]] = None
    algorithm_used = "unknown"

    # 1. Try cuGraph (GPU)
    try:
        layout = _layout_cugraph(node_ids, edges, config.num_iterations_layout)
        if layout:
            algorithm_used = "cugraph_force_atlas2"
    except Exception as e:
        logger.warning(f"cuGraph layout failed: {e}")

    # 2. Try batched FR on GPU
    if layout is None:
        try:
            import torch
            device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
            logger.info(f"[GPU] Trying batched FR on {device} ...")
            layout = _layout_batched_fr(node_ids, edges, config.num_iterations_layout, device)
            algorithm_used = f"batched_fr_{device.type}"
        except Exception as e:
            logger.warning(f"Batched FR failed: {e}")

    # 3. Fallback: igraph DRL (CPU)
    if layout is None:
        logger.info("[CPU] Falling back to igraph DRL ...")
        layout = _layout_igraph_drl(node_ids, edges)
        algorithm_used = "igraph_drl"

    logger.info(f"Layout computed via {algorithm_used} — writing to DB ...")

    # Write x/y to node_coordinates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS node_coordinates (
            paper_id TEXT PRIMARY KEY,
            x REAL,
            y REAL,
            layout_iteration INTEGER
        )
    """)
    conn.commit()

    data = [(pid, xy[0], xy[1], config.num_iterations_layout) for pid, xy in layout.items()]
    progress = StageProgress("Write coordinates", len(data))
    CHUNK = 50_000
    for start in range(0, len(data), CHUNK):
        conn.executemany(
            "INSERT OR REPLACE INTO node_coordinates (paper_id, x, y, layout_iteration) VALUES (?,?,?,?)",
            data[start:start + CHUNK],
        )
        conn.commit()
        progress.update(CHUNK)
        if (start // CHUNK) % 20 == 0:
            progress.log_progress()

    # Also write x/y into nodes table directly for compatibility with compute_layout.py output
    cursor.execute("SELECT name FROM pragma_table_info('nodes') WHERE name='x'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE nodes ADD COLUMN x REAL")
        cursor.execute("ALTER TABLE nodes ADD COLUMN y REAL")
        conn.commit()

    for start in range(0, len(data), CHUNK):
        conn.executemany(
            "UPDATE nodes SET x=?, y=? WHERE paper_id=?",
            [(d[1], d[2], d[0]) for d in data[start:start + CHUNK]],
        )
        conn.commit()

    cursor.execute(
        "INSERT OR REPLACE INTO processing_status (stage, status, timestamp, details) VALUES (?, ?, datetime('now'), ?)",
        ("layout", "completed", f"nodes={len(layout)}, algorithm={algorithm_used}"),
    )
    conn.commit()
    conn.close()

    results = {
        "num_nodes_positioned": len(layout),
        "layout_algorithm": algorithm_used,
        "num_iterations": config.num_iterations_layout,
    }

    logger.info(f"Stage 4 Results: {results}")
    checkpoint_manager.save_checkpoint("layout", results, results)
    return results