"""
PDF downloader for academic papers with retry logic, session management, and browser automation using Playwright.
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
import re
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
import brotli

logger = logging.getLogger(__name__)


class PDFDownloader:
    """Downloads PDF files from academic paper sources using Playwright for complex sites."""
    
    def __init__(self, output_dir: str = "pdfs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.session = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(user_agent=self.headers['User-Agent'])
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def _is_valid_pdf(self, file_path: Path) -> bool:
        """Validate if a file is a valid PDF."""
        try:
            if not file_path.exists():
                return False
            
            file_size = file_path.stat().st_size
            
            # PDF must be at least 1KB
            if file_size < 1024:
                logger.debug(f"PDF too small: {file_size} bytes")
                return False
            
            # PDF must be less than 500MB
            if file_size > 500 * 1024 * 1024:
                logger.debug(f"PDF too large: {file_size} bytes")
                return False
            
            # Check for PDF magic bytes
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    logger.debug(f"Invalid PDF header: {header}")
                    return False
                
                # Check for EOF marker at end
                f.seek(-1024, 2)
                footer = f.read()
                if b'%%EOF' not in footer:
                    logger.debug("Missing %%EOF marker")
                    return False
            
            return True
        except Exception as e:
            logger.debug(f"PDF validation error: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def download_pdf(self, pdf_url: str, paper_id: str) -> Optional[str]:
        if not pdf_url or not paper_id:
            logger.debug(f"Invalid PDF URL or paper_id for download")
            return None
        
        pdf_filename = self.output_dir / f"{paper_id}.pdf"
        
        if pdf_filename.exists():
            try:
                if self._is_valid_pdf(pdf_filename):
                    logger.debug(f"PDF already exists and is valid: {pdf_filename}")
                    return str(pdf_filename)
                else:
                    logger.warning(f"Existing PDF is invalid or corrupted, re-downloading...")
                    pdf_filename.unlink()
            except Exception as e:
                logger.warning(f"Error checking existing PDF: {e}")
                try:
                    pdf_filename.unlink()
                except:
                    pass
        
        try:
            logger.debug(f"Downloading PDF: {pdf_url}")
            
            download_headers = {
                **self.headers,
                'Accept': 'application/pdf,application/x-pdf,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.semanticscholar.org/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site'
            }
            
            if "ssrn.com" in pdf_url:
                pdf_url = pdf_url.replace("abstract=", "delivery=").split("&")[0] + "&partid=1"
            
            async with self.session.get(pdf_url, headers=download_headers, timeout=60) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    content_encoding = response.headers.get('content-encoding', '').lower()
                    logger.debug(f"Content-Type: {content_type}, Content-Encoding: {content_encoding}")
                    
                    try:
                        content = await response.read()
                        
                        # Decompress brotli if needed
                        if content_encoding == 'br' and not content.startswith(b'%PDF'):
                            try:
                                content = brotli.decompress(content)
                                logger.debug("Successfully decompressed brotli content")
                            except Exception as e:
                                logger.warning(f"Failed to decompress brotli content: {e}")
                    except Exception as e:
                        # If brotli decompression fails, try Playwright fallback
                        logger.warning(f"Error reading content: {e}")
                        if "brotli" in str(e).lower() or "br" in content_encoding:
                            logger.info(f"Falling back to Playwright for brotli content")
                            return await self._download_with_playwright(pdf_url, pdf_filename)
                        raise
                    
                    # Validate content
                    if content.startswith(b'%PDF'):
                        # Valid PDF header, continue with validation
                        pass
                    elif any(html_type in content_type for html_type in ['html', 'text/xml']):
                        # Content is HTML/XML, try to find redirect/frame
                        html_text = content.decode('utf-8', errors='ignore')
                        
                        refresh_match = re.search(r'content=["\']\d+;\s*url=([^"\'>]+)["\']', html_text, re.I)
                        frame_match = re.search(r'<(?:iframe|frame)\s+[^>]*src=["\']([^"\']+\.pdf[^"\']*)["\']', html_text, re.I)
                        ieee_frame = re.search(r'src=["\'](https://ieeexplore\.ieee\.org/[^"\']+)["\']', html_text, re.I)
                        
                        target_url = None
                        if frame_match:
                            target_url = frame_match.group(1)
                        elif ieee_frame:
                            target_url = ieee_frame.group(1)
                        elif refresh_match:
                            target_url = refresh_match.group(1)
                        
                        if target_url:
                            if not target_url.startswith('http'):
                                target_url = urljoin(pdf_url, target_url)
                            logger.info(f"Following redirect/frame to: {target_url}")
                            return await self.download_pdf(target_url, paper_id)

                        logger.warning(f"URL returned {content_type}, attempting Playwright fallback")
                        return await self._download_with_playwright(pdf_url, pdf_filename)
                    else:
                        # Not PDF, not HTML - check for other content types
                        preview = content[:1000].lower()
                        html_markers = [
                            b'<!doctype', b'<html', b'<head', b'<body', 
                            b'<meta', b'<title', b'<div', b'<script',
                            b'<style', b'<link', b'<?xml'
                        ]
                        if any(html_marker in preview for html_marker in html_markers):
                            logger.warning(f"Content is HTML/XML, trying Playwright fallback")
                            return await self._download_with_playwright(pdf_url, pdf_filename)
                        logger.warning(f"Downloaded file is not a valid PDF")
                        return None
                    
                    # Validate PDF file size and content
                    file_size_mb = len(content) / 1024 / 1024
                    if file_size_mb < 0.01:
                        logger.warning(f"File too small ({file_size_mb:.3f} MB), likely not valid")
                        return None
                    
                    if file_size_mb > 500:
                        logger.warning(f"File too large ({file_size_mb:.2f} MB), exceeds 500MB limit")
                        return None
                    
                    # Check for EOF marker (but don't fail if missing)
                    if b'%%EOF' not in content[-1024:]:
                        logger.debug(f"PDF may be incomplete (missing %%EOF marker)")
                    
                    # Write the PDF file
                    try:
                        pdf_filename.write_bytes(content)
                        
                        # Final validation
                        if not self._is_valid_pdf(pdf_filename):
                            logger.warning(f"Downloaded PDF failed validation, removing")
                            pdf_filename.unlink()
                            return None
                        
                        logger.info(f"Downloaded PDF: {pdf_filename.name} ({file_size_mb:.2f} MB)")
                        return str(pdf_filename)
                    except Exception as e:
                        logger.error(f"Failed to write PDF file: {e}")
                        try:
                            pdf_filename.unlink()
                        except:
                            pass
                        return None
                
                elif response.status == 403:
                    logger.warning(f"Download failed: HTTP 403 (Access Forbidden), trying Playwright fallback")
                    return await self._download_with_playwright(pdf_url, pdf_filename)
                elif response.status == 404:
                    logger.warning(f"PDF not found (404)")
                    return None
                else:
                    logger.warning(f"Download failed: HTTP {response.status}")
                    return None
        
        except asyncio.TimeoutError:
            logger.warning(f"Download timeout for: {pdf_url}")
            return None
        except Exception as e:
            logger.warning(f"Download error: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None

    async def _download_with_playwright(self, url: str, output_path: Path) -> Optional[str]:
        """Uses Playwright to navigate to paper page, find PDF button, and download."""
        page = await self.context.new_page()
        try:
            logger.info(f"Navigating to {url} with Playwright")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            await asyncio.sleep(3) 
            
            pdf_url_from_source = await self._extract_pdf_url_from_page(page, url)
            if pdf_url_from_source:
                logger.info(f"Found PDF URL in page source: {pdf_url_from_source}")
                try:
                    # Download using aiohttp since we have a direct URL
                    async with self.session.get(pdf_url_from_source, headers=self.headers, timeout=60) as response:
                        if response.status == 200:
                            content = await response.read()
                            if content.startswith(b'%PDF'):
                                output_path.write_bytes(content)
                                logger.info(f"Successfully downloaded PDF from extracted URL: {output_path}")
                                return str(output_path)
                except Exception as e:
                    logger.debug(f"Failed to download extracted PDF URL: {e}")
            
            if "ieeexplore.ieee.org" in url:
                pdf_selectors = [
                    ("a.stats-document-lh-action-pdf", 25000),
                    ("a[href*='stamp.jsp']", 25000),
                    ("a[href*='stampPDF']", 25000),
                    ("a[href*='arnumber']", 25000),
                    ("button:has-text('PDF')", 10000),
                    (".pdf-btn", 10000),
                ]
            elif "acm.org" in url or "dl.acm.org" in url:
                pdf_selectors = [
                    ("a.btn--download-pdf", 25000),
                    ("a[title*='PDF']", 25000),
                    ("a[href*='.pdf']", 25000),
                    ("button:has-text('PDF')", 10000),
                ]
            elif "arxiv.org" in url:
                # ArXiv needs special handling
                if "/abs/" in url:
                    pdf_url = url.replace("/abs/", "/pdf/") + ".pdf"
                    logger.info(f"ArXiv detected, using direct PDF URL: {pdf_url}")
                    await page.goto(pdf_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(1)
                    content = await page.pdf()
                    output_path.write_bytes(content)
                    logger.info(f"Successfully downloaded ArXiv PDF: {output_path}")
                    return str(output_path)
                pdf_selectors = [("a[href$='.pdf']", 15000)]
            elif "semanticscholar.org" in url:
                pdf_selectors = [
                    ("a[data-test-id='download-pdf']", 15000),
                    ("a:has-text('View PDF')", 15000),
                    ("button:has-text('View PDF')", 10000),
                ]
            else:
                pdf_selectors = [
                    ("a[href$='.pdf']", 15000),
                    ("a[href*='.pdf']", 15000),
                    ("button:has-text('PDF')", 10000),
                    ("a:has-text('Download')", 10000),
                    ("a:has-text('View PDF')", 10000),
                ]
            
            for selector, timeout in pdf_selectors:
                try:
                    logger.debug(f"Trying selector: {selector} with timeout {timeout}ms")
                    if await page.is_visible(selector, timeout=timeout):
                        logger.info(f"Found PDF element with selector: {selector}")
                        
                        try:
                            href = await page.get_attribute(selector, 'href', timeout=5000)
                            if href and '.pdf' in href:
                                if not href.startswith('http'):
                                    href = urljoin(url, href)
                                logger.info(f"Direct PDF link found: {href}")
                                
                                # Navigate to PDF URL
                                response = await page.goto(href, wait_until="domcontentloaded", timeout=30000)
                                if response and response.status == 200:
                                    # Check if we're at a PDF
                                    final_url = page.url
                                    if '.pdf' in final_url or 'application/pdf' in (await response.header_value('content-type') or ''):
                                        pdf_content = await page.pdf()
                                        output_path.write_bytes(pdf_content)
                                        logger.info(f"Successfully downloaded PDF via direct link: {output_path}")
                                        return str(output_path)
                        except Exception as e:
                            logger.debug(f"Failed to get href or navigate: {e}")
                        
                        try:
                            async with page.expect_download(timeout=30000) as download_info:
                                await page.click(selector, timeout=10000)
                            download = await download_info.value
                            await download.save_as(output_path)
                            
                            # Verify it's a valid PDF
                            if output_path.exists() and output_path.stat().st_size > 1000:
                                with open(output_path, 'rb') as f:
                                    if f.read(4) == b'%PDF':
                                        logger.info(f"Successfully downloaded PDF via Playwright: {output_path}")
                                        return str(output_path)
                            logger.warning(f"Downloaded file is not a valid PDF")
                            return None
                        except Exception as e:
                            logger.debug(f"Click or download failed for selector {selector}: {e}")
                            continue
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            logger.warning(f"All predefined selectors failed, searching for any PDF links")
            all_links = await page.query_selector_all("a")
            for link in all_links[:20]:  # Check first 20 links
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    if href and ('.pdf' in href.lower() or 'pdf' in text.lower()):
                        logger.info(f"Found potential PDF link: {href}")
                        if not href.startswith('http'):
                            href = urljoin(url, href)
                        
                        # Try to download this link
                        response = await page.goto(href, wait_until="domcontentloaded", timeout=20000)
                        if response and '.pdf' in page.url:
                            pdf_content = await page.pdf()
                            output_path.write_bytes(pdf_content)
                            logger.info(f"Successfully downloaded PDF from discovered link: {output_path}")
                            return str(output_path)
                except Exception as e:
                    logger.debug(f"Failed to process link: {e}")
                    continue
            
            logger.warning(f"No PDF link found on page: {url}")
            return None
            
        except Exception as e:
            logger.warning(f"Playwright download failed: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None
        finally:
            await page.close()
    
    async def _extract_pdf_url_from_page(self, page, base_url: str) -> Optional[str]:
        """Extract PDF URL from page source using various patterns."""
        try:
            content = await page.content()
            
            # Pattern 1: Direct PDF links in href
            pdf_link_patterns = [
                r'href=["\']([^"\']*\.pdf[^"\']*)["\']',
                r'data-url=["\']([^"\']*\.pdf[^"\']*)["\']',
                r'data-pdf-url=["\']([^"\']*\.pdf[^"\']*)["\']',
                r'"pdfUrl":\s*"([^"]+)"',
                r'"pdf":\s*"([^"]+)"',
            ]
            
            for pattern in pdf_link_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if match and not match.startswith('#') and not match.startswith('javascript:'):
                        if not match.startswith('http'):
                            match = urljoin(base_url, match)
                        # Verify it looks like a valid PDF URL
                        parsed = urlparse(match)
                        if parsed.scheme in ['http', 'https'] and ('.pdf' in parsed.path.lower() or 'pdf' in parsed.query.lower()):
                            return match
            
            return None
        except Exception as e:
            logger.debug(f"Failed to extract PDF URL from page: {e}")
            return None
    
    def get_pdf_path(self, paper_id: str) -> Optional[str]:
        pdf_path = self.output_dir / f"{paper_id}.pdf"
        if pdf_path.exists():
            return str(pdf_path)
        return None
