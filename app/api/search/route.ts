import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

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

interface SearchIndex {
  [key: string]: string[];
}

let graphCache: { nodes: Node[] } | null = null;
let searchIndexCache: SearchIndex | null = null;

async function loadGraphData() {
  if (graphCache) return graphCache;

  try {
    const graphPath = path.join(process.cwd(), 'public/data/processed_graph.json');
    const data = JSON.parse(fs.readFileSync(graphPath, 'utf-8'));
    graphCache = data;
    return data;
  } catch (err) {
    console.error('[v0] Error loading graph data:', err);
    throw new Error('Failed to load graph data');
  }
}

async function loadSearchIndex() {
  if (searchIndexCache) return searchIndexCache;

  try {
    const indexPath = path.join(process.cwd(), 'public/data/search_index.json');
    const data = JSON.parse(fs.readFileSync(indexPath, 'utf-8'));
    searchIndexCache = data;
    return data;
  } catch (err) {
    console.error('[v0] Error loading search index:', err);
    return {};
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { query } = body;

    if (!query || typeof query !== 'string' || query.trim().length === 0) {
      return NextResponse.json({ results: [] });
    }

    const graphData = await loadGraphData();
    const searchQuery = query.toLowerCase().trim();

    // Simple search: find papers matching the query
    const results = graphData.nodes
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
      .slice(0, 50) // Limit to 50 results
      .map((node: Node) => ({
        paper_id: node.paper_id,
        title: node.title,
        year: node.year,
        field_of_study: node.field_of_study,
        cited_by_count: node.cited_by_count,
        authors: node.authors,
      }));

    return NextResponse.json({ results });
  } catch (err) {
    console.error('[v0] Search error:', err);
    return NextResponse.json(
      { error: 'Search failed' },
      { status: 500 }
    );
  }
}
