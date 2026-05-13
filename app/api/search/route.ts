import { NextRequest, NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';

interface Node {
  paper_id: string;
  title: string;
  abstract: string;
  keywords: string[];
  authors: Array<{ author_id: string }>;
  year: number;
  field_of_study: string;
  cited_by_count: number;
}

const SUMMARY_FILE = path.join(process.cwd(), 'filtered_papers_summary.json');
const PREVIEW_FILE = path.join(process.cwd(), 'public/data/graph_preview.json');

function loadSearchNodes(): Node[] {
  if (fs.existsSync(PREVIEW_FILE)) {
    const preview = JSON.parse(fs.readFileSync(PREVIEW_FILE, 'utf-8'));
    return preview.nodes || [];
  }

  const content = fs.readFileSync(SUMMARY_FILE, 'utf-8');
  const summary = JSON.parse(content);
  const distribution = summary.distribution_per_year || {};
  return Object.keys(distribution).map((year) => ({
    paper_id: `year_${year}`,
    title: `${Number(distribution[year]).toLocaleString()} papers published in ${year}`,
    abstract: `Summary record for all filtered papers available in ${year}.`,
    keywords: ['yearly distribution', 'filtered papers'],
    authors: [],
    year: Number(year),
    field_of_study: 'All fields',
    cited_by_count: Number(distribution[year])
  }));
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { query } = body;

    if (!query || typeof query !== 'string' || query.trim().length === 0) {
      return NextResponse.json({ results: [] });
    }

    const searchQuery = query.toLowerCase().trim();

    const results = loadSearchNodes()
      .filter((node: Node) => {
        const title = node.title?.toLowerCase() || '';
        const abstract = node.abstract?.toLowerCase() || '';
        const keywords = (node.keywords || []).map((k: string) => k.toLowerCase()).join(' ');

        return (
          title.includes(searchQuery) ||
          abstract.includes(searchQuery) ||
          keywords.includes(searchQuery)
        );
      })
      .slice(0, 50)
      .map((node: Node) => ({
        paper_id: node.paper_id,
        title: node.title,
        year: node.year,
        field_of_study: node.field_of_study,
        cited_by_count: node.cited_by_count,
        authors: node.authors,
      }));

    return NextResponse.json({ results, note: fs.existsSync(PREVIEW_FILE) ? 'Searching indexed preview data.' : 'Searching available year-level summary data. Individual paper search requires processed graph data.' });
  } catch (err) {
    console.error('[v0] Search error:', err);
    return NextResponse.json(
      { error: 'Search failed', results: [] },
      { status: 500 }
    );
  }
}
