"""
GPU-accelerated Citation Network Pipeline Orchestrator.

Main entry point for the complete citation network processing pipeline.

Usage:
    python main.py --input-dir /path/to/papers --db public/data/citation_network.db

    # Resume from layout stage
    python main.py --input-dir /path/to/papers --resume-from layout

    # Use specific GPUs
    python main.py --input-dir /path/to/papers --gpu-devices 0,1,2,3
"""

import logging
import sys
import time
from pathlib import Path

from config import parse_args
from stage_1_ingest import ingest_stage
from stage_2_deduplicate import deduplicate_stage
from stage_3_community import community_detection_stage
from stage_4_layout import layout_stage
from stage_5_export import export_stage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def run_pipeline(config):
    """
    Run the complete GPU-accelerated citation network pipeline.

    Args:
        config: Pipeline configuration.
    """
    logger.info("=" * 70)
    logger.info("GPU-ACCELERATED CITATION NETWORK PIPELINE")
    logger.info("=" * 70)
    logger.info(f"Input directory: {config.input_dir}")
    logger.info(f"Database: {config.db_path}")
    logger.info(f"Number of GPUs: {config.num_gpus}")
    logger.info(f"GPU devices: {config.gpu_devices}")
    logger.info(f"Checkpointing enabled: {config.enable_checkpointing}")
    logger.info("=" * 70)

    start_time = time.time()
    results = {}

    # Define pipeline stages
    stages = [
        ("ingest", ingest_stage, "Load papers and create GPU graph shards"),
        (
            "deduplicate",
            deduplicate_stage,
            "Remove duplicate edges and isolated nodes",
        ),
        (
            "community",
            community_detection_stage,
            "Detect communities using GPU Louvain",
        ),
        ("layout", layout_stage, "Compute layout with GPU FR algorithm"),
        ("export", export_stage, "Export graph to JSON for web visualization"),
    ]

    # Determine which stages to run
    if config.resume_from:
        stage_names = [s[0] for s in stages]
        resume_idx = stage_names.index(config.resume_from)
        stages_to_run = stages[resume_idx:]
        logger.info(f"Resuming from stage: {config.resume_from}")
    else:
        stages_to_run = stages

    # Skip specified stages
    if config.skip_stages:
        stages_to_run = [s for s in stages_to_run if s[0] not in config.skip_stages]
        logger.info(f"Skipping stages: {config.skip_stages}")

    # Run stages
    for stage_name, stage_func, description in stages_to_run:
        logger.info("")
        logger.info(f"Running: {description}")
        logger.info(f"Stage: {stage_name.upper()}")

        stage_start = time.time()

        try:
            stage_result = stage_func(config)
            results[stage_name] = stage_result
            stage_elapsed = time.time() - stage_start

            logger.info(f"✓ {stage_name} completed in {stage_elapsed:.1f}s")

        except Exception as e:
            logger.error(f"✗ {stage_name} failed with error: {e}")
            logger.exception("Full traceback:")
            raise

    # Pipeline complete
    total_elapsed = time.time() - start_time

    logger.info("")
    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f}m)")
    logger.info("")

    # Print summary
    logger.info("RESULTS SUMMARY:")
    for stage_name, stage_result in results.items():
        logger.info(f"\n{stage_name.upper()}:")
        if isinstance(stage_result, dict):
            for key, value in stage_result.items():
                if not isinstance(value, dict):
                    logger.info(f"  {key}: {value}")

    # Print final output location
    if "export" in results:
        output_file = results["export"].get("output_file")
        if output_file:
            logger.info(f"\n✓ Graph data exported to: {output_file}")
            logger.info("  Use this file in your web visualization app")

    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Start the Next.js web app: npm run dev")
    logger.info("2. Open http://localhost:3000 in your browser")
    logger.info("3. Explore the citation network!")
    logger.info("")

    return results


if __name__ == "__main__":
    try:
        config = parse_args()
        run_pipeline(config)
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
