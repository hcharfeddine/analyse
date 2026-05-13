"""Configuration and CLI argument parsing for GPU citation network pipeline."""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PipelineConfig:
    """Configuration for the GPU citation network pipeline."""

    # Input/Output paths
    input_dir: Path
    db_path: Path
    cache_dir: Path
    output_dir: Path

    # GPU settings
    num_gpus: int = 8
    gpu_devices: Optional[list] = None
    batch_size: int = 10000
    max_memory_per_gpu_gb: float = 20.0

    # Processing settings
    reset_db: bool = False
    skip_stages: list = None
    resume_from: Optional[str] = None
    commit_every: int = 50000

    # Algorithm settings
    layout_algorithm: str = "fruchterman_reingold"
    community_algorithm: str = "louvain"
    num_iterations_layout: int = 100
    num_iterations_community: int = 20

    # Checkpointing
    enable_checkpointing: bool = True
    checkpoint_dir: Optional[Path] = None

    # Logging
    verbose: bool = False
    log_file: Optional[Path] = None

    def __post_init__(self):
        """Validate and setup paths."""
        self.input_dir = Path(self.input_dir)
        self.db_path = Path(self.db_path)
        self.cache_dir = Path(self.cache_dir)
        self.output_dir = Path(self.output_dir)

        # Create directories
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.checkpoint_dir is None:
            self.checkpoint_dir = self.cache_dir / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Validate input directory
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")

        # Setup GPU devices
        if self.gpu_devices is None:
            self.gpu_devices = list(range(self.num_gpus))

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            "input_dir": str(self.input_dir),
            "db_path": str(self.db_path),
            "cache_dir": str(self.cache_dir),
            "output_dir": str(self.output_dir),
            "num_gpus": self.num_gpus,
            "gpu_devices": self.gpu_devices,
            "batch_size": self.batch_size,
            "max_memory_per_gpu_gb": self.max_memory_per_gpu_gb,
            "reset_db": self.reset_db,
            "skip_stages": self.skip_stages or [],
            "resume_from": self.resume_from,
            "layout_algorithm": self.layout_algorithm,
            "community_algorithm": self.community_algorithm,
            "enable_checkpointing": self.enable_checkpointing,
            "verbose": self.verbose,
        }

    @staticmethod
    def save(config: "PipelineConfig", path: Path) -> None:
        """Save config to JSON file."""
        with open(path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

    @staticmethod
    def load(path: Path) -> "PipelineConfig":
        """Load config from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return PipelineConfig(**data)


def parse_args() -> PipelineConfig:
    """Parse command-line arguments and return PipelineConfig."""
    parser = argparse.ArgumentParser(
        description="GPU-accelerated citation network pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline with 8 GPUs
  python main.py --input-dir /path/to/papers --db public/data/citation_network.db

  # Resume from a checkpoint
  python main.py --input-dir /path/to/papers --db public/data/citation_network.db --resume-from layout

  # Skip specific stages
  python main.py --input-dir /path/to/papers --skip-stages ingest deduplicate

  # Use only 4 GPUs
  python main.py --input-dir /path/to/papers --num-gpus 4
        """,
    )

    # Required arguments
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing per-year JSON paper files",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="public/data/citation_network.db",
        help="Output SQLite database path (default: public/data/citation_network.db)",
    )

    # Optional arguments
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="public/data/graph_cache",
        help="Directory for GPU cache and intermediate files (default: public/data/graph_cache)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="public/data",
        help="Output directory for tiles and JSON (default: public/data)",
    )
    parser.add_argument(
        "--num-gpus",
        type=int,
        default=8,
        help="Number of GPUs to use (default: 8)",
    )
    parser.add_argument(
        "--gpu-devices",
        type=str,
        default=None,
        help="Comma-separated list of GPU device IDs (default: 0-7)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="Batch size for processing (default: 10000)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database (delete existing and start fresh)",
    )
    parser.add_argument(
        "--skip-stages",
        type=str,
        default=None,
        help="Comma-separated list of stages to skip (ingest, deduplicate, community, layout, export)",
    )
    parser.add_argument(
        "--resume-from",
        type=str,
        default=None,
        choices=["ingest", "deduplicate", "community", "layout", "export"],
        help="Resume pipeline from a specific stage",
    )
    parser.add_argument(
        "--layout-algorithm",
        type=str,
        default="fruchterman_reingold",
        choices=["fruchterman_reingold", "spring", "custom_gpu"],
        help="Graph layout algorithm (default: fruchterman_reingold)",
    )
    parser.add_argument(
        "--community-algorithm",
        type=str,
        default="louvain",
        choices=["louvain", "leiden", "degree_clustering"],
        help="Community detection algorithm (default: louvain)",
    )
    parser.add_argument(
        "--num-layout-iterations",
        type=int,
        default=100,
        help="Number of layout iterations (default: 100)",
    )
    parser.add_argument(
        "--no-checkpointing",
        action="store_true",
        help="Disable checkpointing (not recommended)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    # Parse GPU devices
    gpu_devices = None
    if args.gpu_devices:
        gpu_devices = [int(x.strip()) for x in args.gpu_devices.split(",")]

    # Parse skip stages
    skip_stages = None
    if args.skip_stages:
        skip_stages = [x.strip().lower() for x in args.skip_stages.split(",")]

    return PipelineConfig(
        input_dir=args.input_dir,
        db_path=Path(args.db),
        cache_dir=Path(args.cache_dir),
        output_dir=Path(args.output_dir),
        num_gpus=args.num_gpus,
        gpu_devices=gpu_devices,
        batch_size=args.batch_size,
        reset_db=args.reset,
        skip_stages=skip_stages,
        resume_from=args.resume_from,
        layout_algorithm=args.layout_algorithm,
        community_algorithm=args.community_algorithm,
        num_iterations_layout=args.num_layout_iterations,
        enable_checkpointing=not args.no_checkpointing,
        verbose=args.verbose,
    )
