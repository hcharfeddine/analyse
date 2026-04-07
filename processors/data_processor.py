"""
Data processing utilities for academic papers.
"""

from typing import List, Dict
from collections import defaultdict

from models.paper import Paper


class DataProcessor:
    @staticmethod
    def remove_duplicates(papers: List[Paper]) -> List[Paper]:
        unique_papers = []
        seen_ids = set()
        for paper in papers:
            if not paper.paper_id:
                continue
            if paper.paper_id not in seen_ids:
                seen_ids.add(paper.paper_id)
                unique_papers.append(paper)
        return unique_papers
    
    @staticmethod
    def group_by_keyword_year(papers: List[Paper]) -> Dict[str, Dict[str, List[dict]]]:
        grouped = defaultdict(lambda: defaultdict(list))
        for paper in papers:
            grouped["Uncategorized"][str(paper.year)].append(paper.to_dict())
        return dict(grouped)
    
    @staticmethod
    def get_statistics(papers: List[Paper]) -> Dict:
        stats = {
            'total_papers': len(papers),
            'by_year': defaultdict(int),
            'total_citations': 0
        }
        for paper in papers:
            stats['by_year'][paper.year] += 1
            stats['total_citations'] += (paper.cited_by_count if paper.cited_by_count else 0)
        return stats
