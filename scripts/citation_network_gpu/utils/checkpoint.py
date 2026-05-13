"""Checkpoint management for resumable GPU processing."""

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages saving and loading of checkpoints for resumable processing."""

    def __init__(self, checkpoint_dir: Path, enable: bool = True):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.enable = enable
        if self.enable:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, stage: str, data: Any, metadata: Optional[Dict] = None) -> Optional[Path]:
        if not self.enable:
            return None
        checkpoint_path = self.checkpoint_dir / f"{stage}_checkpoint.pkl"
        with open(checkpoint_path, "wb") as f:
            pickle.dump({"data": data, "timestamp": datetime.now().isoformat()}, f)
        logger.info(f"Saved checkpoint: {checkpoint_path}")
        if metadata:
            meta_path = self.checkpoint_dir / f"{stage}_checkpoint_meta.json"
            with open(meta_path, "w") as f:
                json.dump({"stage": stage, "metadata": metadata, "timestamp": datetime.now().isoformat()}, f, indent=2)
        return checkpoint_path

    def load_checkpoint(self, stage: str) -> Optional[Dict]:
        if not self.enable:
            return None
        checkpoint_path = self.checkpoint_dir / f"{stage}_checkpoint.pkl"
        if not checkpoint_path.exists():
            return None
        with open(checkpoint_path, "rb") as f:
            return pickle.load(f)

    def checkpoint_exists(self, stage: str) -> bool:
        if not self.enable:
            return False
        return (self.checkpoint_dir / f"{stage}_checkpoint.pkl").exists()

    def delete_checkpoint(self, stage: str) -> None:
        for suffix in ("_checkpoint.pkl", "_checkpoint_meta.json"):
            p = self.checkpoint_dir / f"{stage}{suffix}"
            if p.exists():
                p.unlink()

    def list_checkpoints(self) -> Dict[str, str]:
        if not self.enable:
            return {}
        return {
            f.stem.replace("_checkpoint", ""): str(f)
            for f in self.checkpoint_dir.glob("*_checkpoint.pkl")
        }


class StageProgress:
    """Track and log progress of a processing stage."""

    def __init__(self, stage_name: str, total_items: int):
        self.stage_name = stage_name
        self.total_items = total_items
        self.processed_items = 0
        self.errors = 0
        self.start_time = datetime.now()

    def update(self, n: int = 1, errors: int = 0) -> None:
        self.processed_items += n
        self.errors += errors

    def elapsed(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    def eta(self) -> float:
        if self.processed_items == 0 or self.total_items == 0:
            return 0.0
        rate = self.processed_items / self.elapsed()
        return (self.total_items - self.processed_items) / rate if rate > 0 else 0.0

    def pct(self) -> float:
        if self.total_items == 0:
            return 0.0
        return 100.0 * self.processed_items / self.total_items

    def log_progress(self) -> None:
        logger.info(
            f"{self.stage_name}: {self.pct():.1f}% ({self.processed_items:,}/{self.total_items:,})"
            f"  ETA {self.eta()/60:.1f} min  errors={self.errors}"
        )
