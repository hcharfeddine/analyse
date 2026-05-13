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
  edges: Array<{
    source: number;
    target: number;
  }>;
  communities: Record<string, { name: string; color: string }>;
}

let cachedGraphData: GraphData | null = null;

function loadGraphData(): GraphData {
  if (cachedGraphData) return cachedGraphData;

  const graphDataPath = path.join(process.cwd(), 'public/data/graph_data.json');

  if (!fs.existsSync(graphDataPath)) {
    throw new Error('Graph data not found');
  }

  const data = JSON.parse(fs.readFileSync(graphDataPath, 'utf-8'));
  cachedGraphData = data;
  return data;
}

/**
 * GET /api/graph/nodes/[id]
 * 
 * Get a single node by paper ID with full metadata and connected papers.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const paperId = params.id;
    const graphData = loadGraphData();

    // Find the node
    const nodeIndex = graphData.nodes.findIndex((n) => n.id === paperId);

    if (nodeIndex === -1) {
      return NextResponse.json(
        {
          error: 'Paper not found',
          paperId,
        },
        { status: 404 }
      );
    }

    const node = graphData.nodes[nodeIndex];

    // Find connected papers
    const citedBy = graphData.edges
      .filter((e) => e.target === nodeIndex)
      .map((e) => graphData.nodes[e.source]);

    const cites = graphData.edges
      .filter((e) => e.source === nodeIndex)
      .map((e) => graphData.nodes[e.target]);

    const communityInfo = node.community !== null
      ? graphData.communities[String(node.community)]
      : null;

    const headers = {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=600', // Cache for 10 minutes
    };

    return NextResponse.json(
      {
        node: {
          ...node,
          community_info: communityInfo,
        },
        connections: {
          cited_by: citedBy.slice(0, 50), // Limit to 50
          cites: cites.slice(0, 50),
        },
      },
      { headers }
    );
  } catch (error) {
    console.error('Error fetching node:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch node',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
