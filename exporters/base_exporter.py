"""
Data export utilities for academic papers.
"""

import csv
import json
import html
import logging
import os
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from models.paper import Paper
from utils.exceptions import ExportException


class BaseExporter:
    def __init__(self, filename: str):
        self.filename = filename
    
    def export(self, data: Any):
        raise NotImplementedError


class CSVExporter(BaseExporter):
    def export(self, data: List[Paper]):
        try:
            with open(self.filename, 'w', newline='', encoding='utf-8') as f:
                if data:
                    # Filter data to exclude unwanted fields during CSV export if any were missed
                    rows = [p.to_dict() for p in data]
                    fieldnames = rows[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
        except Exception as e:
            raise ExportException(f"Failed to export CSV: {e}")


class JSONExporter(BaseExporter):
    @staticmethod
    def _json_serializer(obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        return str(obj)
    
    def export(self, data: Dict):
        try:
            papers_by_year = defaultdict(list)
            for keyword, years_data in data.items():
                for year, papers in years_data.items():
                    papers_by_year[year].extend(papers)
            
            base_dir = os.path.dirname(self.filename)
            base_name = os.path.splitext(os.path.basename(self.filename))[0]
            
            for year, papers in papers_by_year.items():
                year_filename = os.path.join(base_dir, f"{base_name}_{year}.json")
                serializable_data = [p.to_dict() if hasattr(p, 'to_dict') else p for p in papers]
                
                with open(year_filename, 'w', encoding='utf-8', newline='\n') as f:
                    json.dump(serializable_data, f, indent=2, ensure_ascii=False, default=self._json_serializer)
                
                logger.info(f"Successfully exported JSON for year {year} to {year_filename}")
        except Exception as e:
            raise ExportException(f"Failed to export JSON: {e}")


class PDFExporter(BaseExporter):
    @staticmethod
    def _sanitize_html(text: str) -> str:
        if not text: return ""
        return html.escape(str(text), quote=True).replace('\n', '<br>')
    
    def export(self, data: Dict, stats: Dict = None):
        try:
            doc = SimpleDocTemplate(self.filename, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            elements.append(Paragraph("<b>Academic Papers Collection</b>", styles['Title']))
            elements.append(Spacer(1, 12))
            
            for keyword, years_data in data.items():
                for year, papers in years_data.items():
                    elements.append(Paragraph(f"<b>Year: {year}</b>", styles['Heading2']))
                    for i, paper in enumerate(papers, 1):
                        p_dict = paper.to_dict() if hasattr(paper, 'to_dict') else paper
                        elements.append(Paragraph(f"{i}. {self._sanitize_html(p_dict.get('title'))}", styles['Normal']))
            doc.build(elements)
        except Exception as e:
            raise ExportException(f"Failed to export PDF: {e}")
