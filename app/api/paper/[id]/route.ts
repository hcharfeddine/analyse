import { NextRequest, NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';

const SUMMARY_FILE = path.join(process.cwd(), 'filtered_papers_summary.json');
const PREVIEW_FILE = path.join(process.cwd(), 'public/data/graph_preview.json');

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: paperId } = await params;

  try {
    if (fs.existsSync(PREVIEW_FILE)) {
      const preview = JSON.parse(fs.readFileSync(PREVIEW_FILE, 'utf-8'));
      const previewPaper = (preview.nodes || []).find((node: any) => node.paper_id === paperId);
      if (previewPaper) {
        return NextResponse.json({
          paper: {
            authors: [],
            doi: '',
            publisher: '',
            publication_type: 'paper',
            journal_name: '',
            venue: '',
            pdf_url: '',
            ...previewPaper,
            keywords: previewPaper.keywords || [],
            abstract: previewPaper.abstract || 'This paper is from the generated preview index. Full details can be queried from graph_index.db.'
          }
        });
      }
    }

    const yearMatch = paperId.match(/^year_(\d{4})$/);
    const summary = JSON.parse(fs.readFileSync(SUMMARY_FILE, 'utf-8'));
    const distribution = summary.distribution_per_year || {};
    const year = yearMatch?.[1];
    const count = year ? distribution[year] : null;
    const paper = year && count ? {
      paper_id: paperId,
      title: `${Number(count).toLocaleString()} papers published in ${year}`,
      authors: [],
      year: Number(year),
      cited_by_count: Number(count),
      doi: '',
      publisher: '',
      abstract: `This is a year-level summary node representing all filtered papers available for ${year}. The project currently contains summary data, not the individual paper records needed to inspect one specific paper.`,
      publication_type: 'summary',
      journal_name: '',
      venue: 'Project summary dataset',
      field_of_study: 'All fields',
      keywords: ['yearly distribution', 'filtered papers'],
      pdf_url: '',
      in_degree: Number(year) > 1980 ? 1 : 0,
      out_degree: Number(year) < 2024 ? 1 : 0,
      cluster_id: Math.floor((Number(year) - 1980) / 5)
    } : null;

    if (paper) {
      return NextResponse.json({ paper });
    }

    return NextResponse.json(
      { error: 'Paper not found' },
      { status: 404 }
    );
  } catch (error) {
    console.error('Error fetching paper:', error);
    return NextResponse.json(
      { error: 'Failed to fetch paper details' },
      { status: 500 }
    );
  }
}
