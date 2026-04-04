"""
GROBID-based affiliation extractor for academic papers.
"""

import logging
import asyncio
import os
from typing import Optional, List, Dict
from pathlib import Path
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from models import Paper

logger = logging.getLogger(__name__)


class GROBIDEnricher:
    """Extracts author affiliations from PDFs using GROBID service."""
    
    def __init__(self, grobid_url: str = "http://localhost:8070"):
        self.grobid_url = grobid_url
        self.session = None
        self.headers = {
            'User-Agent': 'Academic Research Tool/1.0'
        }
        self._service_available = None
        self._last_check_time = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def enrich_paper(self, paper: Paper, pdf_path: Optional[str] = None) -> Paper:
        """Enrich paper with affiliation data extracted from PDF."""
        if not pdf_path:
            logger.debug(f"No PDF path for: {paper.title[:60]}")
            return paper
        
        if paper.author_affiliations and paper.author_affiliations != "Affiliations not available":
            logger.debug(f"Affiliations already available for: {paper.title[:60]}")
            return paper
        
        try:
            logger.debug(f"Processing: {Path(pdf_path).name}")
            pdf_file = Path(pdf_path)
            if pdf_file.exists():
                file_size = pdf_file.stat().st_size / 1024 / 1024
                logger.info(f"PDF size: {file_size:.2f} MB")
            
            affiliations = await self._extract_affiliations_from_pdf_with_retry(pdf_path)
            
            if affiliations:
                paper.author_affiliations = affiliations
                logger.debug(f"Found affiliations: {affiliations[:100]}...")
            else:
                logger.debug(f"No affiliations extracted from PDF")
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
        return paper
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((asyncio.TimeoutError, aiohttp.ClientError))
    )
    async def _extract_affiliations_from_pdf_with_retry(self, pdf_path: str) -> Optional[str]:
        """Send PDF to GROBID service with retry logic."""
        return await self._extract_affiliations_from_pdf(pdf_path)
    
    async def _extract_affiliations_from_pdf(self, pdf_path: str) -> Optional[str]:
        """Send PDF to GROBID service and extract affiliations from response."""
        if not await self._check_grobid_service_cached():
            logger.warning(f"GROBID service not available at {self.grobid_url}")
            return None
        
        try:
            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                logger.warning(f"PDF file not found: {pdf_path}")
                return None
            
            with open(pdf_file, 'rb') as f:
                header = f.read(1024)
                if not header.startswith(b'%PDF'):
                    logger.debug(f"Skipping invalid PDF: {pdf_path}")
                    return None
                f.seek(0)
                pdf_content = f.read()
            
            logger.debug(f"Sending PDF to GROBID service...")
            
            form_data = aiohttp.FormData()
            form_data.add_field(
                'input',
                pdf_content,
                filename=pdf_file.name,
                content_type='application/pdf'
            )
            
            url = f"{self.grobid_url}/api/processFulltextDocument"
            
            try:
                async with self.session.post(
                    url,
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=180),
                    ssl=False
                ) as response:
                    logger.info(f"Response status: {response.status}")
                    
                    if response.status == 200:
                        tei_xml = await response.text()
                        logger.info(f"Received {len(tei_xml)} bytes of TEI XML")
                        
                        if logger.isEnabledFor(logging.DEBUG):
                            debug_dir = Path("debug")
                            if debug_dir.exists():
                                debug_file = debug_dir / f"last_grobid_response_{Path(pdf_path).stem}.xml"
                                debug_file.write_text(tei_xml, encoding='utf-8')
                                logger.debug(f"Saved debug XML to: {debug_file}")
                        
                        affiliations = self._parse_affiliations_from_tei(tei_xml)
                        return affiliations
                    elif response.status == 503:
                        logger.warning(f"GROBID service unavailable (503), will retry")
                        raise aiohttp.ClientError("Service unavailable")
                    elif response.status == 500:
                        error_text = await response.text()
                        logger.warning(f"GROBID processing error (500): {error_text[:200]}")
                        return None  # Don't retry on 500
                    else:
                        error_text = await response.text()
                        logger.warning(f"HTTP {response.status}: {error_text[:300]}")
                        return None
            except asyncio.TimeoutError:
                logger.warning(f"Processing timeout for: {pdf_path}, will retry")
                raise  # Let retry decorator handle it
        
        except Exception as e:
            logger.error(f"Error communicating with GROBID: {e}")
            raise
    
    def _parse_affiliations_from_tei(self, tei_xml: str) -> Optional[str]:
        """Parse TEI XML from GROBID to extract author-affiliation mappings."""
        try:
            from lxml import etree
            import re
            
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            root = etree.fromstring(tei_xml.encode('utf-8'), parser=parser)
            
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            affiliations = []
            
            def extract_full_text(elem):
                return ' '.join([t.strip() for t in elem.xpath('.//text()', namespaces=ns) if t.strip()])

            source_affs = root.xpath('//tei:sourceDesc//tei:affiliation', namespaces=ns)
            for aff in source_affs:
                txt = extract_full_text(aff)
                if txt and len(txt) > 2 and txt not in affiliations:
                    affiliations.append(txt)

            authors = root.xpath('//tei:author | //tei:editor', namespaces=ns)
            for author in authors:
                for direct in author.xpath('.//tei:affiliation', namespaces=ns):
                    txt = extract_full_text(direct)
                    if txt and len(txt) > 2 and txt not in affiliations:
                        affiliations.append(txt)
                
                for addr in author.xpath('.//tei:address', namespaces=ns):
                    txt = extract_full_text(addr)
                    if txt and len(txt) > 5 and txt not in affiliations:
                        affiliations.append(txt)

            if not affiliations:
                global_elements = root.xpath('//tei:teiHeader//tei:orgName | //tei:teiHeader//tei:address', namespaces=ns)
                for elem in global_elements:
                    txt = extract_full_text(elem)
                    if txt and len(txt) > 4 and txt not in affiliations:
                        affiliations.append(txt)
            
            affiliations = list(dict.fromkeys(affiliations))
            affiliations = [aff.strip() for aff in affiliations if aff.strip() and len(aff) > 2]
            
            cleaned_affs = []
            institutional_keywords = [
                'univ', 'inst', 'coll', 'lab', 'research', 'center', 'school', 'faculty',
                'inc', 'corp', 'ltd', 'gmbh', 'hospital', 'academy', 'rd', 'dept', 'org'
            ]
            
            for aff in affiliations:
                clean = re.sub(r'^\s*[0-9\*\†\§\dagger\ddagger\s,;:]+\s*', '', aff)
                clean = re.sub(r'\s*[0-9\*\†\§\dagger\ddagger\s,;:]+\s*$', '', clean).strip()
                
                if any(k in clean.lower() for k in institutional_keywords) or '@' in clean or len(clean) > 15:
                    if clean not in cleaned_affs:
                        cleaned_affs.append(clean)

            affiliations = cleaned_affs if cleaned_affs else affiliations
            
            if affiliations:
                affiliations.sort(key=len, reverse=True)
                final_affs = []
                for aff in affiliations:
                    is_substring = False
                    for other in affiliations:
                        if aff != other and aff.lower() in other.lower():
                            is_substring = True
                            break
                    if not is_substring:
                        final_affs.append(aff)
                
                return '; '.join(final_affs[:10])
            
            return None
        
        except ImportError:
            logger.error("lxml library not found")
            return None
        except Exception as e:
            logger.error(f"Error parsing TEI XML: {e}")
            return None
    
    async def _check_grobid_service_cached(self) -> bool:
        """Check if GROBID service is available with caching."""
        import time
        current_time = time.time()
        
        # Cache service availability for 30 seconds
        if self._service_available is not None and (current_time - self._last_check_time) < 30:
            return self._service_available
        
        self._service_available = await self._check_grobid_service()
        self._last_check_time = current_time
        return self._service_available
    
    async def _check_grobid_service(self) -> bool:
        """Check if GROBID service is available."""
        try:
            url = f"{self.grobid_url}/api/isalive"
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=5),
                ssl=False
            ) as response:
                is_alive = response.status == 200
                if is_alive:
                    logger.info("GROBID service is available")
                return is_alive
        except Exception as e:
            logger.warning(f"GROBID service check failed: {e}")
            return False
