"""
Metadata quality reporting tool.

This module provides detailed quality reports on metadata collection,
helping identify coverage gaps by year and metadata field.
"""

import json
from typing import List, Dict
from collections import defaultdict

from models import Paper


class MetadataQualityReport:
    """Analyzes and reports on metadata collection quality."""
    
    def __init__(self):
        self.papers_by_year = defaultdict(list)
        self.metadata_stats = {
            'total_papers': 0,
            'papers_with_title': 0,
            'papers_with_authors': 0,
            'papers_with_abstract': 0,
            'papers_with_affiliations': 0,
            'papers_with_pdf': 0,
            'papers_with_doi': 0,
            'papers_with_year': 0,
            'by_year': {}
        }
    
    def analyze(self, papers: List[Paper]) -> Dict:
        """Analyze metadata quality across all papers."""
        self.papers_by_year = defaultdict(list)
        
        for paper in papers:
            self.papers_by_year[paper.year].append(paper)
        
        self.metadata_stats['total_papers'] = len(papers)
        
        for paper in papers:
            if paper.title and paper.title != 'N/A':
                self.metadata_stats['papers_with_title'] += 1
            
            if paper.authors:
                self.metadata_stats['papers_with_authors'] += 1
                
                # Check for affiliations in authors
                has_aff = any(a.affiliations for a in paper.authors)
                if has_aff:
                    self.metadata_stats['papers_with_affiliations'] += 1
            
            if paper.abstract and paper.abstract != 'Abstract not available':
                self.metadata_stats['papers_with_abstract'] += 1
            
            if paper.pdf_url and paper.pdf_url != 'PDF URL not available':
                self.metadata_stats['papers_with_pdf'] += 1
            
            if paper.doi and paper.doi != 'DOI not available':
                self.metadata_stats['papers_with_doi'] += 1
            
            if paper.year > 0:
                self.metadata_stats['papers_with_year'] += 1
        
        for year in sorted(self.papers_by_year.keys()):
            year_papers = self.papers_by_year[year]
            total = len(year_papers)
            
            year_stats = {
                'total': total,
                'with_title': sum(1 for p in year_papers if p.title and p.title != 'N/A'),
                'with_authors': sum(1 for p in year_papers if p.authors),
                'with_abstract': sum(
                    1 for p in year_papers
                    if p.abstract and p.abstract != 'Abstract not available'
                ),
                'with_affiliations': sum(
                    1 for p in year_papers
                    if any(a.affiliations for a in p.authors)
                ),
                'with_pdf': sum(
                    1 for p in year_papers
                    if p.pdf_url and p.pdf_url != 'PDF URL not available'
                ),
                'with_doi': sum(
                    1 for p in year_papers
                    if p.doi and p.doi != 'DOI not available'
                ),
            }
            
            year_stats['title_coverage'] = f"{(year_stats['with_title'] / total * 100):.1f}%" if total > 0 else "0%"
            year_stats['authors_coverage'] = f"{(year_stats['with_authors'] / total * 100):.1f}%" if total > 0 else "0%"
            year_stats['abstract_coverage'] = f"{(year_stats['with_abstract'] / total * 100):.1f}%" if total > 0 else "0%"
            year_stats['affiliations_coverage'] = f"{(year_stats['with_affiliations'] / total * 100):.1f}%" if total > 0 else "0%"
            year_stats['pdf_coverage'] = f"{(year_stats['with_pdf'] / total * 100):.1f}%" if total > 0 else "0%"
            year_stats['doi_coverage'] = f"{(year_stats['with_doi'] / total * 100):.1f}%" if total > 0 else "0%"
            
            self.metadata_stats['by_year'][year] = year_stats
        
        return self.metadata_stats
    
    def print_report(self):
        """Print a formatted quality report."""
        print("\n" + "=" * 80)
        print("METADATA QUALITY REPORT")
        print("=" * 80)
        
        total = self.metadata_stats['total_papers']
        
        if total == 0:
            print(f"\nTotal Papers: {total}")
            print("No papers collected. Please check your API configuration and year settings.")
            print("=" * 80)
            return
        
        print(f"\nTotal Papers: {total}")
        print(f"Title coverage:        {self.metadata_stats['papers_with_title']}/{total} ({self.metadata_stats['papers_with_title']/total*100:.1f}%)")
        print(f"Author coverage:       {self.metadata_stats['papers_with_authors']}/{total} ({self.metadata_stats['papers_with_authors']/total*100:.1f}%)")
        print(f"Abstract coverage:     {self.metadata_stats['papers_with_abstract']}/{total} ({self.metadata_stats['papers_with_abstract']/total*100:.1f}%)")
        print(f"Affiliations coverage: {self.metadata_stats['papers_with_affiliations']}/{total} ({self.metadata_stats['papers_with_affiliations']/total*100:.1f}%)")
        print(f"PDF URL coverage:      {self.metadata_stats['papers_with_pdf']}/{total} ({self.metadata_stats['papers_with_pdf']/total*100:.1f}%)")
        print(f"DOI coverage:          {self.metadata_stats['papers_with_doi']}/{total} ({self.metadata_stats['papers_with_doi']/total*100:.1f}%)")
        print(f"Year coverage:         {self.metadata_stats['papers_with_year']}/{total} ({self.metadata_stats['papers_with_year']/total*100:.1f}%)")
        
        print("\n" + "-" * 80)
        print("BREAKDOWN BY YEAR")
        print("-" * 80)
        
        for year in sorted(self.metadata_stats['by_year'].keys()):
            stats = self.metadata_stats['by_year'][year]
            print(f"\n{year}:")
            print(f"  Total Papers: {stats['total']}")
            print(f"  Title:        {stats['with_title']}/{stats['total']} ({stats['title_coverage']})")
            print(f"  Authors:      {stats['with_authors']}/{stats['total']} ({stats['authors_coverage']})")
            print(f"  Abstract:     {stats['with_abstract']}/{stats['total']} ({stats['abstract_coverage']})")
            print(f"  Affiliations: {stats['with_affiliations']}/{stats['total']} ({stats['affiliations_coverage']})")
            print(f"  PDF:          {stats['with_pdf']}/{stats['total']} ({stats['pdf_coverage']})")
            print(f"  DOI:          {stats['with_doi']}/{stats['total']} ({stats['doi_coverage']})")
        
        print("\n" + "=" * 80)
    
    def save_report(self, filename: str):
        """Save report to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.metadata_stats, f, indent=2)
