#!/usr/bin/env python3
"""
Main entry point for Stages 3-5: GPU Analysis and Export
========================================================

Runs after graph building (stages 1-2) is complete.

Stages:
  - Stage 3: Community Detection (GPU Louvain)
  - Stage 4: Layout Computation (ForceAtlas2)
  - Stage 5: Export with Pagination

Usage:
  python main_stages_3_5.py [--gpu-id 0] [--force-recompute]

Prerequisites:
  - Must run main_stages_1_2.py first
  - Database must contain graph_nodes and graph_edges
  - NVIDIA GPU recommended (CUDA 11.8+)

Output:
  - Community assignments
  - Node positions (x, y)
  - Paginated JSON exports
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Stage imports
from stage_3_community import run_community_detection
from stage_4_layout import run_layout_computation
from stage_5_export import run_export_with_pagination

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run GPU analysis and export (Stages 3-5) on citation network',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standard run with GPU 0
  python main_stages_3_5.py

  # Use GPU 1 with forced recomputation
  python main_stages_3_5.py --gpu-id 1 --force-recompute

  # Export to specific directory
  python main_stages_3_5.py --export-dir ./my_exports

  # Skip export, only compute communities and layout
  python main_stages_3_5.py --skip-export
        """
    )
    parser.add_argument(
        '--gpu-id',
        type=int,
        default=0,
        help='GPU ID to use (default: 0)'
    )
    parser.add_argument(
        '--force-recompute',
        action='store_true',
        help='Force recomputation of community detection and layout'
    )
    parser.add_argument(
        '--skip-export',
        action='store_true',
        help='Skip export step, only compute communities and layout'
    )
    parser.add_argument(
        '--export-dir',
        type=str,
        default='./exports',
        help='Directory for export files (default: ./exports)'
    )
    parser.add_argument(
        '--layout-algorithm',
        type=str,
        default='forceatlas2',
        choices=['forceatlas2', 'spring', 'kamada-kawai'],
        help='Layout algorithm to use (default: forceatlas2)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10000,
        help='Batch size for processing (default: 10000)'
    )

    return parser.parse_args()


def main():
    """Main entry point for stages 3-5."""
    args = parse_args()
    
    logger.info("=" * 80)
    logger.info("CITATION NETWORK - GPU ANALYSIS & EXPORT (Stages 3-5)")
    logger.info("=" * 80)
    logger.info(f"GPU ID: {args.gpu_id}")
    logger.info(f"Force Recompute: {args.force_recompute}")
    logger.info(f"Export Directory: {args.export_dir}")
    logger.info(f"Layout Algorithm: {args.layout_algorithm}")
    logger.info("=" * 80)
    
    try:
        # Stage 3: Community Detection
        logger.info("\n[Stage 3/3] Running Community Detection...")
        logger.info("-" * 80)
        
        community_result = run_community_detection(
            gpu_id=args.gpu_id,
            force_recompute=args.force_recompute,
            batch_size=args.batch_size
        )
        
        if not community_result.get('success'):
            logger.error("Community detection failed")
            return 1
        
        logger.info(f"✓ Community Detection Complete")
        logger.info(f"  - Modularity: {community_result.get('modularity', 'N/A'):.4f}")
        logger.info(f"  - Communities: {community_result.get('num_communities', 'N/A')}")
        logger.info(f"  - Time: {community_result.get('time_seconds', 'N/A'):.2f}s")

        # Stage 4: Layout Computation
        logger.info("\n[Stage 4/5] Running Layout Computation...")
        logger.info("-" * 80)
        
        layout_result = run_layout_computation(
            algorithm=args.layout_algorithm,
            gpu_id=args.gpu_id,
            force_recompute=args.force_recompute,
            batch_size=args.batch_size
        )
        
        if not layout_result.get('success'):
            logger.error("Layout computation failed")
            return 1
        
        logger.info(f"✓ Layout Computation Complete")
        logger.info(f"  - Algorithm: {args.layout_algorithm}")
        logger.info(f"  - Time: {layout_result.get('time_seconds', 'N/A'):.2f}s")

        # Stage 5: Export (optional)
        if not args.skip_export:
            logger.info("\n[Stage 5/5] Running Export with Pagination...")
            logger.info("-" * 80)
            
            export_result = run_export_with_pagination(
                export_dir=args.export_dir,
                batch_size=args.batch_size
            )
            
            if not export_result.get('success'):
                logger.error("Export failed")
                return 1
            
            logger.info(f"✓ Export Complete")
            logger.info(f"  - Export Directory: {args.export_dir}")
            logger.info(f"  - Files Created: {export_result.get('num_files', 'N/A')}")
            logger.info(f"  - Time: {export_result.get('time_seconds', 'N/A'):.2f}s")
        else:
            logger.info("\n[Stage 5/5] Skipped (--skip-export)")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("✓ GPU ANALYSIS & EXPORT PIPELINE COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Completed at: {datetime.now().isoformat()}")
        
        return 0

    except KeyboardInterrupt:
        logger.warning("\n\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\n✗ Pipeline failed with error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
