import { NextRequest, NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';

const DATA_FILE = path.join(process.cwd(), 'public/data/processed_graph.json');

// Cache metadata to avoid re-reading the file multiple times
let cachedMetadata: any = null;

function readGraphMetadata() {
  if (cachedMetadata) return cachedMetadata;
  
  try {
    if (!fs.existsSync(DATA_FILE)) {
      return { error: 'Data file not found. Run npm run process first.' };
    }

    // Read the file and extract metadata without loading all nodes/edges
    const fileSize = fs.statSync(DATA_FILE).size;
    const content = fs.readFileSync(DATA_FILE, 'utf-8');
    const data = JSON.parse(content);

    cachedMetadata = {
      statistics: data.statistics || {},
      clusters: data.clusters || {},
      total_nodes: data.nodes?.length || 0,
      total_edges: data.edges?.length || 0,
      file_size_mb: Math.round(fileSize / 1024 / 1024)
    };

    return cachedMetadata;
  } catch (error) {
    console.error('Error reading graph metadata:', error);
    return { error: 'Failed to read graph data' };
  }
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const type = searchParams.get('type') || 'metadata';
  const page = parseInt(searchParams.get('page') || '0');
  const limit = parseInt(searchParams.get('limit') || '1000');

  try {
    if (!fs.existsSync(DATA_FILE)) {
      return NextResponse.json(
        { error: 'Data file not found. Run npm run process first.' },
        { status: 404 }
      );
    }

    const content = fs.readFileSync(DATA_FILE, 'utf-8');
    const data = JSON.parse(content);

    if (type === 'metadata') {
      return NextResponse.json({
        statistics: data.statistics || {},
        clusters: data.clusters || {},
        total_nodes: data.nodes?.length || 0,
        total_edges: data.edges?.length || 0
      });
    }

    if (type === 'nodes') {
      const nodes = data.nodes || [];
      const start = page * limit;
      const end = start + limit;
      const paginatedNodes = nodes.slice(start, end);

      return NextResponse.json({
        data: paginatedNodes,
        page,
        limit,
        total: nodes.length,
        has_more: end < nodes.length
      });
    }

    if (type === 'edges') {
      const edges = data.edges || [];
      const start = page * limit;
      const end = start + limit;
      const paginatedEdges = edges.slice(start, end);

      return NextResponse.json({
        data: paginatedEdges,
        page,
        limit,
        total: edges.length,
        has_more: end < edges.length
      });
    }

    if (type === 'sample') {
      // Return a small sample for initial visualization
      const nodes = (data.nodes || []).slice(0, 500);
      const nodeIds = new Set(nodes.map((n: any) => n.paper_id));
      const edges = (data.edges || [])
        .filter((e: any) => nodeIds.has(e.source) && nodeIds.has(e.target))
        .slice(0, 2000);

      return NextResponse.json({
        nodes,
        edges,
        clusters: data.clusters || {},
        statistics: data.statistics || {}
      });
    }

    return NextResponse.json({ error: 'Invalid type parameter' }, { status: 400 });
  } catch (error) {
    console.error('Error in graph API:', error);
    return NextResponse.json(
      { error: 'Failed to read graph data' },
      { status: 500 }
    );
  }
}
