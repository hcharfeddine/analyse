
import asyncio
import logging
import sys
import os
import json

# Add the directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.base_client import OpenAlexClient
from models.paper import Paper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_extraction():
    async with OpenAlexClient() as client:
        # Search for a well-known paper that MUST have citations
        logger.info("Searching for papers to test extraction...")
        papers = await client.search("machine learning", 2020, 5)
        
        if not papers:
            logger.error("No papers found to test.")
            return

        all_zeros = True
        for paper in papers:
            logger.info(f"--- Paper: {paper.title} ---")
            logger.info(f"Citation Count: {paper.cited_by_count}")
            if paper.cited_by_count > 0:
                all_zeros = False
        
        if all_zeros:
            logger.error("VERIFICATION FAILED: All citation counts are still 0")
        else:
            logger.info("VERIFICATION SUCCESS: Citation counts extracted correctly")

if __name__ == "__main__":
    asyncio.run(test_extraction())
