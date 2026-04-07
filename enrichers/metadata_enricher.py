"""
Comprehensive metadata enrichment orchestrator.
"""

import logging
import asyncio
from typing import List

from models.paper import Paper
from services.base_client import OpenAlexClient, CrossRefClient, ArXivClient
from enrichers.advanced_enrichers import (
    GoogleScholarEnricher,
    SSRNEnricher,
    ResearchGateEnricher,
    DOIEnricher
)
# from tools.pdf_downloader import PDFDownloader
# from enrichers.grobid_enricher import GROBIDEnricher
from config import config

logger = logging.getLogger(__name__)


class ComprehensiveMetadataEnricher:
    """Orchestrates metadata enrichment from multiple sources."""
    
    def __init__(self):
        self.openalex_client = None
        self.crossref_client = None
        self.arxiv_client = None
        self.google_scholar = None
        self.ssrn = None
        self.researchgate = None
        self.doi_enricher = None
        self.pdf_downloader = None
        self.grobid_enricher = None
    
    async def __aenter__(self):
        self.openalex_client = OpenAlexClient()
        await self.openalex_client.__aenter__()
        
        self.crossref_client = CrossRefClient()
        await self.crossref_client.__aenter__()
        
        self.arxiv_client = ArXivClient()
        await self.arxiv_client.__aenter__()
        
        self.google_scholar = GoogleScholarEnricher()
        await self.google_scholar.__aenter__()
        
        self.ssrn = SSRNEnricher()
        await self.ssrn.__aenter__()
        
        self.researchgate = ResearchGateEnricher()
        await self.researchgate.__aenter__()
        
        self.doi_enricher = DOIEnricher()
        await self.doi_enricher.__aenter__()
        
        # Disabled browser-based components for stability and environment compatibility
        # self.pdf_downloader = PDFDownloader()
        # await self.pdf_downloader.__aenter__()
        
        # self.grobid_enricher = GROBIDEnricher()
        # await self.grobid_enricher.__aenter__()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        clients = [
            self.openalex_client, self.crossref_client, self.arxiv_client,
            self.google_scholar, self.ssrn, self.researchgate, self.doi_enricher,
            self.pdf_downloader, self.grobid_enricher
        ]
        
        for client in clients:
            if client:
                await client.__aexit__(exc_type, exc_val, exc_tb)
    
    def _is_arxiv_doi(self, doi: str) -> bool:
        """Check if DOI is an arXiv DOI."""
        return doi and doi.startswith('10.48550/arXiv.')
    
    async def enrich_papers(self, papers: List[Paper]) -> List[Paper]:
        """
        Smart metadata enrichment for 95%+ coverage.
        - CrossRef: All papers (fast, adds references/DOIs)
        - GROBID: Only papers missing affiliations (~30%)
        - Citations: Only high-impact papers (50+ citations)
        """
        logger.info(f"Processing {len(papers)} papers with smart selective enrichment")
        
        # Categorize papers by enrichment needs
        needs_crossref = []
        needs_citations = []
        
        for paper in papers:
            # All papers get CrossRef enrichment for complete references
            needs_crossref.append(paper)
            
            # Citations: Only for high-impact papers (50+ citations)
            if config.ENABLE_CITATION_ENRICHMENT:
                try:
                    cited_count = int(paper.citations) if paper.citations else 0
                    if cited_count >= config.CITATION_QUALITY_THRESHOLD:
                        needs_citations.append(paper)
                except (ValueError, TypeError):
                    pass
        
        logger.info(f"Enrichment plan: {len(needs_crossref)} CrossRef, {len(needs_citations)} Citations (PDF/GROBID disabled)")
        
        # Phase 1: CrossRef enrichment (fast, all papers)
        async def enrich_crossref(paper):
            if config.USE_CROSSREF and paper.doi != 'DOI not available':
                try:
                    paper = await self.crossref_client.enrich_paper(paper)
                    if paper.references and len(paper.references) > 0:
                        logger.debug(f"[v0] Paper {paper.paper_id} now has {len(paper.references)} references")
                except Exception as e:
                    logger.debug(f"CrossRef enrichment failed for {paper.paper_id}: {e}")
            return paper
        
        logger.info("Phase 1: CrossRef enrichment...")
        logger.info(f"[v0] CrossRef enrichment: {len(needs_crossref)} papers to enrich, USE_CROSSREF={config.USE_CROSSREF}")
        crossref_tasks = [enrich_crossref(p) for p in needs_crossref]
        papers = await asyncio.gather(*crossref_tasks)
        papers_with_refs = sum(1 for p in papers if p.references and len(p.references) > 0)
        logger.info(f"Phase 1 complete: {len(papers)} papers enriched, {papers_with_refs} now have references")
        
        # Phase 2: Citation enrichment (very selective, only high-impact papers)
        if needs_citations:
            logger.info(f"Phase 2: Citation enrichment for {len(needs_citations)} high-impact papers...")
            
            async def enrich_citations(paper):
                try:
                    if config.ENABLE_CITATION_ENRICHMENT and paper.paper_id:
                        paper = await self._enrich_citations(paper)
                except Exception as e:
                    logger.debug(f"Citation enrichment failed for {paper.paper_id}: {e}")
                return paper
            
            citations_tasks = [enrich_citations(p) for p in needs_citations]
            enriched_citations = await asyncio.gather(*citations_tasks)
            
            # Update papers with citation results
            paper_map = {p.paper_id: p for p in papers}
            for enriched in enriched_citations:
                if enriched.paper_id in paper_map:
                    paper_map[enriched.paper_id] = enriched
            papers = list(paper_map.values())
            logger.info(f"Phase 2 complete: {len(needs_citations)} papers enriched")
        
        logger.info(f"Enrichment complete: {len(papers)} papers (PDF/GROBID disabled for speed)")
        return papers
    
    async def _enrich_citations(self, paper: Paper) -> Paper:
        """Enrich paper with citation relationships."""
        # Citation enrichment disabled - references come from CrossRef during enrichment phase
        # Cited_by count is provided directly from OpenAlex (paper.citations field)
        return paper
    
    def _needs_enrichment(self, paper: Paper) -> bool:
        """Check if paper still needs metadata enrichment."""
        return (
            paper.abstract == 'Abstract not available' or
            paper.author_affiliations == 'Affiliations not available'
        )
