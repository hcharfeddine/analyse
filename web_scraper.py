import asyncio
import aiohttp
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
import re
import json
import time
import random
import logging

logger = logging.getLogger(__name__)

from playwright.async_api import async_playwright, BrowserContext, Page, Browser

from models import Paper, Author
from exceptions import APIException
from config import config


class BrowserPool:
    """
    Pool of browser contexts for parallel scraping.
    """
    
    def __init__(self, num_contexts: int = 4):
        self.num_contexts = num_contexts
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.contexts: List[BrowserContext] = []
        self.context_locks: List[asyncio.Lock] = []
        self._next_context = 0
        self._counter_lock = asyncio.Lock()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        ]
    
    async def initialize(self):
        """Initialize browser and create multiple contexts"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-background-networking',
                    '--disable-sync',
                    '--disable-translate',
                    '--metrics-recording-only',
                    '--no-first-run',
                ]
            )
            
            # Create multiple contexts for parallel scraping
            for i in range(self.num_contexts):
                context = await self.browser.new_context(
                    user_agent=self.user_agents[i % len(self.user_agents)],
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True,
                    bypass_csp=True,
                )
                await context.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", lambda route: route.abort())
                
                self.contexts.append(context)
                self.context_locks.append(asyncio.Lock())
            
            logger.info(f"Initialized {self.num_contexts} browser contexts")
            
        except Exception as e:
            logger.warning(f"Could not initialize browser pool: {e}")
            self.browser = None
    
    async def get_context(self) -> tuple[int, BrowserContext, asyncio.Lock]:
        """
        Get an available context from the pool using round-robin allocation.
        """
        if not self.contexts:
            return -1, None, None
        
        async with self._counter_lock:
            start_idx = self._next_context
            self._next_context = (self._next_context + 1) % self.num_contexts
        
        # Try to get the assigned context, or wait for it
        lock = self.context_locks[start_idx]
        await lock.acquire()
        return start_idx, self.contexts[start_idx], lock
    
    def release_context(self, index: int, lock: asyncio.Lock):
        """Release a context back to the pool"""
        if lock and lock.locked():
            lock.release()
    
    async def close(self):
        """Close all contexts and browser"""
        for context in self.contexts:
            try:
                await context.close()
            except:
                pass
        
        if self.browser:
            try:
                await self.browser.close()
            except:
                pass
        
        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass


class SemanticScholarScraper:
    """Scrape structured metadata from Semantic Scholar paper detail pages"""
    
    BASE_URL = "https://www.semanticscholar.org/paper"
    AUTHOR_URL = "https://www.semanticscholar.org/author"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        self.request_delay = config.TOPIC_SCRAPE_MIN_DELAY
        
        self.session = None
        self.connector = None
        self.browser_pool: Optional[BrowserPool] = None
        
        # Track timing per context to avoid rate limiting
        self.context_last_request: Dict[int, float] = {}
    
    async def __aenter__(self):
        """Context manager entry - initialize session and browser pool"""
        self.connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,  # Increased from 20 to 30
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=aiohttp.ClientTimeout(total=20)  # Reduced from 30 to 20
        )
        
        self.browser_pool = BrowserPool(num_contexts=config.NUM_BROWSER_CONTEXTS)
        await self.browser_pool.initialize()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup"""
        if self.session:
            await self.session.close()
        
        if self.browser_pool:
            await self.browser_pool.close()
    
    async def scrape_paper_detail(self, paper_id: str) -> Optional[Dict]:
        """
        Scrape paper detail page using browser pool for parallel execution.
        """
        if not self.session:
            raise RuntimeError("Scraper not initialized. Use 'async with SemanticScholarScraper() as scraper:'")
        
        url = f"{self.BASE_URL}/{paper_id}"
        
        max_retries = config.SEMANTIC_SCHOLAR_MAX_RETRIES
        
        for attempt in range(max_retries):
            try:
                html = await self._fetch_with_browser_pool(url, attempt)
                
                if not html:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(config.SEMANTIC_SCHOLAR_RETRY_DELAY * (attempt + 1))
                        continue
                    else:
                        return None
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract metadata from structured data (JSON-LD)
                metadata = self._extract_json_ld(soup)
                
                # Extract authors with IDs from DOM
                authors = self._extract_authors_with_ids(soup)
                
                topics = self._extract_topics(soup)
                
                # Only retry on actual failures
                if not topics and attempt < max_retries - 1 and not metadata:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                
                return {
                    'paper_id': paper_id,
                    'metadata': metadata,
                    'authors': authors,
                    'topics': topics,
                    'citations': self._extract_citation_count(soup),
                    'references': self._extract_reference_count(soup)
                }
            
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(config.SEMANTIC_SCHOLAR_RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    return None
        
        return None
    
    async def _fetch_with_browser_pool(self, url: str, attempt: int = 0) -> Optional[str]:
        """
        Fetch using browser pool for true parallel execution.
        Each request gets its own context from the pool.
        Optimized timing and waits.
        """
        if not self.browser_pool or not self.browser_pool.contexts:
            return await self._fetch_with_aiohttp(url)
        
        context_idx, context, lock = await self.browser_pool.get_context()
        
        if context is None:
            return await self._fetch_with_aiohttp(url)
        
        page = None
        try:
            current_time = time.time()
            last_request = self.context_last_request.get(context_idx, 0)
            time_since_last = current_time - last_request
            
            if time_since_last < self.request_delay:
                await asyncio.sleep(self.request_delay - time_since_last)
            
            page = await context.new_page()
            
            # Navigate with timeout
            await page.goto(url, wait_until='domcontentloaded', timeout=config.TOPIC_SCRAPE_PAGE_TIMEOUT)
            
            topic_wait_time = config.TOPIC_SCRAPE_WAIT_FOR_TOPICS + (attempt * 1000)
            
            try:
                await page.wait_for_selector(
                    'a[href*="/topic/"], [data-test-id="topic-link"], .cl-paper-topics a',
                    timeout=topic_wait_time
                )
            except:
                try:
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
                    await asyncio.sleep(0.3)  # Reduced from 1.0
                except:
                    pass
            
            await asyncio.sleep(0.2 + (attempt * 0.2))  # Reduced from 0.5 + 0.5
            
            html = await page.content()
            self.context_last_request[context_idx] = time.time()
            
            return html
        
        except Exception as e:
            return await self._fetch_with_aiohttp(url)
        
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass
            self.browser_pool.release_context(context_idx, lock)
    
    async def _fetch_with_aiohttp(self, url: str) -> Optional[str]:
        """Fallback: Fetch with aiohttp (HTTP only, won't get Topics)"""
        try:
            async with self.session.get(url, headers=self.headers) as response:
                if response.status in (200, 202):
                    return await response.text()
                else:
                    return None
        except Exception as e:
            return None
    
    def _extract_topics(self, soup: BeautifulSoup) -> List[str]:
        """Extract topics from the page"""
        topics = []
        
        try:
            topic_links = []
            
            topic_links.extend(soup.find_all('a', href=re.compile(r'/topic/')))
            topic_links.extend(soup.find_all('a', {'data-test-id': 'topic-link'}))
            
            topics_section = soup.find('div', {'data-test-id': 'topics'}) or soup.find('section', class_=re.compile(r'topic', re.I))
            if topics_section:
                topic_links.extend(topics_section.find_all('a'))
            
            seen_topics = set()
            for link in topic_links:
                topic_text = link.get_text(strip=True)
                topic_text = re.sub(r'$$opens in a new tab$$\s*', '', topic_text, flags=re.IGNORECASE).strip()
                topic_text = re.sub(r'\s+', ' ', topic_text).strip()
                
                if 2 <= len(topic_text) <= 100 and topic_text.lower() not in seen_topics:
                    seen_topics.add(topic_text.lower())
                    topics.append(topic_text)
        
        except Exception as e:
            pass
        
        return topics
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> Dict:
        """Extract JSON-LD structured data"""
        try:
            script_tag = soup.find('script', {'type': 'application/ld+json'})
            if script_tag:
                return json.loads(script_tag.string)
        except Exception as e:
            pass
        
        return {}
    
    def _extract_authors_with_ids(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract authors with their IDs"""
        authors = []
        
        try:
            author_links = soup.find_all('a', {'data-test-id': 'author-link'})
            
            for link in author_links:
                href = link.get('href', '')
                name = link.get_text(strip=True)
                
                if '/author/' in href:
                    author_id = href.split('/author/')[1].split('/')[0]
                    
                    authors.append({
                        'author_id': author_id,
                        'name': name,
                        'affiliations': []
                    })
        
        except Exception as e:
            pass
        
        return authors
    
    def _extract_citation_count(self, soup: BeautifulSoup) -> int:
        """Extract citation count"""
        try:
            citations_elem = soup.find('span', {'data-test-id': 'citation-count'})
            if citations_elem:
                text = citations_elem.get_text(strip=True)
                return int(text.split()[0].replace(',', ''))
        except Exception as e:
            pass
        
        return 0
    
    def _extract_reference_count(self, soup: BeautifulSoup) -> int:
        """Extract reference count"""
        try:
            refs_elem = soup.find('span', {'data-test-id': 'reference-count'})
            if refs_elem:
                text = refs_elem.get_text(strip=True)
                return int(text.split()[0].replace(',', ''))
        except Exception as e:
            pass
        
        return 0
    
    async def fetch_author_citations_browser(
        self, 
        author_ids: List[str],
        progress_callback=None
    ) -> Dict[str, Dict]:
        """
        Fetch author metadata (citations, affiliations) using parallel browsers.
        Returns Dict mapping author_id to a dict of {citations, affiliations}.
        """
        if not self.browser_pool or not self.browser_pool.contexts:
            logger.warning("BrowserPool not available for author fetching")
            return {}
        
        results: Dict[str, Dict] = {}
        
        if not author_ids:
            return results
        
        semaphore = asyncio.Semaphore(config.NUM_BROWSER_CONTEXTS)
        completed = 0
        successful = 0
        total = len(author_ids)
        start_time = time.time()
        
        async def fetch_one(author_id: str) -> tuple:
            nonlocal completed, successful
            async with semaphore:
                author_data = await self._scrape_author_citations(author_id)
                
                completed += 1
                if author_data:
                    successful += 1
                
                # Progress every 50 authors instead of 25 to reduce I/O and CPU
                if completed % 50 == 0 or completed == total:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta = (total - completed) / rate if rate > 0 else 0
                    logger.info(f"Authors: {completed}/{total} ({successful} successful) - {rate:.1f}/sec")
                
                return author_id, author_data
        
        # Fetch all in parallel
        tasks = [fetch_one(aid) for aid in author_ids]
        fetched = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in fetched:
            if isinstance(result, tuple):
                author_id, data = result
                results[author_id] = data
        
        # Retry failed ones once
        failed = [aid for aid, data in results.items() if not data]
        if failed and len(failed) < len(author_ids) * 0.5:
            logger.info(f"Retrying {len(failed)} failed authors...")
            await asyncio.sleep(2.0)
            
            retry_tasks = [fetch_one(aid) for aid in failed]
            retry_results = await asyncio.gather(*retry_tasks, return_exceptions=True)
            
            for result in retry_results:
                if isinstance(result, tuple):
                    author_id, data = result
                    if data:
                        results[author_id] = data
        
        final_successful = sum(1 for v in results.values() if v)
        logger.info(f"Browser fetch complete: {final_successful}/{total} authors")
        
        return results
    
    async def _scrape_author_citations(self, author_id: str) -> Optional[Dict]:
        """Scrape citation count and affiliations from author page"""
        if not author_id:
            return None
        
        url = f"{self.AUTHOR_URL}/{author_id}"
        
        context_idx, context, lock = await self.browser_pool.get_context()
        
        if context is None:
            return None
        
        page = None
        try:
            current_time = time.time()
            last_request = self.context_last_request.get(context_idx, 0)
            time_since_last = current_time - last_request
            
            min_delay = 0.2
            if time_since_last < min_delay:
                await asyncio.sleep(min_delay - time_since_last)
            
            page = await context.new_page()
            
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            
            # Wait for any of the common stats or affiliation selectors
            try:
                await page.wait_for_selector(
                    '[data-test-id="author-citations"], .cl-author-summary__stats, .cl-author-summary__affiliations',
                    timeout=3000
                )
            except:
                # If wait fails, we still try to scrape what's loaded
                await asyncio.sleep(1.0)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            citation_count = None
            affiliations = []
            
            # 1. Extract Citation Count (Improved Patterns)
            try:
                # Modern Semantic Scholar selector
                cite_elem = soup.select_one('[data-test-id="author-citations"], .cl-author-summary__stats-item:has(span:-soup-contains("Citations"))')
                if cite_elem:
                    numbers = re.findall(r'[\d,]+', cite_elem.get_text())
                    if numbers:
                        citation_count = int(numbers[0].replace(',', ''))
                
                # Fallback patterns from existing code
                if not citation_count:
                    stats = soup.find_all(['span', 'div'], string=re.compile(r'citations?', re.I))
                    for stat in stats:
                        parent = stat.parent
                        if parent:
                            nums = re.findall(r'[\d,]+', parent.get_text())
                            if nums:
                                citation_count = int(nums[0].replace(',', ''))
                                break
            except:
                pass

            # 2. Extract Affiliations (Enhanced Logic)
            try:
                # Modern Semantic Scholar selectors for current HTML structure
                aff_selectors = [
                    '[data-test-id="author-affiliation"]',
                    '.cl-author-summary__affiliations',
                    '.cl-author-summary__affiliation',
                    '.cl-author-summary__header-meta-item',
                    '.cl-author-summary__bio',
                    '[data-test-id="author-bio"]',
                    '.author-info',
                    '.author-profile-section',
                    'span[class*="affiliation"]',
                ]
                for selector in aff_selectors:
                    elements = soup.select(selector)
                    for elem in elements:
                        text = elem.get_text(strip=True)
                        if text and len(text) > 3:
                            # Split multiple institutions if present
                            for part in re.split(r'[,;|]', text):
                                part = part.strip()
                                if part and len(part) > 3 and part.lower() not in ['n/a', 'none', 'independent', 'unknown']:
                                    if part not in affiliations:
                                        affiliations.append(part)
                
                bio = soup.select_one('[data-test-id="author-bio"], .cl-author-summary__bio, [class*="biography"], [class*="bio"]')
                if bio:
                    bio_text = bio.get_text()
                    # Look for institutional mentions with improved patterns
                    patterns = [
                        # Match "at [Institution]" or "with [Institution]"
                        r'(?:at|with|of|from|in|research|professor|researcher|working|faculty member)\s+([A-Z][a-zA-Z\s&,\-]*(?:University|Institute|Institute of|College|College of|School|School of|Center|Centre|Lab|Laboratory|Research|Group|Department|Division|Corporation|Company|Inc|Ltd|Hospital|Clinic|Academy)(?:\s+[A-Z][a-zA-Z\s,\-]*)?)',
                        # Match standalone institution names in caps
                        r'([A-Z][a-zA-Z\s&,\-]+(?:University|Institute|College|School|Center|Lab|Research))',
                        # Email-based affiliations
                        r'@([a-zA-Z0-9\.\-]+)',
                    ]
                    for pattern in patterns:
                        found = re.findall(pattern, bio_text)
                        for aff in found:
                            if aff and len(aff) > 3 and aff.lower() not in ['n/a', 'none', 'unknown']:
                                if aff not in affiliations:
                                    affiliations.append(aff)
                
                structured_affs = soup.select('[class*="affiliation"], [class*="institution"], [class*="company"]')
                for elem in structured_affs:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 3 and text not in affiliations:
                        affiliations.append(text)
            except:
                pass
            
            self.context_last_request[context_idx] = time.time()
            
            # Always return a dict if we got anything useful
            if citation_count is not None or affiliations:
                return {
                    'citations': citation_count,
                    'affiliations': affiliations
                }
            return None
        
        except Exception as e:
            return None
        
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass
            self.browser_pool.release_context(context_idx, lock)


class UniversalMetadataExtractor:
    """
    Extract standardized metadata from any academic paper source.
    Focuses on IDs, structured fields, and essential data.
    """
    
    @staticmethod
    def extract_author_ids(authors_data: List[Dict]) -> List[Author]:
        authors = []
        for author_data in authors_data:
            author = Author(
                author_id=author_data.get('author_id') or author_data.get('orcid'),
                name=author_data.get('name', ''),
                affiliations=author_data.get('affiliations', [])
            )
            authors.append(author)
        
        return authors
    
    @staticmethod
    def normalize_paper_id(paper_id: str, source: str) -> str:
        if source == 'Semantic Scholar':
            return f"ss-{paper_id}"
        elif source == 'CrossRef':
            return f"doi-{paper_id}"
        elif source == 'arXiv':
            return f"arxiv-{paper_id}"
        
        return paper_id
