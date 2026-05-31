import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CheckpointManager:
    def __init__(
        self,
        checkpoint_dir: Optional[Path] = None,
        enable: bool = True,
        *,
        db_path: Optional[Path] = None,
    ):
        if checkpoint_dir is None:
            checkpoint_dir = Path(db_path).parent / "checkpoints" if db_path else Path("checkpoints")
        self.checkpoint_dir = Path(checkpoint_dir)
        self.enable = enable
        if self.enable:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._stages_file = self.checkpoint_dir / "stages.json"
        self._stages: Dict[str, str] = self._load_stages()

    def _load_stages(self) -> Dict[str, str]:
        if not self.enable or not self._stages_file.exists():
            return {}
        try:
            with open(self._stages_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load stages file: {e}")
            return {}

    def _save_stages(self) -> None:
        if not self.enable:
            return
        try:
            with open(self._stages_file, "w") as f:
                json.dump(self._stages, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save stages file: {e}")

    def check_stage_complete(self, stage: str) -> bool:
        if not self.enable:
            return False
        return self._stages.get(stage) == "complete"

    def mark_stage_complete(self, stage: str) -> None:
        if not self.enable:
            return
        self._stages[stage] = "complete"
        self._save_stages()
        logger.info(f"Stage '{stage}' marked complete in checkpoint")

    def reset_stage(self, stage: str) -> None:
        if stage in self._stages:
            del self._stages[stage]
            self._save_stages()

    def list_complete_stages(self) -> list:
        return [s for s, v in self._stages.items() if v == "complete"]

    def save_checkpoint(self, stage: str, data: Any, metadata: Optional[Dict] = None) -> Optional[Path]:
        if not self.enable:
            return None
        checkpoint_path = self.checkpoint_dir / f"{stage}_checkpoint.pkl"
        try:
            with open(checkpoint_path, "wb") as f:
                pickle.dump({"data": data, "timestamp": datetime.now().isoformat()}, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Saved checkpoint: {checkpoint_path}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint for stage '{stage}': {e}")
            return None
        if metadata:
            meta_path = self.checkpoint_dir / f"{stage}_checkpoint_meta.json"
            try:
                with open(meta_path, "w") as f:
                    json.dump({"stage": stage, "metadata": metadata, "timestamp": datetime.now().isoformat()}, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not save checkpoint metadata for '{stage}': {e}")
        return checkpoint_path

    def load_checkpoint(self, stage: str) -> Optional[Dict]:
        if not self.enable:
            return None
        checkpoint_path = self.checkpoint_dir / f"{stage}_checkpoint.pkl"
        if not checkpoint_path.exists():
            return None
        try:
            with open(checkpoint_path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"Could not load checkpoint for stage '{stage}': {e}")
            return None

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
    STAGE_1 = "stage_1_ingest"
    STAGE_2 = "stage_2_deduplicate"
    STAGE_3 = "stage_3_community"
    STAGE_4 = "stage_4_layout"
    STAGE_5 = "stage_5_export"

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
        elapsed = self.elapsed()
        if elapsed == 0:
            return 0.0
        rate = self.processed_items / elapsed
        return (self.total_items - self.processed_items) / rate if rate > 0 else 0.0

    def pct(self) -> float:
        if self.total_items == 0:
            return 0.0
        return 100.0 * self.processed_items / self.total_items

    def log_progress(self) -> None:
        logger.info(
            f"{self.stage_name}: {self.pct():.1f}%"
            f" ({self.processed_items:,}/{self.total_items:,})"
            f"  ETA {self.eta()/60:.1f} min"
            f"  errors={self.errors}"
        )
