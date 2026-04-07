#!/usr/bin/env python3
"""
Test GROBID extraction on a single PDF to debug affiliation parsing.
"""

import asyncio
import logging
from pathlib import Path
from enrichers.grobid_enricher import GROBIDEnricher

# Setup logging to see debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_grobid():
    """Test GROBID with the first PDF in the pdfs directory."""
    
    pdfs_dir = Path("schol/pdfs")
    
    # Find first PDF
    pdf_files = list(pdfs_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.error(f"No PDF files found in {pdfs_dir}")
        logger.error("Make sure PDFs are downloaded first by running the main scraper")
        return
    
    pdf_path = pdf_files[0]
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing GROBID with: {pdf_path.name}")
    logger.info(f"File size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")
    logger.info(f"{'='*80}\n")
    
    async with GROBIDEnricher() as enricher:
        affiliations = await enricher._extract_affiliations_from_pdf(str(pdf_path))
        
        logger.info(f"\n{'='*80}")
        logger.info(f"RESULT: {affiliations}")
        logger.info(f"{'='*80}\n")
        
        if not affiliations:
            logger.error("GROBID did not extract any affiliations!")
            logger.error("This means either:")
            logger.error("1. GROBID is not running (check: docker ps | grep grobid)")
            logger.error("2. The PDF is corrupted or not readable")
            logger.error("3. The affiliation data is stored differently than expected")
            
            # Save the raw TEI XML for inspection
            from lxml import etree
            pdf_file = Path(pdf_path)
            
            with open(pdf_file, 'rb') as f:
                pdf_content = f.read()
            
            # Create form data
            import aiohttp
            form_data = aiohttp.FormData()
            form_data.add_field(
                'input',
                pdf_content,
                filename=pdf_file.name,
                content_type='application/pdf'
            )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8070/api/processFulltextDocument",
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=120),
                    ssl=False
                ) as response:
                    if response.status == 200:
                        tei_xml = await response.text()
                        
                        # Save to file for inspection
                        debug_xml = Path("debug_grobid_output.xml")
                        debug_xml.write_text(tei_xml)
                        logger.error(f"\nRaw TEI XML saved to: {debug_xml}")
                        logger.error("Use a text editor to inspect what's in the XML")
                    else:
                        logger.error(f"GROBID returned status {response.status}")

if __name__ == "__main__":
    asyncio.run(test_grobid())
