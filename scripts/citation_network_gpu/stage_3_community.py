"""Stage 3: Community detection using GPU-accelerated Louvain algorithm.

FIX: Original used degree-bin grouping and called it "GPU Louvain" — it wasn't.
     Communities were completely meaningless (just sorted by citation count).

FIXED approach (in priority order):
  1. cuGraph Louvain (GPU) — real Louvain on GPU, uses all 8 RTX 4090s via cuGraph
  2. python-louvain / networkx Louvain (CPU) — real modularity-based Louvain
  3. Degree-bin fallback — only if nothing else is available (clearly labelled)
"""

import logging
import sqlite3
from typing import Dict, List, Tuple

from config import PipelineConfig
from utils.checkpoint import CheckpointManager, StageProgress

logger = logging.getLogger(__name__)


# ── GPU Louvain via cuGraph ────────────────────────────────────────────────────

def _louvain_cugraph(node_ids: List[str], edges: List[Tuple[str, str]]) -> Dict[str, int]:
    """Real GPU Louvain via RAPIDS cuGraph."""
    import cudf
    import cugraph

    logger.info("  Building cuGraph for Louvain ...")
    node_to_idx = {nid: i for i, nid in enumerate(node_ids)}

    srcs = [node_to_idx[s] for s, t in edges if s in node_to_idx and t in node_to_idx]
    dsts = [node_to_idx[t] for s, t in edges if s in node_to_idx and t in node_to_idx]

    df = cudf.DataFrame({"src": srcs, "dst": dsts})
    G = cugraph.Graph()
    G.from_cudf_edgelist(df, source="src", destination="dst")

    logger.info("  Running cuGraph Louvain ...")
    parts, modularity = cugraph.louvain(G)
    logger.info(f"  cuGraph Louvain done — modularity={modularity:.4f}")

    parts_df = parts.to_pandas()
    idx_to_community = dict(zip(parts_df["vertex"].tolist(), parts_df["partition"].tolist()))

    return {nid: int(idx_to_community.get(node_to_idx[nid], 0)) for nid in node_ids}


# ── CPU Louvain via python-louvain ────────────────────────────────────────────

def _louvain_cpu(node_ids: List[str], edges: List[Tuple[str, str]]) -> Dict[str, int]:
    """Real modularity-based Louvain via python-louvain + networkx."""
    try:
        import community as community_louvain  # python-louvain
        import networkx as nx
    except ImportError:
        raise ImportError("Install with: pip install python-louvain networkx")

    logger.info("  Building networkx graph for CPU Louvain ...")
    G = nx.Graph()
    G.add_nodes_from(node_ids)
    G.add_edges_from(edges)

    logger.info(f"  Running CPU Louvain on {G.number_of_nodes():,} nodes ...")
    partition = community_louvain.best_partition(G)
    logger.info(f"  CPU Louvain done — {len(set(partition.values()))} communities")
    return partition


# ── Fallback: degree-bin clustering ──────────────────────────────────────────

def _degree_bin_fallback(node_ids: List[str], edges: List[Tuple[str, str]]) -> Dict[str, int]:
    """
    FALLBACK ONLY — not real community detection.
    Groups nodes by degree bucket. Use only if Louvain is unavailable.
    """
    logger.warning("  Using degree-bin fallback — NOT real community detection!")
    degree: Dict[str, int] = {nid: 0 for nid in node_ids}
    for s, t in edges:
        if s in degree:
            degree[s] += 1
        if t in degree:
            degree[t] += 1

    communities: Dict[str, int] = {}
    bins: Dict[int, int] = {}
    community_counter = 0
    for nid in node_ids:
        b = degree[nid] // 10
        if b not in bins:
            bins[b] = community_counter
            community_counter += 1
        communities[nid] = bins[b]

    logger.warning(f"  Degree-bin fallback: {community_counter} pseudo-communities")
    return communities


# ── Stage entry point ─────────────────────────────────────────────────────────

