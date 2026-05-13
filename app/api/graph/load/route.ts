import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

/**
 * GET /api/graph/load
 * 
 * Load the complete graph data from the GPU pipeline JSON export.
 * This endpoint returns the full graph structure including nodes, edges, and metadata.
 */
export async function GET(request: NextRequest) {
  try {
    const graphDataPath = path.join(process.cwd(), 'public/data/graph_data.json');

    // Check if file exists
    if (!fs.existsSync(graphDataPath)) {
      return NextResponse.json(
        {
          error: 'Graph data not found. Please run the GPU pipeline first.',
          path: graphDataPath,
          instructions: [
            '1. Run: python scripts/citation_network_gpu/main.py --input-dir <input_dir> --db public/data/citation_network.db',
            '2. This will generate public/data/graph_data.json',
            '3. Refresh the page to load the visualization',
          ],
        },
        { status: 404 }
      );
    }

    // Read and parse JSON
    const graphData = JSON.parse(fs.readFileSync(graphDataPath, 'utf-8'));

    // Add cache headers
    const headers = {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=3600', // Cache for 1 hour
    };

    return NextResponse.json(graphData, { headers });
  } catch (error) {
    console.error('Error loading graph data:', error);
    return NextResponse.json(
      {
        error: 'Failed to load graph data',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
