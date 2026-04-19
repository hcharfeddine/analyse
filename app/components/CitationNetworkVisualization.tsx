'use client';

import React, { useEffect, useRef, useState } from 'react';
import Sigma from 'sigma';
import { Graph } from 'graphology';
import { GraphSkeleton, ErrorState } from './LoadingStates';

interface Node {
  paper_id: string;
  title: string;
  year: number;
  cited_by_count: number;
  field_of_study: string;
  cluster_id: number;
  in_degree: number;
  out_degree: number;
  [key: string]: any;
}

interface Edge {
  source: string;
  target: string;
}

interface GraphData {
  nodes: Node[];
  edges: Edge[];
  clusters: Record<number, any>;
  statistics: any;
}

interface Props {
  selectedPaperId: string | null;
  onSelectPaper: (paperId: string) => void;
  searchQuery: string;
  yearRange: [number, number];
  selectedClusters: number[];
}

const CitationNetworkVisualization: React.FC<Props> = ({
  selectedPaperId,
  onSelectPaper,
  searchQuery,
  yearRange,
  selectedClusters,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<any>(null);

  // Load and initialize graph
  useEffect(() => {
    const loadGraph = async () => {
      try {
        setIsLoading(true);
        
        // Fetch graph data from API (sample to avoid memory issues)
        const response = await fetch('/api/graph?type=sample');
        
        if (!response.ok) {
          throw new Error('Failed to load graph data');
        }

        const data: GraphData = await response.json();
        console.log('[v0] Loaded graph sample:', {
          nodes: data.nodes.length,
          edges: data.edges.length,
          clusters: Object.keys(data.clusters).length,
        });

        // Create Graphology graph
        const graph = new Graph();
        
        // Add nodes
        const colorMap = generateColorMap(Object.keys(data.clusters).length);
        
        data.nodes.forEach((node) => {
          const clusterColor = colorMap[node.cluster_id] || '#475569';
          const size = Math.log(node.cited_by_count + 1) * 3 + 5; // Log scale for size
          
          graph.addNode(node.paper_id, {
            label: node.title,
            x: Math.random() * 100,
            y: Math.random() * 100,
            size,
            color: clusterColor,
            data: node,
          });
        });

        // Add edges
        data.edges.forEach((edge) => {
          if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
            graph.addEdge(edge.source, edge.target);
          }
        });

        graphRef.current = graph;
        setStats(data.statistics);
        setIsLoading(false);
        setError(null);
      } catch (err) {
        console.error('[v0] Error loading graph:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
        setIsLoading(false);
      }
    };

    loadGraph();
  }, []);

  // Initialize Sigma and render
  useEffect(() => {
    if (!containerRef.current || !graphRef.current || isLoading) return;

    try {
      // Clear previous instance
      if (sigmaRef.current) {
        sigmaRef.current.kill();
      }

      const sigma = new Sigma(graphRef.current, containerRef.current, {
        renderLabels: true,
        enableEdgeClickEvents: true,
        enableEdgeWheelEvents: true,
        enableEdgeDragEvents: true,
        enableNodeClickEvents: true,
        enableNodeDragEvents: true,
        enableNodeWheelEvents: true,
        renderEdgeLabels: false,
        defaultNodeColor: '#475569',
        defaultEdgeColor: 'rgba(255, 255, 255, 0.05)',
        labelFont: 'Space Mono',
        labelColor: { color: '#94a3b8' },
        labelSize: 11,
      });

      sigmaRef.current = sigma;

      // Handle node click
      sigma.on('clickNode', ({ node }) => {
        onSelectPaper(node);
      });

      // Handle canvas click (deselect)
      sigma.on('clickStage', () => {
        // onSelectPaper(null); // Optional: uncomment to deselect on canvas click
      });

      console.log('[v0] Sigma initialized with', graphRef.current.order, 'nodes');
    } catch (err) {
      console.error('[v0] Error initializing Sigma:', err);
      setError(err instanceof Error ? err.message : 'Error initializing visualization');
    }

    return () => {
      if (sigmaRef.current) {
        sigmaRef.current.kill();
        sigmaRef.current = null;
      }
    };
  }, [isLoading, onSelectPaper]);

  // Apply filters (search, year range, clusters)
  useEffect(() => {
    if (!sigmaRef.current || !graphRef.current) return;

    const graph = graphRef.current;
    const sigma = sigmaRef.current;

    // Filter nodes based on criteria
    graph.nodes().forEach((nodeId) => {
      const node = graph.getNodeAttributes(nodeId);
      const nodeData = node.data as Node;

      let visible = true;

      // Year filter
      if (nodeData.year && (nodeData.year < yearRange[0] || nodeData.year > yearRange[1])) {
        visible = false;
      }

      // Cluster filter
      if (selectedClusters.length > 0 && !selectedClusters.includes(nodeData.cluster_id)) {
        visible = false;
      }

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const title = nodeData.title?.toLowerCase() || '';
        const abstract = nodeData.abstract?.toLowerCase() || '';
        const keywords = (nodeData.keywords || []).map((k: string) => k.toLowerCase()).join(' ');
        
        if (!title.includes(query) && !abstract.includes(query) && !keywords.includes(query)) {
          visible = false;
        }
      }

      // Highlight selected paper — use graph not sigma (Sigma v3 API)
      if (selectedPaperId && nodeId === selectedPaperId) {
        graph.setNodeAttribute(nodeId, 'highlighted', true);
        graph.setNodeAttribute(nodeId, 'size', (node.size || 10) * 2);
      } else {
        graph.setNodeAttribute(nodeId, 'highlighted', false);
        graph.setNodeAttribute(nodeId, 'size', node.data?.size || 10);
      }

      graph.setNodeAttribute(nodeId, 'hidden', !visible);
    });
  }, [searchQuery, yearRange, selectedClusters, selectedPaperId]);

  // Render loading state
  if (isLoading) {
    return <GraphSkeleton />;
  }

  // Render error state
  if (error) {
    return <ErrorState error={error} onRetry={() => window.location.reload()} />;
  }

  return (
    <div className="w-full h-full flex flex-col relative">
      {/* Header with stats */}
      <div className="absolute top-6 left-6 right-6 z-10 pointer-events-none flex justify-between items-start">
        <div className="bg-black/50 backdrop-blur-md border border-white/10 rounded-lg p-3 pointer-events-auto shadow-2xl">
          {stats && (
            <div className="flex items-center gap-6">
              <div>
                <p className="text-[10px] text-muted uppercase tracking-widest mono-text mb-0.5">Nodes</p>
                <p className="text-sm text-white font-medium mono-text">{stats.total_nodes?.toLocaleString() || '?'}</p>
              </div>
              <div className="w-px h-8 bg-white/10"></div>
              <div>
                <p className="text-[10px] text-muted uppercase tracking-widest mono-text mb-0.5">Edges</p>
                <p className="text-sm text-white font-medium mono-text">{stats.total_edges?.toLocaleString() || '?'}</p>
              </div>
              <div className="w-px h-8 bg-white/10"></div>
              <div>
                <p className="text-[10px] text-muted uppercase tracking-widest mono-text mb-0.5">Clusters</p>
                <p className="text-sm text-white font-medium mono-text">{stats.total_clusters || '?'}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Visualization container */}
      <div ref={containerRef} className="flex-1 bg-transparent" />
      
      {/* Subtle grid background overlay */}
      <div className="absolute inset-0 pointer-events-none opacity-5 -z-10" 
           style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)', backgroundSize: '50px 50px' }}>
      </div>
    </div>
  );
};

// Generate distinct vibrant colors for clusters
function generateColorMap(clusterCount: number): Record<number, string> {
  const colors = [
    '#3b82f6', // blue
    '#8b5cf6', // purple
    '#ec4899', // pink
    '#06b6d4', // cyan
    '#10b981', // green
    '#f59e0b', // amber
    '#ef4444', // red
    '#14b8a6', // teal
    '#f97316', // orange
    '#6366f1', // indigo
    '#84cc16', // lime
    '#d946ef', // fuchsia
  ];

  const colorMap: Record<number, string> = {};
  for (let i = 0; i < clusterCount; i++) {
    colorMap[i] = colors[i % colors.length];
  }
  return colorMap;
}

export default CitationNetworkVisualization;
