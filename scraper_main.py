import asyncio
from typing import List, Dict
import os
from datetime import datetime
import logging
import time

from api_clients import OpenAlexClient, get_author_citation_cache, reset_author_citation_cache
from models import Paper
from filters import PaperFilter
from data_processor import DataProcessor
from exporters import CSVExporter, JSONExporter, PDFExporter
from metadata_quality_report import MetadataQualityReport
from config import config

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("schol_scraper.log"),
        logging.StreamHandler()
    ]
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class AcademicPaperScraper:
    """Academic paper scraper using OpenAlex API"""
    
    def __init__(self):
        self.processor = DataProcessor()
        self.filter = PaperFilter(
            require_authors=False,
            filter_surveys=False,
            filter_publishers=False,
            filter_citations=False
        )
        self.all_papers = []
        self.timing = {}
        self.start_time = None
        self.quality_report = MetadataQualityReport()
    
    def _print_timing(self, stage: str, elapsed: float):
        minutes = int(elapsed // 60)
        seconds = elapsed % 60
        time_str = f"{minutes}m {seconds:.1f}s" if minutes > 0 else f"{seconds:.1f}s"
        self.timing[stage] = elapsed
        print(f"    {stage:<40} {time_str:>12}")
    
    async def collect_papers(self) -> List[Paper]:
        stage_start = time.time()
        print("\n" + "="*70)
        print("ACADEMIC PAPER COLLECTION".center(70))
        print("="*70 + "\n")
        
        reset_author_citation_cache()
        
        async with OpenAlexClient() as client:
            all_papers = []
            for idx, year in enumerate(config.YEARS):
                print(f"  Fetching papers for year {year}... [{idx+1}/{len(config.YEARS)}]")
                try:
                    # Fetching without keyword since user said keywords not needed
                    papers = await client.search("*", year, config.MAX_PAPERS_PER_YEAR)
                    all_papers.extend(papers)
                    print(f"    Found {len(papers)} papers (Total: {len(all_papers)})")
                    # Minimal sleep between years
                    await asyncio.sleep(0.1)
                except Exception as e:
                    print(f"    Error fetching year {year}: {e}")
                    continue
        
        self.all_papers = all_papers
        elapsed = time.time() - stage_start
        self._print_timing("Paper collection", elapsed)
        return all_papers
    
    async def process_papers(self, papers: List[Paper]) -> List[Paper]:
        print("\n" + "-"*70)
        print("PROCESSING PAPERS".center(70))
        print("-"*70 + "\n")
        
        unique_papers = self.processor.remove_duplicates(papers)
        print(f"  Total collected:             {len(papers)}")
        print(f"  Unique papers:               {len(unique_papers)}")
        
        filtered_papers = self.filter.filter_papers(unique_papers)
        print(f"  After filtering:             {len(filtered_papers)}")
        
        # Analyze quality
        self.quality_report.analyze(filtered_papers)
        self.quality_report.print_report()
        
        return filtered_papers
    
    def export_results(self, papers: List[Paper]):
        export_start = time.time()
        if not os.path.exists(config.OUTPUT_FOLDER):
            os.makedirs(config.OUTPUT_FOLDER)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stats = self.processor.get_statistics(papers)
        grouped_data = self.processor.group_by_keyword_year(papers)
        
        if config.EXPORT_JSON:
            json_file = os.path.join(config.OUTPUT_FOLDER, f"papers_{timestamp}.json")
            JSONExporter(json_file).export(grouped_data)
        
        if config.EXPORT_CSV:
            csv_file = os.path.join(config.OUTPUT_FOLDER, f"papers_{timestamp}.csv")
            CSVExporter(csv_file).export(papers)
            
        export_elapsed = time.time() - export_start
        self._print_timing("Data export", export_elapsed)


async def main():
    start_all = time.time()
    try:
        scraper = AcademicPaperScraper()
        scraper.start_time = time.time()
        papers = await scraper.collect_papers()
        papers = await scraper.process_papers(papers)
        scraper.export_results(papers)
        
        total_elapsed = time.time() - start_all
        minutes = int(total_elapsed // 60)
        seconds = total_elapsed % 60
        time_str = f"{minutes}m {seconds:.1f}s" if minutes > 0 else f"{seconds:.1f}s"
        
        print("\n" + "="*70)
        print(f"TOTAL EXECUTION TIME: {time_str}".center(70))
        print("="*70 + "\n")
        
    except Exception as e:
        logger.exception("Fatal error in scraper")
        raise


if __name__ == "__main__":
    asyncio.run(main())
