import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

interface GraphData {
  nodes: Array<{
    id: string;
    title: string;
    authors: string[];
    year: number | null;
    abstract: string;
    citations_count: number;
    community: number | null;
    x: number | null;
    y: number | null;
  }>;
}

let cachedGraphData: GraphData | null = null;

function loadGraphData(): GraphData {
  if (cachedGraphData) return cachedGraphData;

  const graphDataPath = path.join(process.cwd(), 'public/data/graph_data.json');

  if (!fs.existsSync(graphDataPath)) {
    throw new Error('Graph data not found at ' + graphDataPath);
  }

  const data = JSON.parse(fs.readFileSync(graphDataPath, 'utf-8'));
  cachedGraphData = data;
  return data;
}

/**
 * GET /api/graph/nodes?search=query&community=5&year_min=2020&year_max=2024
 * 
 * Search and filter nodes with optional query, community, and year filters.
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const search = searchParams.get('search')?.toLowerCase() || '';
    const community = searchParams.get('community') ? Number(searchParams.get('community')) : null;
    const yearMin = searchParams.get('year_min') ? Number(searchParams.get('year_min')) : null;
    const yearMax = searchParams.get('year_max') ? Number(searchParams.get('year_max')) : null;
    const limit = searchParams.get('limit') ? Number(searchParams.get('limit')) : 100;

    const graphData = loadGraphData();

    let results = graphData.nodes;

    // Apply filters
    if (search) {
      results = results.filter(
        (node) =>
          node.title.toLowerCase().includes(search) ||
          node.authors.some((author) => author.toLowerCase().includes(search))
      );
    }

    if (community !== null) {
      results = results.filter((node) => node.community === community);
    }

    if (yearMin !== null) {
      results = results.filter((node) => node.year === null || node.year >= yearMin);
    }

    if (yearMax !== null) {
      results = results.filter((node) => node.year === null || node.year <= yearMax);
    }

    // Limit results
    results = results.slice(0, limit);

    const headers = {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=300', // Cache for 5 minutes
    };

    return NextResponse.json(
      {
        total: results.length,
        nodes: results,
      },
      { headers }
    );
  } catch (error) {
    console.error('Error searching nodes:', error);
    return NextResponse.json(
      {
        error: 'Failed to search nodes',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