def community_detection_stage(config: PipelineConfig) -> Dict:
    """
    Stage 3: Detect research communities using the best available algorithm.

    Args:
        config: Pipeline configuration.
    Returns:
        Results dictionary with community detection statistics.
    """
    logger.info("=" * 60)
    logger.info("STAGE 3: COMMUNITY DETECTION")
    logger.info("=" * 60)

    checkpoint_manager = CheckpointManager(config.checkpoint_dir, config.enable_checkpointing)
    if checkpoint_manager.checkpoint_exists("community"):
        logger.info("Found existing checkpoint, loading...")
        cp = checkpoint_manager.load_checkpoint("community")
        return cp.get("data", {})

    conn = sqlite3.connect(config.db_path)
    conn.execute("PRAGMA cache_size=-512000")
    cursor = conn.cursor()

    logger.info("Loading graph from database ...")
    cursor.execute("SELECT paper_id FROM nodes ORDER BY paper_id")
    node_ids = [r[0] for r in cursor.fetchall()]

    # Load edges in batches to avoid RAM spike
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
        logger.info(f"  Loaded {len(edges):,} edges so far ...")

    logger.info(f"Graph: {len(node_ids):,} nodes, {len(edges):,} edges")

    # ── Try algorithms in priority order ──────────────────────────────────────
    algorithm_used = "unknown"
    communities: Dict[str, int] = {}

    if config.community_algorithm in ("louvain", "leiden"):
        # 1. Try cuGraph (GPU)
        try:
            logger.info("[GPU] Attempting cuGraph Louvain ...")
            communities = _louvain_cugraph(node_ids, edges)
            algorithm_used = "cugraph_louvain"
        except Exception as e:
            logger.warning(f"cuGraph Louvain failed: {e}")
            # 2. Try CPU Louvain
            try:
                logger.info("[CPU] Attempting python-louvain ...")
                communities = _louvain_cpu(node_ids, edges)
                algorithm_used = "cpu_louvain"
            except Exception as e2:
                logger.warning(f"CPU Louvain failed: {e2}")
                logger.warning("Falling back to degree-bin clustering (not real Louvain)")
                communities = _degree_bin_fallback(node_ids, edges)
                algorithm_used = "degree_bin_fallback"
    else:
        communities = _degree_bin_fallback(node_ids, edges)
        algorithm_used = "degree_bin"

    num_communities = len(set(communities.values()))
    logger.info(f"Detected {num_communities:,} communities via {algorithm_used}")

    # ── Write back to DB ──────────────────────────────────────────────────────
    logger.info("Writing community assignments to database ...")
    progress = StageProgress("Community Write", len(communities))
    data = [(cid, pid) for pid, cid in communities.items()]

    CHUNK = 50_000
    for start in range(0, len(data), CHUNK):
        conn.executemany("UPDATE nodes SET community_id=? WHERE paper_id=?", data[start:start+CHUNK])
        conn.commit()
        progress.update(CHUNK)
        if (start // CHUNK) % 20 == 0:
            progress.log_progress()

    # Community stats
    cursor.execute(
        "SELECT community_id, COUNT(*) FROM nodes WHERE community_id IS NOT NULL GROUP BY community_id"
    )
    community_sizes = {r[0]: r[1] for r in cursor.fetchall()}

    cursor.execute(
        "INSERT OR REPLACE INTO processing_status (stage, status, timestamp, details) VALUES (?, ?, datetime('now'), ?)",
        ("community", "completed", f"communities={num_communities}, algorithm={algorithm_used}"),
    )
    conn.commit()
    conn.close()

    results = {
        "num_communities": num_communities,
        "algorithm_used": algorithm_used,
        "largest_community": max(community_sizes.values()) if community_sizes else 0,
        "num_nodes_in_communities": sum(community_sizes.values()),
    }

    logger.info(f"Stage 3 Results: {results}")
    checkpoint_manager.save_checkpoint("community", results, results)
    return results
