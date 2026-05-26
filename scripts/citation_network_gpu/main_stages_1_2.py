#!/usr/bin/env python3
"""
Main entry point for Citation Network Pipeline: STAGES 1-2 ONLY
═══════════════════════════════════════════════════════════════

Builds the optimized graph with:
1. Stage 1: Ingest data → integer mappings → filter isolated papers
2. Stage 2: Deduplicate edges

This is the OPTIMIZED PIPELINE with:
✓ Pseudo-integer node IDs (6-10x faster operations)
✓ Lightweight database schema
✓ Filtering of isolated papers (no citations)
✓ Batched processing

Output: graph_nodes, graph_edges tables + mapping tables
Expected runtime: 7-10 minutes for 54M papers

Usage:
    python main_stages_1_2.py --input-dir /path/to/papers --reset-db

Options:
    --input-dir       Path to directory with JSON paper files
    --reset-db        Drop and recreate tables (default: False)
    --db-path         SQLite database path (default: citation_network.db)
    --batch-size      Batch size for processing (default: 10000)
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from config import PipelineConfig
from stage_1_ingest import ingest_papers
from stage_2_deduplicate import deduplicate_edges
from utils.checkpoint import CheckpointManager, StageProgress

# ── Setup logging ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline_stages_1_2.log"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    """Run stages 1-2 of the citation network pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing JSON paper files",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        default=False,
        help="Drop and recreate database tables",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("citation_network.db"),
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="Batch size for processing",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.input_dir.exists():
        logger.error(f"Input directory does not exist: {args.input_dir}")
        sys.exit(1)

    # Configure pipeline
    config = PipelineConfig(
        input_dir=str(args.input_dir),
        db_path=str(args.db_path),
        reset_db=args.reset_db,
        batch_size=args.batch_size,
    )

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  Citation Network Pipeline: Stages 1-2 (Graph Building) ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info(f"Input directory: {args.input_dir}")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Reset DB: {args.reset_db}")
    logger.info(f"Batch size: {args.batch_size}")

    checkpoint = CheckpointManager(db_path=config.db_path)
    
    start_time = time.time()

    try:
        # Stage 1: Ingest papers + create integer mappings + filter isolated
        logger.info("\n" + "=" * 60)
        logger.info("STAGE 1: INGEST PAPERS & BUILD INTEGER MAPPINGS")
        logger.info("=" * 60)
        
        if checkpoint.check_stage_complete(StageProgress.STAGE_1):
            logger.info("✓ Stage 1 already complete (checkpoint found)")
        else:
            stage_1_start = time.time()
            ingest_papers(config)
            stage_1_time = time.time() - stage_1_start
            checkpoint.mark_stage_complete(StageProgress.STAGE_1)
            logger.info(f"✓ Stage 1 complete in {stage_1_time/60:.1f} minutes")

        # Stage 2: Deduplicate edges
        logger.info("\n" + "=" * 60)
        logger.info("STAGE 2: DEDUPLICATE EDGES")
        logger.info("=" * 60)
        
        if checkpoint.check_stage_complete(StageProgress.STAGE_2):
            logger.info("✓ Stage 2 already complete (checkpoint found)")
        else:
            stage_2_start = time.time()
            deduplicate_edges(config)
            stage_2_time = time.time() - stage_2_start
            checkpoint.mark_stage_complete(StageProgress.STAGE_2)
            logger.info(f"✓ Stage 2 complete in {stage_2_time/60:.1f} minutes")

        # Final summary
        total_time = time.time() - start_time
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total time: {total_time/60:.1f} minutes")
        logger.info("\nNext steps:")
        logger.info("  1. Review graph statistics in database")
        logger.info("  2. Run main_stages_3_4.py for community detection & layout")
        logger.info("  3. Run main_stages_4_5.py for export")

    except Exception as e:
        logger.error(f"\n✗ Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
