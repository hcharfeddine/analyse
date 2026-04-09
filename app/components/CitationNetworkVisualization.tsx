'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import Sigma from 'sigma';
import { Graph } from 'graphology';

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
        
        // Fetch graph data
        const response = await fetch('/data/processed_graph.json', {
          cache: 'force-cache',
        });
        
        if (!response.ok) {
          throw new Error('Failed to load graph data');
        }

        const data: GraphData = await response.json();
        console.log('[v0] Loaded graph data:', {
          nodes: data.nodes.length,
          edges: data.edges.length,
          clusters: Object.keys(data.clusters).length,
        });

        // Create Graphology graph
        const graph = new Graph();
        
        // Add nodes
        const colorMap = generateColorMap(Object.keys(data.clusters).length);
        
        data.nodes.forEach((node) => {
          const clusterColor = colorMap[node.cluster_id] || '#999999';
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
        defaultNodeColor: '#999999',
        defaultEdgeColor: 'rgba(200, 200, 200, 0.5)',
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

      // Highlight selected paper
      if (selectedPaperId && nodeId === selectedPaperId) {
        sigma.setNodeAttribute(nodeId, 'highlighted', true);
        sigma.setNodeAttribute(nodeId, 'size', (node.size || 10) * 2);
      } else {
        sigma.setNodeAttribute(nodeId, 'highlighted', false);
        sigma.setNodeAttribute(nodeId, 'size', node.data?.size || 10);
      }

      sigma.setNodeAttribute(nodeId, 'hidden', !visible);
    });
  }, [searchQuery, yearRange, selectedClusters, selectedPaperId]);

  // Render loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center w-full h-full bg-muted/10">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted">Loading citation network...</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="flex items-center justify-center w-full h-full bg-red-50 dark:bg-red-950">
        <div className="text-center p-6">
          <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">Error</h3>
          <p className="text-red-700 dark:text-red-200">{error}</p>
          <p className="text-sm text-red-600 dark:text-red-300 mt-4">
            Make sure to run the data extraction and processing scripts first.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col">
      {/* Header with stats */}
      <div className="border-b border-border bg-background px-4 py-3 flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold">Citation Network Visualization</h2>
          {stats && (
            <p className="text-sm text-muted">
              {stats.total_nodes?.toLocaleString() || '?'} papers •{' '}
              {stats.total_edges?.toLocaleString() || '?'} citations •{' '}
              {stats.total_clusters || '?'} research clusters
            </p>
          )}
        </div>
      </div>

      {/* Visualization container */}
      <div ref={containerRef} className="flex-1 bg-white dark:bg-gray-900" />
    </div>
  );
};

// Generate distinct colors for clusters
function generateColorMap(clusterCount: number): Record<number, string> {
  const colors = [
    '#3b82f6', // blue
    '#ef4444', // red
    '#10b981', // green
    '#f59e0b', // amber
    '#8b5cf6', // purple
    '#ec4899', // pink
    '#06b6d4', // cyan
    '#14b8a6', // teal
    '#f97316', // orange
    '#6366f1', // indigo
    '#84cc16', // lime
    '#0d9488', // teal-600
    '#d946ef', // fuchsia
    '#ea580c', // orange-600
    '#7c2d12', // orange-900
  ];

  const colorMap: Record<number, string> = {};
  for (let i = 0; i < clusterCount; i++) {
    colorMap[i] = colors[i % colors.length];
  }
  return colorMap;
}

export default CitationNetworkVisualization;
