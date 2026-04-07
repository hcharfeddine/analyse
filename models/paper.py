"""
Data models for academic paper collection.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Author:
    """Represents an academic paper author with associated metadata."""
    
    author_id: Optional[str] = None
    affiliations: List[str] = field(default_factory=list)
    ror_ids: List[str] = field(default_factory=list)
    countries: List[str] = field(default_factory=list)
    organization_types: List[str] = field(default_factory=list)
    citation_count: int = 0  # Author's total citation count
    
    def to_dict(self) -> dict:
        """Convert author to dictionary representation."""
        return {
            'author_id': self.author_id,
            'affiliations': self.affiliations if self.affiliations else [],
            'ror_ids': self.ror_ids if self.ror_ids else [],
            'countries': self.countries if self.countries else [],
            'organization_types': self.organization_types if self.organization_types else [],
            'citation_count': self.citation_count if self.citation_count is not None else 0
        }


@dataclass
class CitationPaper:
    paper_id: Optional[str] = None
    title: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            'paper_id': self.paper_id,
            'title': self.title,
            'authors': self.authors,
            'year': self.year
        }


@dataclass
class Paper:
    paper_id: Optional[str] = None
    title: str = ""
    authors: List[Author] = field(default_factory=list)
    year: int = 0
    cited_by_count: int = 0
    doi: str = ""
    publisher: str = ""
    abstract: str = "Abstract not available"
    publication_type: str = "Unknown"
    journal_name: str = "Journal not specified"
    venue: str = "Venue not specified"
    field_of_study: str = "Field not classified"
    references: List[str] = field(default_factory=list)
    pdf_url: str = "PDF URL not available"
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'paper_id': self.paper_id,
            'title': self.title,
            'authors': [a.to_dict() for a in self.authors],
            'year': self.year,
            'cited_by_count': self.cited_by_count if self.cited_by_count is not None else 0,
            'doi': self.doi,
            'publisher': self.publisher,
            'abstract': self.abstract,
            'publication_type': self.publication_type,
            'journal_name': self.journal_name,
            'venue': self.venue,
            'field_of_study': self.field_of_study,
            'references': self.references if self.references else [],
            'pdf_url': self.pdf_url,
            'keywords': self.keywords if self.keywords else []
        }
    
    @property
    def normalized_title(self) -> str:
        if not self.title:
            return ""
        return self.title.lower().strip()
