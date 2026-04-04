"""
API clients for academic paper data sources.
"""

import asyncio
import aiohttp
import time
import random
import logging
from typing import List, Optional, Dict, Set
from abc import ABC, abstractmethod

from models import Paper, Author, CitationPaper
from exceptions import APIException
from config import config

logger = logging.getLogger(__name__)


class GlobalRateLimiter:
    def __init__(self, min_delay: float = 2.0):
        self._lock = asyncio.Lock()
        self._last_request_time = 0.0
        self._min_delay = min_delay
        self._consecutive_429s = 0
    
    async def acquire(self) -> int:
        async with self._lock:
            now = time.time()
            effective_delay = self._min_delay + (self._consecutive_429s * 2.0)
            wait_time = effective_delay - (now - self._last_request_time)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request_time = time.time()
            return 0
    
    def report_429(self):
        self._consecutive_429s = min(self._consecutive_429s + 1, 10)
    
    def report_success(self):
        if self._consecutive_429s > 0:
            self._consecutive_429s = max(self._consecutive_429s - 0.5, 0)
    
    def reset_backoff(self):
        self._consecutive_429s = 0


_global_rate_limiter = GlobalRateLimiter(min_delay=1.0)


class AuthorCitationCache:
    def __init__(self):
        self._cache: Dict[str, Optional[int]] = {}
        self._pending: Set[str] = set()
        self._failed: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, author_id: str) -> Optional[int]:
        async with self._lock:
            return self._cache.get(author_id)
    
    async def set(self, author_id: str, citation_count: Optional[int]):
        async with self._lock:
            self._cache[author_id] = citation_count
            self._pending.discard(author_id)
    
    async def mark_pending(self, author_id: str) -> bool:
        async with self._lock:
            if author_id in self._cache or author_id in self._pending:
                return False
            self._pending.add(author_id)
            return True


_author_citation_cache = AuthorCitationCache()


