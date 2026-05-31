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


def verify_gpu_setup():
    """Check GPU and RAPIDS availability before running pipeline."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("GPU SETUP VERIFICATION")
    logger.info("=" * 70)
    
    # Check CUDA
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            device_count = torch.cuda.device_count()
            logger.info(f"✓ CUDA available: {device_count} GPU(s) detected")
            for i in range(min(device_count, 8)):
                props = torch.cuda.get_device_properties(i)
                logger.info(f"  GPU {i}: {props.name} ({props.total_memory / 1e9:.1f} GB VRAM)")
        else:
            logger.error("✗ CUDA NOT available. GPU acceleration DISABLED.")
            logger.error("  GPU will not be used — pipeline will run on CPU (SLOW).")
            return False
    except Exception as e:
        logger.error(f"✗ PyTorch/CUDA check failed: {e}")
        return False
    
    # Check RAPIDS for Stage 3 (Community Detection)
    rapids_available = False
    try:
        import cudf
        import cugraph
        rapids_available = True
        logger.info("✓ RAPIDS (cudf + cugraph) available")
        logger.info("  → Stage 3 will use GPU Louvain (FAST)")
    except ImportError as e:
        logger.warning(f"⚠️  RAPIDS not available: {e}")
        logger.warning("  → Stage 3 will use CPU Louvain (SLOW on large graphs)")
        logger.warning("")
        logger.warning("  To enable GPU community detection, install RAPIDS:")
        logger.warning("    pip install cudf-cu12 cugraph-cu12  # For CUDA 12")
        logger.warning("    # OR for CUDA 11:")
        logger.warning("    pip install cudf-cu11 cugraph-cu11")
    
    # Check igraph for Stage 4 fallback
    igraph_available = False
    try:
        import igraph
        igraph_available = True
        logger.info("✓ igraph available (Stage 4 CPU layout fallback)")
    except ImportError:
        logger.warning("⚠️  igraph not installed")
        logger.warning("  → Stage 4 CPU fallback will fail without this")
        logger.warning("  Install with: pip install igraph")
    
    logger.info("")
    logger.info("Summary:")
    logger.info(f"  CUDA: {'✓' if cuda_available else '✗'}")
    logger.info(f"  RAPIDS: {'✓' if rapids_available else '✗ (GPU Louvain will fail)'}")
    logger.info(f"  igraph: {'✓' if igraph_available else '✗ (CPU DRL will fail)'}")
    
    if not rapids_available:
        logger.warning("")
        logger.warning("WARNING: RAPIDS not available! Stage 3 will use CPU Louvain,")
        logger.warning("which can take WEEKS for 50M+ papers. Consider installing RAPIDS.")
    
    logger.info("=" * 70)
    logger.info("")
    
    return cuda_available


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
        
        # Verify GPU setup before running
        gpu_ok = verify_gpu_setup()
        if not gpu_ok:
            logger.warning("GPU unavailable. Pipeline will fall back to CPU (may be VERY slow).")
        
        run_pipeline(config)
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
