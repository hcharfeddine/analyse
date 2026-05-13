"""Graph sharding utilities.

FIX: Original used list.index() — O(N) per edge lookup = catastrophically slow.
     Now uses dict for O(1) lookup.
FIX: Cross-shard edges were incorrectly indexed (target_idx from wrong shard).
     Now all edges stored as (source_global_id, target_global_id) strings;
     tensor conversion happens per-shard with correct local indices.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

logger = logging.getLogger(__name__)


class GraphShard:
    """Represents one GPU's shard of the graph."""

    def __init__(self, shard_id: int, device: torch.device):
        self.shard_id = shard_id
        self.device = device
        self.node_ids: List[str] = []
        self._node_idx: Dict[str, int] = {}  # FIX: O(1) lookup
        self.node_metadata: Dict[str, Dict] = {}
        # Edges stored as global string IDs; resolved to local indices at compute time
        self._edge_src_ids: List[str] = []
        self._edge_dst_ids: List[str] = []

    def add_node(self, node_id: str, metadata: Dict) -> None:
        if node_id not in self._node_idx:
            self._node_idx[node_id] = len(self.node_ids)
            self.node_ids.append(node_id)
            self.node_metadata[node_id] = metadata

    def add_edge(self, source_id: str, target_id: str) -> None:
        """Add edge by global string IDs — resolved to local indices later."""
        self._edge_src_ids.append(source_id)
        self._edge_dst_ids.append(target_id)

    def to_tensor(self) -> Tuple[Optional[torch.Tensor], Optional[torch.Tensor]]:
        """
        Convert edges to (src_indices, dst_indices) tensors using local node indices.
        Skips edges whose endpoints aren't in this shard (cross-shard references).
        """
        srcs, dsts = [], []
        for s, d in zip(self._edge_src_ids, self._edge_dst_ids):
            si = self._node_idx.get(s)
            di = self._node_idx.get(d)
            if si is not None and di is not None:
                srcs.append(si)
                dsts.append(di)

        if not srcs:
            return None, None

        src_t = torch.tensor(srcs, dtype=torch.long, device=self.device)
        dst_t = torch.tensor(dsts, dtype=torch.long, device=self.device)
        return src_t, dst_t

    def num_nodes(self) -> int:
        return len(self.node_ids)

    def num_edges(self) -> int:
        return len(self._edge_src_ids)


class GraphShardManager:
    """Manages sharding of graph across multiple GPUs."""

    def __init__(self, num_shards: int, device_ids: List[int]):
        self.num_shards = num_shards
        self.device_ids = device_ids
        self.shards: List[GraphShard] = []
        for i in range(num_shards):
            device = torch.device(f"cuda:{device_ids[i]}" if torch.cuda.is_available() and i < len(device_ids) else "cpu")
            self.shards.append(GraphShard(i, device))
        logger.info(f"Created {num_shards} graph shards across devices {device_ids}")

    def _shard_for(self, node_id: str) -> int:
        return hash(node_id) % self.num_shards

    def add_node(self, node_id: str, metadata: Dict) -> None:
        shard_id = self._shard_for(node_id)
        self.shards[shard_id].add_node(node_id, metadata)

    def add_edge(self, source_id: str, target_id: str) -> None:
        """
        FIX: Add edge to the source node's shard using global string IDs.
        Cross-shard edges are stored but filtered at tensor-conversion time.
        """
        shard_id = self._shard_for(source_id)
        self.shards[shard_id].add_edge(source_id, target_id)

    def get_shard_stats(self) -> Dict:
        return {
            f"shard_{s.shard_id}": {"num_nodes": s.num_nodes(), "num_edges": s.num_edges()}
            for s in self.shards
        }

    def total_nodes(self) -> int:
        return sum(s.num_nodes() for s in self.shards)

    def total_edges(self) -> int:
        return sum(s.num_edges() for s in self.shards)