class BaseAPIClient(ABC):
    def __init__(self):
        self.session = None
        self.headers = {'User-Agent': 'Academic Research Tool/1.0'}
    
    async def __aenter__(self):
        # Limit connections per session to avoid overwhelming APIs
        connector = aiohttp.TCPConnector(limit=config.MAX_CONCURRENT_REQUESTS)
        self.session = aiohttp.ClientSession(connector=connector, headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def search(self, keyword: str, year: int, limit: int) -> List[Paper]:
        pass
    
    async def _make_request(self, url: str, params: dict, timeout: Optional[int] = None):
        timeout = timeout or config.REQUEST_TIMEOUT
        if not self.session:
            raise APIException("Session not initialized.")
        
        max_attempts = 10 # Increased retries
        for attempt in range(1, max_attempts + 1):
            await _global_rate_limiter.acquire()
            try:
                async with self.session.get(url, params=params, timeout=timeout) as response:
                    if response.status == 429:
                        _global_rate_limiter.report_429()
                        wait = (attempt * 5) + random.uniform(0, 5) # Progressive backoff
                        logger.warning(f"Rate limited (429). Waiting {wait:.2f}s (Attempt {attempt})...")
                        await asyncio.sleep(wait)
                        continue
                        
                    if response.status == 404:
                        _global_rate_limiter.report_success()
                        logger.warning(f"Resource not found (404): {url}")
                        return {}
                        
                    if response.status >= 500:
                        wait = (attempt * 2) + random.uniform(0, 2)
                        logger.warning(f"Server error ({response.status}). Retrying in {wait:.2f}s...")
                        await asyncio.sleep(wait)
                        continue

                    response.raise_for_status()
                    _global_rate_limiter.report_success()
                    return await response.json()
            except aiohttp.ClientConnectorError as e:
                logger.error(f"Connection error: {e}")
                if attempt == max_attempts:
                    raise APIException(f"Connection failed after {max_attempts} attempts: {e}")
                await asyncio.sleep(attempt + random.uniform(0, 2))
            except asyncio.TimeoutError:
                logger.warning(f"Request timeout on attempt {attempt}")
                if attempt == max_attempts:
                    raise APIException(f"Request timed out after {max_attempts} attempts")
                await asyncio.sleep(attempt)
            except Exception as e:
                if attempt == max_attempts:
                    raise APIException(f"API request failed: {e}")
                wait = attempt + random.uniform(0, 2)
                await asyncio.sleep(wait)
        raise APIException("Failed to get response")


class OpenAlexClient(BaseAPIClient):
    BASE_URL = "https://api.openalex.org/works"
    
    async def _get_author_citation_count(self, author_id: str) -> int:
        """Fetch total citation count for an author."""
        if not author_id:
            return 0
            
        cache = get_author_citation_cache()
        cached_count = await cache.get(author_id)
        if cached_count is not None:
            return cached_count
            
        if not await cache.mark_pending(author_id):
            return 0
            
        try:
            url = f"https://api.openalex.org/authors/{author_id}"
            params = {}
            if config.CORE_API_KEY:
                params['api_key'] = config.CORE_API_KEY
            if config.OPENALEX_MAILTO:
                params['mailto'] = config.OPENALEX_MAILTO
            data = await self._make_request(url, params)
            count = data.get('cited_by_count', 0)
            await cache.set(author_id, count)
            return count
        except Exception as e:
            logger.error(f"Error fetching author citations for {author_id}: {e}")
            await cache.set(author_id, 0)
            return 0

    async def search(self, keyword: str, year: int, limit: int) -> List[Paper]:
        all_papers = []
        page_count = 0
        try:
            cursor = "*"
            per_page = 200 # Max per page for cursor is 200
            
            while cursor and len(all_papers) < limit:
                params = {
                    'filter': f'publication_year:{year}',
                    'per_page': per_page, # Always request full page for stability
                    'cursor': cursor
                }
                if config.CORE_API_KEY:
                    params['api_key'] = config.CORE_API_KEY
                if config.OPENALEX_MAILTO:
                    params['mailto'] = config.OPENALEX_MAILTO
                if keyword and keyword != "*":
                    params['search'] = keyword
                
                data = await self._make_request(self.BASE_URL, params)
                results = data.get('results', [])
                page_count += 1
                
                if not results:
                    logger.info(f"No more results for year {year} after {page_count} pages, total papers: {len(all_papers)}")
                    break
                    
                # Process papers one by one or in small batches to avoid 429
                parsed_results = []
                # Use a small semaphore to limit concurrency for parsing (which includes author lookups)
                semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_AUTHOR_FETCHES)
                
                async def sem_parse(item):
                    async with semaphore:
                        return await self._parse_paper_async(item)
                
                tasks = [sem_parse(item) for item in results]
                parsed_results = await asyncio.gather(*tasks)
                
                for paper in parsed_results:
                    if paper:
                        all_papers.append(paper)
                        if len(all_papers) >= limit:
                            break
                
                cursor = data.get('meta', {}).get('next_cursor')
                if not cursor:
                      break
                  
                  # Minimal sleep between pages (OpenAlex has no rate limits)
                await asyncio.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"OpenAlex search error: {e}")
        return all_papers[:limit]
        
    async def _parse_paper_async(self, item: dict) -> Optional[Paper]:
        try:
            # Extract basic paper metadata
            paper_id = item.get('id', '').split('/')[-1] if item.get('id') else None
            title = item.get('display_name', 'N/A')
            year = item.get('publication_year', 0)
            doi = item.get('doi', '').replace('https://doi.org/', '') if item.get('doi') else 'DOI not available'
            
            # Extract authors and prepare citation fetch tasks
            authorships = item.get('authorships', [])
            author_tasks = []
            author_base_data = []
            
            # Collect citation counts - prefer data from work response, fallback to API if enabled
            citation_counts = []
            
            for m in authorships:
                author_data = m.get('author', {})
                institutions = m.get('institutions', []) or []
                raw_id = author_data.get('id')
                author_id = str(raw_id).split('/')[-1] if raw_id else ""
                
                # OPTIMIZED: Extract citation count directly from work response
                # OpenAlex includes cited_by_count in the author object within authorships
                citation_count = author_data.get('cited_by_count', 0) or 0
                
                # Store citation count directly without API call (much faster!)
                citation_counts.append(citation_count)
                
                # Optional: Fetch full author metrics from API if enabled and citation_count is 0
                if citation_count == 0 and config.FETCH_AUTHOR_CITATIONS and author_id:
                    author_tasks.append((len(author_base_data), self._get_author_citation_count(author_id)))
                
                author_base_data.append({
                    'author_id': author_id if author_id else None,
                    'affiliations': [inst.get('display_name') for inst in institutions if inst and inst.get('display_name')],
                    'ror_ids': [str(inst.get('ror')).split('/')[-1] for inst in institutions if inst and inst.get('ror')],
                    'countries': [inst.get('country_code') for inst in institutions if inst and inst.get('country_code')],
                    'organization_types': [inst.get('type') for inst in institutions if inst and inst.get('type')]
                })
            
            # Fetch missing author citations from API only if enabled (time-consuming)
            if author_tasks and config.FETCH_AUTHOR_CITATIONS:
                for idx, task in author_tasks:
                    try:
                        count = await asyncio.wait_for(task, timeout=config.FETCH_AUTHOR_CITATIONS_TIMEOUT)
                        if count > 0:
                            citation_counts[idx] = count
                    except asyncio.TimeoutError:
                        logger.warning(f"Author citation fetch timed out")
                        pass
            
            authors = []
            for i, base in enumerate(author_base_data):
                authors.append(Author(
                    author_id=base['author_id'],
                    affiliations=base['affiliations'],
                    ror_ids=base['ror_ids'],
                    countries=base['countries'],
                    organization_types=base['organization_types'],
                    citation_count=citation_counts[i]
                ))
            
            # Simple abstract reconstruction
            abstract_text = "Abstract not available"
            inverted_index = item.get('abstract_inverted_index')
            if inverted_index:
                word_positions = []
                for word, pos_list in inverted_index.items():
                    for pos in pos_list:
                        word_positions.append((pos, word))
                word_positions.sort()
                abstract_text = " ".join([word for pos, word in word_positions])
            
            cited_by_count = item.get('cited_by_count') or 0
            
            primary_loc = item.get('primary_location') or {}
            source = primary_loc.get('source') or {}
            
            publisher = item.get('publisher') or source.get('publisher') or source.get('host_organization_name') or 'Unknown Publisher'
            journal_name = source.get('display_name', 'Journal not specified')
            venue = journal_name
            pub_type = item.get('type', 'Unknown')
            
            field_of_study = 'Field not classified'
            topics = item.get('topics', [])
            keywords = []
            if topics:
                field_of_study = topics[0].get('display_name', 'Field not classified')
                keywords = [t.get('display_name') for t in topics]
            
            references = [str(ref).split('/')[-1] for ref in item.get('referenced_works', [])]
            
            oa_data = item.get('open_access') or {}
            pdf_url = oa_data.get('oa_url') or primary_loc.get('pdf_url') or 'PDF URL not available'

            return Paper(
                paper_id=paper_id,
                title=title,
                authors=authors,
                year=year,
                cited_by_count=cited_by_count,
                doi=doi,
                publisher=publisher,
                abstract=abstract_text,
                publication_type=pub_type,
                journal_name=journal_name,
                venue=venue,
                field_of_study=field_of_study,
                references=references,
                pdf_url=pdf_url,
                keywords=keywords
            )
        except Exception as e:
            logger.error(f"Error parsing paper: {e}")
            return None

    def _parse_paper(self, item: dict) -> Optional[Paper]:
        return None


def reset_author_citation_cache():
    global _author_citation_cache
    _author_citation_cache = AuthorCitationCache()

def get_author_citation_cache():
    return _author_citation_cache


class CrossRefClient(BaseAPIClient):
    BASE_URL = "https://api.crossref.org/works"
    async def search(self, keyword: str, year: int, limit: int) -> List[Paper]: return []
    async def enrich_paper(self, paper: Paper) -> Paper: return paper


class ArXivClient(BaseAPIClient):
    BASE_URL = "http://export.arxiv.org/api/query"
    async def search(self, keyword: str, year: int, limit: int) -> List[Paper]: return []
