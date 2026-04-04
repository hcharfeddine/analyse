"""
Schol - Academic Paper Collection Framework

A comprehensive Python library for collecting, processing, and enriching
academic paper metadata from multiple sources.

Modules:
    models: Data models for papers and authors
    config: Configuration management
    api_clients: API clients for academic data sources
    advanced_enrichers: Additional enrichment sources
    metadata_enricher_v3: Enrichment orchestration
    data_processor: Data processing utilities
    filters: Paper filtering
    exporters: Export to CSV, JSON, PDF
    analyze_metadata_gaps: Gap analysis tools
    metadata_quality_report: Quality reporting
    exceptions: Custom exceptions
"""

from .models import Paper, Author
from .config import config, ScraperConfig
from .exceptions import ScraperException, APIException, ExportException, ValidationException
from .data_processor import DataProcessor
from .filters import PaperFilter
from .exporters import CSVExporter, JSONExporter, PDFExporter
from .api_clients import (
    OpenAlexClient,
    CrossRefClient,
    ArXivClient,
    get_author_citation_cache,
    reset_author_citation_cache
)
from .advanced_enrichers import (
    GoogleScholarEnricher,
    SSRNEnricher,
    ResearchGateEnricher,
    DOIEnricher
)
from .metadata_enricher_v3 import ComprehensiveMetadataEnricher
from .analyze_metadata_gaps import MetadataGapAnalyzer
from .metadata_quality_report import MetadataQualityReport

__version__ = "1.0.0"
__author__ = "Academic Paper Collection Team"

__all__ = [
    # Models
    "Paper",
    "Author",
    
    # Configuration
    "config",
    "ScraperConfig",
    
    # Exceptions
    "ScraperException",
    "APIException",
    "ExportException",
    "ValidationException",
    
    # Processing
    "DataProcessor",
    "PaperFilter",
    
    # Exporters
    "CSVExporter",
    "JSONExporter",
    "PDFExporter",
    
    # API Clients
    "OpenAlexClient",
    "CrossRefClient",
    "ArXivClient",
    "get_author_citation_cache",
    "reset_author_citation_cache",
    
    # Enrichers
    "GoogleScholarEnricher",
    "SSRNEnricher",
    "ResearchGateEnricher",
    "DOIEnricher",
    "ComprehensiveMetadataEnricher",
    
    # Analysis
    "MetadataGapAnalyzer",
    "MetadataQualityReport",
]
