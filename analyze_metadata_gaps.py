"""
Metadata gap analysis tool.

This module provides functionality to analyze metadata completeness
and identify papers that can benefit from enrichment.
"""

import json
from typing import List, Dict
from collections import defaultdict

from models import Paper


class MetadataGapAnalyzer:
    """Analyzes metadata gaps and enrichment potential."""
    
    def __init__(self):
        self.gaps = defaultdict(list)
    
    def analyze(self, papers: List[Paper]) -> Dict:
        """Analyze metadata gaps across all papers."""
        analysis = {
            'total_papers': len(papers),
            'by_year': {},
            'enrichment_potential': {
                'crossref_eligible': 0,
                'arxiv_eligible': 0,
                'both_eligible': 0,
                'no_enrichment_possible': 0
            },
            'missing_metadata': {
                'no_abstract': 0,
                'no_affiliations': 0,
                'no_pdf': 0,
                'all_missing': 0
            }
        }
        
        for paper in papers:
            year = paper.year
            if year not in analysis['by_year']:
                analysis['by_year'][year] = {
                    'total': 0,
                    'missing_abstract': 0,
                    'missing_affiliations': 0,
                    'missing_pdf': 0,
                    'has_doi': 0,
                    'crossref_eligible': 0,
                    'arxiv_eligible': 0,
                }
            
            year_data = analysis['by_year'][year]
            year_data['total'] += 1
            
            has_abstract = paper.abstract and paper.abstract != 'Abstract not available'
            has_affiliations = (
                paper.author_affiliations and
                paper.author_affiliations != 'Affiliations not available'
            )
            has_pdf = paper.pdf_url and paper.pdf_url != 'PDF URL not available'
            has_doi = paper.doi and paper.doi != 'DOI not available'
            
            if not has_abstract:
                year_data['missing_abstract'] += 1
                analysis['missing_metadata']['no_abstract'] += 1
            
            if not has_affiliations:
                year_data['missing_affiliations'] += 1
                analysis['missing_metadata']['no_affiliations'] += 1
            
            if not has_pdf:
                year_data['missing_pdf'] += 1
                analysis['missing_metadata']['no_pdf'] += 1
            
            if not has_abstract and not has_affiliations and not has_pdf:
                analysis['missing_metadata']['all_missing'] += 1
            
            if has_doi:
                year_data['has_doi'] += 1
                year_data['crossref_eligible'] += 1
                analysis['enrichment_potential']['crossref_eligible'] += 1
            
            if not has_abstract:
                year_data['arxiv_eligible'] += 1
                analysis['enrichment_potential']['arxiv_eligible'] += 1
            
            if has_doi and not has_abstract:
                analysis['enrichment_potential']['both_eligible'] += 1
            
            if not has_doi and has_abstract:
                analysis['enrichment_potential']['no_enrichment_possible'] += 1
        
        return analysis
    
    def print_analysis(self, analysis: Dict):
        """Print formatted analysis report."""
        print("\n" + "=" * 80)
        print("METADATA GAP ANALYSIS")
        print("=" * 80)
        
        total = analysis['total_papers']
        print(f"\nTotal Papers: {total}")
        
        print(f"\nMissing Metadata Summary:")
        print(f"  Papers without abstract: {analysis['missing_metadata']['no_abstract']}")
        print(f"  Papers without affiliations: {analysis['missing_metadata']['no_affiliations']}")
        print(f"  Papers without PDF: {analysis['missing_metadata']['no_pdf']}")
        print(f"  Papers missing ALL metadata: {analysis['missing_metadata']['all_missing']}")
        
        print(f"\nEnrichment Potential:")
        print(f"  CrossRef eligible (has DOI): {analysis['enrichment_potential']['crossref_eligible']}")
        print(f"  arXiv eligible (missing abstract): {analysis['enrichment_potential']['arxiv_eligible']}")
        print(f"  Both sources eligible: {analysis['enrichment_potential']['both_eligible']}")
        print(f"  Cannot be enriched: {analysis['enrichment_potential']['no_enrichment_possible']}")
        
        print(f"\nBreakdown by Year:")
        print("-" * 80)
        
        for year in sorted(analysis['by_year'].keys()):
            data = analysis['by_year'][year]
            total_year = data['total']
            print(f"\n{year}:")
            print(f"  Total: {total_year}")
            print(f"  Missing Abstract: {data['missing_abstract']}/{total_year} ({data['missing_abstract']/total_year*100:.1f}%)")
            print(f"  Missing Affiliations: {data['missing_affiliations']}/{total_year} ({data['missing_affiliations']/total_year*100:.1f}%)")
            print(f"  Missing PDF: {data['missing_pdf']}/{total_year} ({data['missing_pdf']/total_year*100:.1f}%)")
            print(f"  Has DOI: {data['has_doi']}/{total_year} ({data['has_doi']/total_year*100:.1f}%)")
        
        print("\n" + "=" * 80)
    
    def save_analysis(self, filename: str, analysis: Dict):
        """Save analysis to JSON file."""
        with open(filename, 'w') as f:
            json.dump(analysis, f, indent=2)
