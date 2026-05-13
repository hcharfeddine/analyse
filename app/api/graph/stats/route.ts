import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

/**
 * GET /api/graph/stats
 * 
 * Get overall network statistics and metadata.
 */
export async function GET(request: NextRequest) {
  try {
    const graphDataPath = path.join(process.cwd(), 'public/data/graph_data.json');

    if (!fs.existsSync(graphDataPath)) {
      return NextResponse.json(
        {
          error: 'Graph data not found',
        },
        { status: 404 }
      );
    }

    const graphData = JSON.parse(fs.readFileSync(graphDataPath, 'utf-8'));

    // Calculate statistics
    const yearCounts: Record<number, number> = {};
    const communitySizes: Record<string, number> = {};
    let minYear = Infinity;
    let maxYear = -Infinity;
    let totalCitations = 0;
    let maxCitations = 0;

    for (const node of graphData.nodes) {
      // Year statistics
      if (node.year !== null) {
        yearCounts[node.year] = (yearCounts[node.year] || 0) + 1;
        minYear = Math.min(minYear, node.year);
        maxYear = Math.max(maxYear, node.year);
      }

      // Community statistics
      if (node.community !== null) {
        const commKey = String(node.community);
        communitySizes[commKey] = (communitySizes[commKey] || 0) + 1;
      }

      // Citation statistics
      totalCitations += node.citations_count || 0;
      maxCitations = Math.max(maxCitations, node.citations_count || 0);
    }

    // Find most cited papers
    const topCited = [...graphData.nodes]
      .sort((a, b) => (b.citations_count || 0) - (a.citations_count || 0))
      .slice(0, 10);

    const stats = {
      metadata: graphData.metadata,
      year_range: {
        min: minYear === Infinity ? null : minYear,
        max: maxYear === -Infinity ? null : maxYear,
      },
      year_distribution: yearCounts,
      community_sizes: communitySizes,
      citation_stats: {
        total: totalCitations,
        average: graphData.nodes.length > 0 ? totalCitations / graphData.nodes.length : 0,
        max: maxCitations,
      },
      top_cited_papers: topCited,
    };

    const headers = {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=3600', // Cache for 1 hour
    };

    return NextResponse.json(stats, { headers });
  } catch (error) {
    console.error('Error calculating stats:', error);
    return NextResponse.json(
      {
        error: 'Failed to calculate statistics',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
