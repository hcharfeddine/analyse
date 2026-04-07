"""
Diagnostic script to check GROBID service status and debug PDF/affiliation issues.
"""

import asyncio
import aiohttp
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


async def check_grobid_service(url: str = "http://localhost:8070") -> bool:
    """Check if GROBID service is running and accessible."""
    logger.info("=" * 80)
    logger.info("GROBID SERVICE CHECK")
    logger.info("=" * 80)
    logger.info(f"\n1. Checking GROBID service at: {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/api/isalive", timeout=aiohttp.ClientTimeout(total=5), ssl=False) as response:
                if response.status == 200:
                    logger.info("   ✓ GROBID service is RUNNING and responsive")
                    return True
                else:
                    logger.error(f"   ✗ GROBID returned status {response.status}")
                    return False
    except asyncio.TimeoutError:
        logger.error("   ✗ GROBID service TIMEOUT - service not responding")
        logger.error("   → Make sure Docker container is running:")
        logger.error("     docker ps | grep grobid")
        return False
    except aiohttp.ClientConnRefusedError:
        logger.error("   ✗ GROBID service NOT ACCESSIBLE (connection refused)")
        logger.error("   → Start GROBID with:")
        logger.error("     docker run -d -p 8070:8070 grobid/grobid:latest")
        return False
    except Exception as e:
        logger.error(f"   ✗ Error checking GROBID: {e}")
        return False


async def check_pdf_files() -> int:
    """Check if PDFs were downloaded."""
    logger.info("\n2. Checking downloaded PDFs")
    logger.info("-" * 80)
    
    pdf_dir = Path("academic/pdfs")
    if not pdf_dir.exists():
        logger.error(f"   ✗ PDF directory does not exist: {pdf_dir}")
        return 0
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    logger.info(f"   Found {len(pdf_files)} PDF files in {pdf_dir}")
    
    if pdf_files:
        for pdf_file in pdf_files[:5]:  # Show first 5
            size_mb = pdf_file.stat().st_size / 1024 / 1024
            logger.info(f"     • {pdf_file.name} ({size_mb:.2f} MB)")
        if len(pdf_files) > 5:
            logger.info(f"     ... and {len(pdf_files) - 5} more files")
    else:
        logger.warning("   ⚠ NO PDF files found! PDFs were not downloaded.")
        logger.warning("   → Check if paper PDF URLs are valid")
        logger.warning("   → Check internet connection")
    
    return len(pdf_files)


async def test_grobid_with_sample_pdf(grobid_url: str = "http://localhost:8070"):
    """Test GROBID processing with a sample PDF."""
    logger.info("\n3. Testing GROBID PDF processing")
    logger.info("-" * 80)
    
    pdf_dir = Path("academic/pdfs")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning("   ⚠ No PDF files to test")
        return False
    
    # Use first PDF
    test_pdf = pdf_files[0]
    logger.info(f"   Testing with: {test_pdf.name}")
    
    try:
        with open(test_pdf, 'rb') as f:
            pdf_content = f.read()
        
        if not pdf_content.startswith(b'%PDF'):
            logger.error(f"   ✗ File is not a valid PDF (magic bytes check failed)")
            return False
        
        logger.info(f"   ✓ PDF is valid ({len(pdf_content) / 1024 / 1024:.2f} MB)")
        
        # Send to GROBID
        logger.info("   Sending PDF to GROBID...")
        
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field('input', pdf_content, filename=test_pdf.name, content_type='application/pdf')
            
            async with session.post(
                f"{grobid_url}/api/processFulltextDocument",
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=120),
                ssl=False
            ) as response:
                logger.info(f"   Response status: {response.status}")
                
                if response.status == 200:
                    tei_xml = await response.text()
                    logger.info(f"   ✓ GROBID processing successful ({len(tei_xml)} bytes TEI XML)")
                    
                    # Check for affiliations in XML
                    if 'affiliation' in tei_xml.lower():
                        logger.info("   ✓ Affiliations found in GROBID output")
                        return True
                    else:
                        logger.warning("   ⚠ No affiliations in GROBID output")
                        logger.warning("   → PDF might not contain affiliation information")
                        return False
                else:
                    error_text = await response.text()
                    logger.error(f"   ✗ GROBID processing failed: {error_text[:300]}")
                    return False
    
    except FileNotFoundError:
        logger.error(f"   ✗ PDF file not found: {test_pdf}")
        return False
    except Exception as e:
        logger.error(f"   ✗ Error testing GROBID: {e}")
        return False


async def main():
    """Run all diagnostic checks."""
    logger.info("\nACCADEMIC PAPER COLLECTION - GROBID DIAGNOSTICS")
    
    # Check GROBID service
    grobid_running = await check_grobid_service()
    
    # Check PDFs
    pdf_count = await check_pdf_files()
    
    # Test GROBID if available
    if grobid_running and pdf_count > 0:
        await test_grobid_with_sample_pdf()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY & RECOMMENDATIONS")
    logger.info("=" * 80)
    
    if not grobid_running:
        logger.info("❌ GROBID service is NOT running")
        logger.info("\n   To start GROBID:")
        logger.info("   $ docker run -d -p 8070:8070 grobid/grobid:latest")
        logger.info("\n   Or use the official Docker image:")
        logger.info("   $ docker run -d -p 8070:8070 grobid/grobid:0.8.0")
    else:
        logger.info("✓ GROBID service is running")
    
    if pdf_count == 0:
        logger.info("❌ No PDFs were downloaded")
        logger.info("\n   This could be because:")
        logger.info("   1. Paper PDF URLs are invalid or broken")
        logger.info("   2. Download was blocked by firewall/proxy")
        logger.info("   3. Server requires authentication headers")
        logger.info("\n   Check the full logs for Stage 4 & 5 (Google Scholar & SSRN)")
    else:
        logger.info(f"✓ {pdf_count} PDFs downloaded successfully")
    
    logger.info("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
