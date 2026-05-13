"""GPU device management and utilities for multi-GPU processing."""

import logging
import os
from typing import List, Optional

import torch

logger = logging.getLogger(__name__)


class GPUManager:
    """Manages GPU device allocation."""

    def __init__(self, gpu_devices: Optional[List[int]] = None, verbose: bool = False):
        self.verbose = verbose
        self.num_gpus = torch.cuda.device_count()

        if self.num_gpus == 0:
            logger.warning("No CUDA devices found. Using CPU fallback.")
            self.device_ids = []
        else:
            self.device_ids = gpu_devices if gpu_devices is not None else list(range(self.num_gpus))
            logger.info(f"Using GPU devices: {self.device_ids} ({self.num_gpus} total available)")

    def get_device(self, idx: int = 0) -> torch.device:
        if self.device_ids and idx < len(self.device_ids):
            return torch.device(f"cuda:{self.device_ids[idx]}")
        return torch.device("cpu")

    def primary_device(self) -> torch.device:
        return self.get_device(0)

    def print_gpu_memory(self) -> None:
        for gid in self.device_ids:
            used = torch.cuda.memory_allocated(gid) / 1e9
            total = torch.cuda.get_device_properties(gid).total_memory / 1e9
            name = torch.cuda.get_device_properties(gid).name
            logger.info(f"  GPU {gid} ({name}): {used:.2f} / {total:.2f} GB used")

    def clear_cache(self) -> None:
        for gid in self.device_ids:
            with torch.cuda.device(gid):
                torch.cuda.empty_cache()
