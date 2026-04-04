# Academic Paper Collector & Metadata Enricher

A professional-grade automated tool for harvesting, filtering, and enriching academic paper metadata from multiple scholarly sources. This project specializes in high-fidelity data extraction, including author affiliations, citation metrics, and full-text PDF acquisition.

## Key Features

- **Multi-Source Discovery**: Integrates with Semantic Scholar, CrossRef, arXiv, and Google Scholar for comprehensive coverage.
- **Robust PDF Acquisition**: Utilizes Playwright-based headless browsing to bypass bot detection on major publisher sites (IEEE, ACM, etc.) and handles Brotli-compressed assets.
- **Deep Metadata Enrichment**: 
  - **GROBID Integration**: Extracts granular author affiliations directly from PDF full-texts.
  - **Author Analytics**: Fetches comprehensive citation counts and historical metadata for all contributors.
  - **Topic Modeling**: Automatically scrapes and populates paper-level keywords and topics.
- **Resilient Processing**: Built-in exponential backoff and retry logic for third-party APIs and GROBID services.
- **Multi-Format Export**: Generates professional reports in CSV, JSON, and stylized PDF formats.
- **High Performance**: Features parallel scraping, asynchronous processing, and intelligent browser context pooling.

## Project Structure

- `academic/scraper_main.py`: The primary entry point orchestrating the collection and enrichment workflow.
- `academic/pdf_downloader.py`: Advanced PDF retrieval engine with Playwright fallback logic.
- `academic/grobid_enricher.py`: Handles high-precision affiliation extraction from scientific papers.
- `academic/web_scraper.py`: Core logic for scraping Semantic Scholar and other academic portals.
- `academic/config.py`: Centralized configuration for keywords, years, and performance tuning.

## Technical Enhancements

This version of the project includes several critical upgrades:
- **Intelligent PDF Downloader**: Automatically switches to browser-based scraping when standard HTTP requests are blocked or return HTML pages.
- **Brotli Support**: Native handling of modern web compression formats used by academic publishers.
- **Optimized Resource Usage**: Default logging set to `WARNING` with granular controls to minimize CPU overhead during large-scale runs.
- **Improved Extraction**: Specialized selectors for major publishers ensuring higher success rates for affiliation data.

## Requirements

- Python 3.8+
- Playwright (with Chromium)
- GROBID Service (running instance)
- Additional dependencies listed in `academic/requirements.txt`
