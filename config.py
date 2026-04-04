"""
Configuration settings for the academic paper scraper.

This module provides centralized configuration management for all components
including API settings, rate limits, and export options.

OPTIMIZED FOR MAXIMUM PERFORMANCE AND COMPLETE METADATA EXTRACTION
"""

import logging
from typing import List
from dataclasses import dataclass, field


@dataclass
class ScraperConfig:
    """Configuration settings for the paper scraping system."""
    
    # Logging Configuration
    LOG_LEVEL: str = "WARNING"  # Reduced for performance
    ENABLE_VERBOSE_LOGGING: bool = False

    YEARS: List[int] = field(default_factory=lambda: [2024])

    # Request Settings - COMPREHENSIVE DATA COLLECTION
    REQUEST_TIMEOUT: int = 120  # Increased for stability with large requests
    RETRY_ATTEMPTS: int = 5
    DELAY_BETWEEN_REQUESTS: float = 0.1  # Minimal delay for OpenAlex (no rate limit)
    
    # Semantic Scholar Settings
    SEMANTIC_SCHOLAR_RATE_LIMIT_DELAY: float = 0.1
    SEMANTIC_SCHOLAR_RETRY_DELAY: float = 5.0
    SEMANTIC_SCHOLAR_MAX_RETRIES: int = 3
    SEMANTIC_SCHOLAR_API_KEY: str = ""
    MAX_CONCURRENT_REQUESTS: int = 30  # Maximum parallel requests for comprehensive fetching
    MAX_CONCURRENT_AUTHOR_FETCHES: int = 20  # Maximum parallel author citation fetching
    MAX_CONCURRENT_ENRICHMENT: int = 30  # Maximum parallel enrichment
    
    # Author Citation Settings - NOW OPTIMIZED!
    # Set to False to skip author citation fetching (saves significant time)
    # If False, citation counts will be extracted from work response if available
    FETCH_AUTHOR_CITATIONS: bool = False  # Set to True to fetch individual author metrics
    FETCH_AUTHOR_CITATIONS_TIMEOUT: float = 30.0  # Max time to spend on author citation fetching
    
    SKIP_AUTHOR_CITATIONS: bool = False  # ENABLED - fetch ALL author citation counts
    PARALLEL_TOPIC_AND_AUTHOR_FETCH: bool = True
    
    # Citation Enrichment Settings - DISABLED
    # References come from CrossRef enrichment, citations counts from OpenAlex
    ENABLE_CITATION_ENRICHMENT: bool = False
    MAX_CITATIONS_PER_PAPER: int = 0
    MAX_REFERENCES_PER_PAPER: int = 0
    CITATION_RATE_LIMIT_DELAY: float = 0.0
    CITATION_QUALITY_THRESHOLD: int = 0
    
    # Topic Scraping Settings
    MAX_CONCURRENT_TOPIC_SCRAPES: int = 10  # REDUCED
    NUM_BROWSER_CONTEXTS: int = 0  # DISABLED
    TOPIC_SCRAPE_MIN_DELAY: float = 0.5  # INCREASED
    TOPIC_SCRAPE_PAGE_TIMEOUT: int = 15000  # INCREASED
    TOPIC_SCRAPE_WAIT_FOR_TOPICS: int = 3000  # INCREASED
    
    # Data Source Toggles - SMART SELECTION
    USE_SEMANTIC_SCHOLAR: bool = False
    USE_CROSSREF: bool = False  # DISABLED to prioritize speed and OpenAlex references
    USE_ARXIV: bool = False  # DISABLED to prioritize speed
    USE_GOOGLE_SCHOLAR: bool = False
    USE_SSRN: bool = False
    USE_RESEARCHGATE: bool = False
    USE_DOI_LOOKUP: bool = False  # DISABLED to prioritize speed
    USE_OPENALEX: bool = True
    
    # GROBID settings for PDF affiliation extraction
    # DISABLED - PDF downloads consume too much time with minimal benefit
    USE_GROBID: bool = False
    GROBID_URL: str = "http://localhost:8070"
    GROBID_TIMEOUT: int = 15
    GROBID_SELECTIVE: bool = False
    GROBID_MAX_PAPERS: int = 0
    
    # PDF Downloader Settings - DISABLED
    PDF_DOWNLOAD_DIR: str = "pdfs"
    PDF_DOWNLOAD_TIMEOUT: int = 0
    PDF_MAX_SIZE_MB: int = 0
    PDF_SKIP_DOWNLOAD_IF_EXISTS: bool = True
    PDF_SELECTIVE_DOWNLOAD: bool = False
    
    # API Keys - REQUIRED AS OF FEBRUARY 13, 2026
    # Get your free OpenAlex API key at: https://openalex.org/settings/account
    # API key enables: faster requests, higher rate limits, access to from_created_date/from_updated_date filters
    CORE_API_KEY: str = "qs9vjo5oT546nGac5CCGHy"  # IMPORTANT: Replace with your own OpenAlex API key
    OPENALEX_MAILTO: str = "hcharfedine@gmail.com"  # Required: Your email for API identification

    # Output Settings
    OUTPUT_FOLDER: str = "output"
    EXPORT_CSV: bool = False
    EXPORT_JSON: bool = True
    EXPORT_PDF: bool = False  # DISABLED for speed (can be slow for large datasets)
    
    # Year-only search configuration 
    # COMPREHENSIVE: Fetch EVERY SINGLE paper from OpenAlex
    MAX_PAPERS_PER_YEAR: int = 999999999  # Fetch ALL papers per year
    YEAR_ONLY_DEDUPLICATION: bool = True


config = ScraperConfig()
