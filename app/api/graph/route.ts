import { NextRequest, NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';
import * as readline from 'readline';

const DATA_FILE = path.join(process.cwd(), 'data/processed_graph.json');

const METADATA_FILE = path.join(process.cwd(), 'data/metadata.json');
const SUMMARY_FILE = path.join(process.cwd(), 'filtered_papers_summary.json');
const PREVIEW_FILE = path.join(process.cwd(), 'public/data/graph_preview.json');

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

function getSummaryGraph() {
  const content = fs.readFileSync(SUMMARY_FILE, 'utf-8');
  const summary = JSON.parse(content);
  const distribution = summary.distribution_per_year || {};
  const years = Object.keys(distribution).map(Number).sort((a, b) => a - b);
  const minCount = Math.min(...years.map((year) => distribution[String(year)]));
  const maxCount = Math.max(...years.map((year) => distribution[String(year)]));

  const nodes = years.map((year) => {
    const count = distribution[String(year)];
    const normalized = maxCount === minCount ? 1 : (count - minCount) / (maxCount - minCount);
    return {
      paper_id: `year_${year}`,
      title: `${count.toLocaleString()} papers published in ${year}`,
      year,
      cited_by_count: count,
      field_of_study: 'All fields',
      cluster_id: Math.floor((year - years[0]) / 5),
      in_degree: year === years[0] ? 0 : 1,
      out_degree: year === years[years.length - 1] ? 0 : 1,
      keywords: ['yearly distribution', 'filtered papers'],
      abstract: `This node represents all ${count.toLocaleString()} filtered papers available in the project summary for ${year}. Individual paper records are not included in this workspace yet.`,
      x: (year - years[0]) * 8,
      y: (0.5 - normalized) * 80
    };
  });

  const edges = years.slice(1).map((year, index) => ({
    source: `year_${years[index]}`,
    target: `year_${year}`
  }));

  const clusters = years.reduce((acc: { [key: string]: any }, year) => {
    const clusterId = Math.floor((year - years[0]) / 5);
    acc[String(clusterId)] = acc[String(clusterId)] || { id: clusterId, size: 0 };
    acc[String(clusterId)].size += 1;
    return acc;
  }, {});

  return {
    nodes,
    edges,
    clusters,
    statistics: {
      total_nodes: summary.total_filtered_papers,
      total_edges: edges.length,
      total_clusters: Object.keys(clusters).length,
      visible_nodes: nodes.length,
      source: 'filtered_papers_summary.json',
      note: 'Showing all available summary data grouped by year. Upload or generate public/data/processed_graph.json to visualize individual papers.'
    }
  };
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const type = searchParams.get('type') || 'graph';

  try {
    if ((type === 'graph' || type === 'sample') && fs.existsSync(PREVIEW_FILE)) {
      return NextResponse.json(JSON.parse(fs.readFileSync(PREVIEW_FILE, 'utf-8')));
    }

    if (type === 'sample') {
      return NextResponse.json(getSummaryGraph());
    }

    if (!fs.existsSync(DATA_FILE)) {
      return NextResponse.json(getSummaryGraph());
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
      valid_types: ['graph', 'sample', 'metadata', 'info']
    }, { status: 400 });

  } catch (error) {
    console.error('Error in graph API:', error);
    return NextResponse.json(
      { error: 'Failed to read graph data', details: String(error) },
      { status: 500 }
    );
  }
}
