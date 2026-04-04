"""
Advanced metadata enrichers for comprehensive paper coverage.
"""

import asyncio
import aiohttp
import time
import re
import logging
from typing import Optional
from difflib import SequenceMatcher

from models import Paper

logger = logging.getLogger(__name__)


class GoogleScholarEnricher:
    """Enriches metadata using Google Scholar search."""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.last_request_time = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def enrich_paper(self, paper: Paper) -> Paper:
        """Attempt to find paper on Google Scholar and extract metadata."""
        await self._enforce_rate_limit()
        
        try:
            search_url = "https://scholar.google.com/scholar"
            params = {'q': paper.title}
            
            async with self.session.get(
                search_url,
                params=params,
                headers=self.headers,
                timeout=10
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    if paper.pdf_url == 'PDF URL not available':
                        pdf_url = self._extract_pdf_url(html)
                        if pdf_url:
                            paper.pdf_url = pdf_url
        except Exception as e:
            logger.debug(f"Google Scholar enrichment error: {e}")
        
        return paper
    
    def _extract_pdf_url(self, html: str) -> Optional[str]:
        """Extract PDF URL from Google Scholar HTML."""
        pdf_pattern = r'\[PDF\].*?href=["\']([^"\']+)["\']'
        matches = re.findall(pdf_pattern, html)
        return matches[0] if matches else None
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        delay_needed = 2.0 - elapsed
        
        if delay_needed > 0:
            await asyncio.sleep(delay_needed)
        
        self.last_request_time = time.time()


class SSRNEnricher:
    """Enriches metadata using SSRN."""
    
    def __init__(self):
        self.session = None
        self.headers = {'User-Agent': 'Academic Research Tool/1.0'}
        self.last_request_time = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def enrich_paper(self, paper: Paper) -> Paper:
        """Attempt to find paper on SSRN and extract metadata."""
        await self._enforce_rate_limit()
        
        try:
            search_url = "https://papers.ssrn.com/sol3/results.cfm"
            params = {'q': paper.title}
            
            async with self.session.get(
                search_url,
                params=params,
                headers=self.headers,
                timeout=10
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    if paper.abstract == 'Abstract not available':
                        abstract = self._extract_abstract(html)
                        if abstract:
                            paper.abstract = abstract
                    
                    if paper.pdf_url == 'PDF URL not available':
                        pdf_url = self._extract_pdf_url(html)
                        if pdf_url:
                            paper.pdf_url = pdf_url
        except Exception as e:
            logger.debug(f"SSRN enrichment error: {e}")
        
        return paper
    
    def _extract_abstract(self, html: str) -> Optional[str]:
        """Extract abstract from SSRN HTML."""
        abstract_pattern = r'<h3>Abstract</h3>.*?<p>(.*?)</p>'
        matches = re.findall(abstract_pattern, html, re.DOTALL)
        
        if matches:
            abstract = re.sub(r'<[^>]+>', '', matches[0]).strip()
            if len(abstract) > 50:
                return abstract
        return None
    
    def _extract_pdf_url(self, html: str) -> Optional[str]:
        """Extract PDF URL from SSRN HTML."""
        pdf_pattern = r'href=["\']([^"\']*\.pdf)["\']'
        matches = re.findall(pdf_pattern, html)
        
        if matches:
            url = matches[0]
            if not url.startswith('http'):
                url = 'https://papers.ssrn.com' + url
            return url
        return None
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        delay_needed = 1.0 - elapsed
        
        if delay_needed > 0:
            await asyncio.sleep(delay_needed)
        
        self.last_request_time = time.time()


class ResearchGateEnricher:
    """Enriches metadata using ResearchGate."""
    
    def __init__(self):
        self.session = None
        self.headers = {'User-Agent': 'Academic Research Tool/1.0'}
        self.last_request_time = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def enrich_paper(self, paper: Paper) -> Paper:
        """Attempt to find paper on ResearchGate and extract metadata."""
        await self._enforce_rate_limit()
        
        try:
            search_url = "https://www.researchgate.net/search"
            params = {'q': paper.title}
            
            async with self.session.get(
                search_url,
                params=params,
                headers=self.headers,
                timeout=10
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    if paper.author_affiliations == 'Affiliations not available':
                        affiliations = self._extract_affiliations(html)
                        if affiliations:
                            paper.author_affiliations = affiliations
                    
                    if paper.pdf_url == 'PDF URL not available':
                        pdf_url = self._extract_pdf_url(html)
                        if pdf_url:
                            paper.pdf_url = pdf_url
        except Exception as e:
            logger.debug(f"ResearchGate enrichment error: {e}")
        
        return paper
    
    def _extract_affiliations(self, html: str) -> Optional[str]:
        """Extract author affiliations from ResearchGate HTML."""
        aff_pattern = r'<span[^>]*>([^<]*(?:University|Institute|College|Lab)[^<]*)</span>'
        matches = re.findall(aff_pattern, html, re.IGNORECASE)
        
        if matches:
            affiliations = list(set(matches))[:5]
            return '; '.join(affiliations)
        return None
    
    def _extract_pdf_url(self, html: str) -> Optional[str]:
        """Extract PDF URL from ResearchGate HTML."""
        pdf_pattern = r'href=["\']([^"\']*\.pdf)["\']'
        matches = re.findall(pdf_pattern, html)
        
        if matches:
            url = matches[0]
            if not url.startswith('http'):
                url = 'https://www.researchgate.net' + url
            return url
        return None
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        delay_needed = 1.5 - elapsed
        
        if delay_needed > 0:
            await asyncio.sleep(delay_needed)
        
        self.last_request_time = time.time()


class DOIEnricher:
    """Enriches metadata by searching for missing DOIs."""
    
    def __init__(self):
        self.session = None
        self.headers = {'User-Agent': 'Academic Research Tool/1.0'}
        self.last_request_time = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def enrich_paper(self, paper: Paper) -> Paper:
        """Attempt to find DOI for paper using CrossRef search."""
        if paper.doi != 'DOI not available':
            return paper
        
        await self._enforce_rate_limit()
        
        try:
            search_url = "https://api.crossref.org/works"
            params = {'query': paper.title, 'rows': 1}
            
            async with self.session.get(search_url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('message', {}).get('items'):
                        item = data['message']['items'][0]
                        
                        if self._titles_match(paper.title, item.get('title', [''])[0]):
                            if item.get('DOI'):
                                paper.doi = item['DOI']
        except Exception as e:
            logger.debug(f"DOI lookup error: {e}")
        
        return paper
    
    def _titles_match(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """Check if two titles are similar enough."""
        ratio = SequenceMatcher(None, title1.lower(), title2.lower()).ratio()
        return ratio >= threshold
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        delay_needed = 0.1 - elapsed
        
        if delay_needed > 0:
            await asyncio.sleep(delay_needed)
        
        self.last_request_time = time.time()
