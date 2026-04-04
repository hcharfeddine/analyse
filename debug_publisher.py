
import asyncio
import logging
import sys
import os
import json

# Add the directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_clients import OpenAlexClient
from models import Paper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_extraction():
    async with OpenAlexClient() as client:
        # We'll use a specific ID from previous results to inspect raw data
        paper_id = "W4362663195"
        logger.info(f"Fetching raw data for paper: {paper_id}")
        
        url = f"https://api.openalex.org/works/{paper_id}"
        async with client.session.get(url) as response:
            data = await response.json()
            # Log the entire data structure to see where publisher might be
            # logger.info(json.dumps(data, indent=2))
            
            logger.info(f"Top-level publisher: {data.get('publisher')}")
            
            primary_loc = data.get('primary_location') or {}
            source = primary_loc.get('source') or {}
            logger.info(f"Source: {json.dumps(source, indent=2)}")
            
            # Check for other fields
            logger.info(f"Host venue: {json.dumps(data.get('host_venue'), indent=2)}")
            
            # Check for 'publisher' in 'locations'
            for i, loc in enumerate(data.get('locations', [])):
                s = loc.get('source') or {}
                logger.info(f"Location {i} source publisher: {s.get('publisher')}")
                logger.info(f"Location {i} source display_name: {s.get('display_name')}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
