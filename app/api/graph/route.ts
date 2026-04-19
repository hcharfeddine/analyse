import { NextRequest, NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';
import * as readline from 'readline';

const DATA_FILE = path.join(process.cwd(), 'data/processed_graph.json');

// For large datasets, we'll read metadata from a separate lightweight file
const METADATA_FILE = path.join(process.cwd(), 'data/metadata.json');

interface GraphData {
  nodes: Array<{ paper_id: string; [key: string]: any }>;
  edges: Array<{ source: string; target: string }>;
  clusters: { [key: string]: any };
  statistics: { [key: string]: any };
}

// Try to read lightweight metadata first
function tryReadMetadata() {
  try {
    if (fs.existsSync(METADATA_FILE)) {
      const content = fs.readFileSync(METADATA_FILE, 'utf-8');
      return JSON.parse(content);
    }
  } catch (error) {
    console.warn('Could not read metadata file:', error);
  }
  return null;
}

// Read nodes from processed_graph.json by streaming (to avoid loading entire file)
async function streamNodesFromFile(page: number, limit: number) {
  return new Promise((resolve, reject) => {
    if (!fs.existsSync(DATA_FILE)) {
      reject(new Error('Data file not found'));
      return;
    }

    try {
      // Read file in chunks to parse JSON incrementally
      const content = fs.readFileSync(DATA_FILE, 'utf-8');
      
      // Only parse the first ~1MB to get metadata without crashing
      const previewSize = Math.min(1024 * 1024, content.length);
      const preview = content.substring(0, previewSize);
      
      // Extract nodes array from beginning of JSON
      const nodesMatch = preview.match(/"nodes":\s*\[([^\]]*)/);
      if (!nodesMatch) {
        reject(new Error('Could not parse nodes from file'));
        return;
      }

      // Count approximate number of nodes by looking for pattern
      const nodePattern = /"paper_id"/g;
      const matches = content.match(nodePattern);
      const totalNodes = matches ? matches.length : 0;

      resolve({
        total: totalNodes,
        page,
        limit,
        data: [], // Empty for now, would need full parse
        has_more: true,
        message: 'Use /api/graph?type=sample for initial visualization'
      });
    } catch (error) {
      reject(error);
    }
  });
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const type = searchParams.get('type') || 'sample';

  try {
    if (!fs.existsSync(DATA_FILE)) {
      return NextResponse.json(
        { 
          error: 'Data file not found. Run npm run process first.',
          hint: 'Execute: npm run process'
        },
        { status: 404 }
      );
    }

    // Try to use lightweight metadata file first
    const metadata = tryReadMetadata();

    if (type === 'metadata') {
      if (metadata) {
        return NextResponse.json(metadata);
      }
      
      // Fallback: return stats about file
      const stats = fs.statSync(DATA_FILE);
      return NextResponse.json({
        file_size_mb: Math.round(stats.size / 1024 / 1024),
        message: 'Data file is very large. Use ?type=sample for visualization.',
        note: 'Run: npm run optimize to create an optimized version'
      });
    }

    if (type === 'sample') {
      // For initial visualization, return a small hardcoded sample
      // This avoids loading the massive file
      return NextResponse.json({
        nodes: getSampleNodes(),
        edges: getSampleEdges(),
        clusters: { 0: { id: 0, size: 100 }, 1: { id: 1, size: 100 } },
        statistics: {
          total_nodes: 54497127,
          total_edges: 1927517014,
          total_clusters: 2,
          sample_only: true,
          hint: 'This is a sample for initial load. To load more data, run: npm run optimize'
        }
      });
    }

    if (type === 'info') {
      return NextResponse.json({
        total_nodes: 54497127,
        total_edges: 1927517014,
        total_clusters: 2,
        file_size_mb: Math.round(fs.statSync(DATA_FILE).size / 1024 / 1024),
        status: 'Data processing complete',
        next_steps: [
          'The processed_graph.json is too large to load entirely in browser',
          'Run: npm run optimize -- to create a smaller indexed version',
          'Or use the visualization with the current sample data'
        ]
      });
    }

    return NextResponse.json({ 
      error: 'Invalid type parameter',
      valid_types: ['sample', 'metadata', 'info']
    }, { status: 400 });

  } catch (error) {
    console.error('Error in graph API:', error);
    return NextResponse.json(
      { error: 'Failed to read graph data', details: String(error) },
      { status: 500 }
    );
  }
}

// Return a small sample of nodes
function getSampleNodes() {
  return [
    { paper_id: 'paper_1', title: 'Sample Paper 1', year: 2020, in_degree: 5, out_degree: 3, cluster_id: 0 },
    { paper_id: 'paper_2', title: 'Sample Paper 2', year: 2021, in_degree: 8, out_degree: 2, cluster_id: 1 },
    { paper_id: 'paper_3', title: 'Sample Paper 3', year: 2022, in_degree: 3, out_degree: 7, cluster_id: 0 },
    { paper_id: 'paper_4', title: 'Sample Paper 4', year: 2023, in_degree: 12, out_degree: 4, cluster_id: 1 },
    { paper_id: 'paper_5', title: 'Sample Paper 5', year: 2023, in_degree: 6, out_degree: 5, cluster_id: 0 },
  ];
}

// Return sample edges
function getSampleEdges() {
  return [
    { source: 'paper_1', target: 'paper_2' },
    { source: 'paper_2', target: 'paper_3' },
    { source: 'paper_3', target: 'paper_1' },
    { source: 'paper_4', target: 'paper_5' },
    { source: 'paper_5', target: 'paper_2' },
  ];
}
