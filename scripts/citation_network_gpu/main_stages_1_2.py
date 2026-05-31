#!/usr/bin/env python3
import argparse
import logging
import sys
import time
from pathlib import Path

from config import PipelineConfig
from stage_1_ingest import ingest_papers
from stage_2_deduplicate import deduplicate_edges
from utils.checkpoint import CheckpointManager, StageProgress
from auto_chunk import auto_chunk_directory

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
    parser = argparse.ArgumentParser(description="Citation Network Pipeline: Stages 1-2")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--reset-db",  action="store_true", default=False)
    parser.add_argument("--db-path",   type=Path, default=Path("citation_network.db"))
    parser.add_argument("--batch-size", type=int, default=10000)
    parser.add_argument("--no-auto-chunk", action="store_true", default=False)
    parser.add_argument("--chunk-size", type=float, default=500.0, metavar="MB")
    args = parser.parse_args()

    if not args.input_dir.exists():
        logger.error(f"Input directory does not exist: {args.input_dir}")
        sys.exit(1)

    logger.info("Citation Network Pipeline — Stages 1-2")
    logger.info(f"Input : {args.input_dir}")
    logger.info(f"DB    : {args.db_path}")
    logger.info(f"Auto-chunk: {'off' if args.no_auto_chunk else f'on ({args.chunk_size} MB)'}")

    if not args.no_auto_chunk:
        # remove_originals=True: after splitting papers_2020.json into chunks,
        # delete the original so PaperDataLoader doesn't see it AND the chunks
        # and process all papers twice.
        result = auto_chunk_directory(
            input_dir=args.input_dir,
            max_mb=args.chunk_size,
            remove_originals=True,
        )
        if result["files_split"] > 0:
            logger.info(
                f"Auto-chunk: split {result['files_split']} file(s) into "
                f"{result['chunks_created']} chunks (originals removed)"
            )

    config = PipelineConfig(
        input_dir=str(args.input_dir),
        db_path=str(args.db_path),
        cache_dir=str(args.db_path.parent / "cache"),
        output_dir=str(args.db_path.parent / "output"),
        reset_db=args.reset_db,
        batch_size=args.batch_size,
    )

    checkpoint = CheckpointManager(db_path=config.db_path)
    start_time = time.time()

    try:
        logger.info("--- STAGE 1: INGEST ---")
        if checkpoint.check_stage_complete(StageProgress.STAGE_1):
            logger.info("Stage 1 already complete — skipping")
        else:
            t = time.time()
            ingest_papers(config)
            checkpoint.mark_stage_complete(StageProgress.STAGE_1)
            logger.info(f"Stage 1 done in {(time.time()-t)/60:.1f} min")

        logger.info("--- STAGE 2: DEDUPLICATE ---")
        if checkpoint.check_stage_complete(StageProgress.STAGE_2):
            logger.info("Stage 2 already complete — skipping")
        else:
            t = time.time()
            deduplicate_edges(config)
            checkpoint.mark_stage_complete(StageProgress.STAGE_2)
            logger.info(f"Stage 2 done in {(time.time()-t)/60:.1f} min")

        logger.info(f"Stages 1-2 complete in {(time.time()-start_time)/60:.1f} min total")
        logger.info(f"DB: {args.db_path}")
        logger.info("Next: python main_stages_3_5.py --db-path " + str(args.db_path))

    except KeyboardInterrupt:
        logger.warning("Interrupted")
        sys.exit(1)
    except Exception as exc:
        logger.error(f"Pipeline failed: {exc}")
        logger.exception("Traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
