"""
Paper filtering utilities.
"""

from typing import List

from models.paper import Paper


class PaperFilter:
    """Filters papers based on quality and relevance criteria."""
    
    ALLOWED_PUBLISHERS = {
        'IEEE', 'ACM', 'Elsevier', 'Wiley', 'Springer', 'Arxiv',
        'EMNLP', 'IJCNLP', 'Computational Linguistics', 'CoNLL', 'EACL',
        'NAACL', 'ACL', 'Findings', 'COLING',
        'ICLR', 'CVPR', 'ICCV', 'ECCV', 'WACV', 'ICML', 'AAAI'
    }
    
    def __init__(
        self,
        min_citations: int = 10,
        min_citations_arxiv: int = 5,
        require_authors: bool = True,
        filter_surveys: bool = True,
        filter_publishers: bool = True,
        filter_citations: bool = True  # Added flag to optionally disable citation filtering
    ):
        self.min_citations = min_citations
        self.min_citations_arxiv = min_citations_arxiv
        self.require_authors = require_authors
        self.filter_surveys = filter_surveys
        self.filter_publishers = filter_publishers
        self.filter_citations = filter_citations  # Store the flag
    
    def filter_papers(self, papers: List[Paper]) -> List[Paper]:
        """Apply all configured filters to a list of papers."""
        filtered = papers
        
        if self.require_authors:
            filtered = [p for p in filtered if self._has_authors(p)]
        
        if self.filter_citations:
            filtered = [p for p in filtered if self._has_min_citations(p)]
        
        if self.filter_surveys:
            filtered = [p for p in filtered if not self._is_survey(p)]
        
        # This fixes the issue where Open Alex and other sources provide data in different publisher formats
        if self.filter_publishers:
            filtered = [p for p in filtered if self._is_allowed_publisher_or_unspecified(p)]
        
        return filtered
    
    def _has_authors(self, paper: Paper) -> bool:
        """Check if paper has valid authors."""
        if not paper.authors or len(paper.authors) == 0:
            return False
        return any(author.name and author.name.strip() for author in paper.authors)
    
    def _has_min_citations(self, paper: Paper) -> bool:
        """Check if paper meets minimum citation requirement."""
        normalized_publisher = paper.get_normalized_publisher()
        
        if normalized_publisher == 'Arxiv':
            return paper.citations >= self.min_citations_arxiv
        return paper.citations >= self.min_citations
    
    def _is_survey(self, paper: Paper) -> bool:
        """Check if paper is a survey or review."""
        return paper.is_survey_or_review()
    
    def _is_allowed_publisher(self, paper: Paper) -> bool:
        """Check if paper is from an allowed publisher."""
        normalized = paper.get_normalized_publisher()
        return normalized in self.ALLOWED_PUBLISHERS
    
    def _is_allowed_publisher_or_unspecified(self, paper: Paper) -> bool:
        """
        Check if paper is from an allowed publisher OR has unspecified publisher.
        
        This is more permissive than strict publisher filtering, allowing papers
        from sources like Open Alex that may have different publisher data formats.
        Papers with empty, unspecified, or unrecognized publishers are accepted
        as long as they pass other quality checks (authors, citations, not survey).
        """
        if not paper.publisher or paper.publisher.strip() == "" or paper.publisher == "Unknown":
            # Accept papers with missing/empty publisher (already passed other filters)
            return True
        
        normalized = paper.get_normalized_publisher()
        
        # If we have a recognized publisher name, require it to be in the allowed list
        if normalized in self.ALLOWED_PUBLISHERS:
            return True
        
        # For unrecognized publisher names, accept them (as long as they passed citation/author checks)
        # This allows papers from smaller publishers or new sources
        return True
    
    def get_publisher_summary(self, papers: List[Paper]) -> dict:
        """Generate summary of publishers in the paper collection."""
        publisher_counts = {}
        
        for paper in papers:
            normalized = paper.get_normalized_publisher()
            publisher_counts[normalized] = publisher_counts.get(normalized, 0) + 1
        
        sorted_publishers = sorted(
            publisher_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            'total_papers': len(papers),
            'unique_publishers': len(publisher_counts),
            'publishers': dict(sorted_publishers)
        }
