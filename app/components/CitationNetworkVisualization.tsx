'use client';

import React, { useEffect, useRef, useState } from 'react';
import Sigma from 'sigma';
import { Graph } from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import circular from 'graphology-layout/circular';
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
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [useFallbackRenderer, setUseFallbackRenderer] = useState(false);

  // Load and initialize graph
  useEffect(() => {
    const loadGraph = async () => {
      try {
        setIsLoading(true);
        
        const response = await fetch('/api/graph');
        
        if (!response.ok) {
          throw new Error('Failed to load graph data');
        }

        const data: GraphData = await response.json();
        setGraphData(data);
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
          const clusterColor = colorMap[node.cluster_id] || '#64748b';
          const weight = (node.cited_by_count || 0) + (node.in_degree || 0) + (node.out_degree || 0);
          const size = Math.max(2, Math.min(12, Math.log(weight + 1) * 0.9 + 2));

          graph.addNode(node.paper_id, {
            label: node.title,
            x: typeof node.x === 'number' ? node.x : Math.random(),
            y: typeof node.y === 'number' ? node.y : Math.random(),
            size,
            baseSize: size,
            color: clusterColor,
            data: node,
          });
        });

        // Add edges with subtle styling
        data.edges.forEach((edge) => {
          if (
            graph.hasNode(edge.source) &&
            graph.hasNode(edge.target) &&
            !graph.hasEdge(edge.source, edge.target)
          ) {
            graph.addEdge(edge.source, edge.target, {
              size: 0.4,
              color: 'rgba(148, 163, 184, 0.55)',
            });
          }
        });

        // Compute a real network layout so nodes cluster and edges form readable lines
        if (graph.order > 0 && graph.size > 0) {
          circular.assign(graph, { scale: 100 });
          const settings = forceAtlas2.inferSettings(graph);
          const iterations =
            graph.order > 5000 ? 200 : graph.order > 2000 ? 350 : graph.order > 500 ? 500 : 700;
          forceAtlas2.assign(graph, {
            iterations,
            settings: {
              ...settings,
              gravity: 0.5,
              scalingRatio: 20,
              slowDown: 3,
              barnesHutOptimize: graph.order > 1000,
              barnesHutTheta: 0.6,
              strongGravityMode: false,
              linLogMode: true,
              outboundAttractionDistribution: false,
              adjustSizes: false,
            },
          });
        } else if (graph.order > 0) {
          circular.assign(graph, { scale: 100 });
        }

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
        renderEdgeLabels: false,
        defaultNodeColor: '#64748b',
        defaultEdgeColor: 'rgba(148, 163, 184, 0.35)',
        labelFont: 'Inter, system-ui, sans-serif',
        labelColor: { color: '#cbd5e1' },
        labelSize: 12,
        labelWeight: '500',
        labelDensity: 0.3,
        labelGridCellSize: 120,
        labelRenderedSizeThreshold: 14,
        minCameraRatio: 0.05,
        maxCameraRatio: 8,
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
      setUseFallbackRenderer(true);
      setError(null);
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
        graph.setNodeAttribute(nodeId, 'size', (node.baseSize || node.size || 10) * 1.8);
      } else {
        graph.setNodeAttribute(nodeId, 'highlighted', false);
        graph.setNodeAttribute(nodeId, 'size', node.baseSize || 10);
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

  if (useFallbackRenderer && graphData && graphRef.current) {
    const graph = graphRef.current;
    const colorMap = generateColorMap(Object.keys(graphData.clusters).length);

    const visibleIds = new Set<string>();
    const filteredNodes = graphData.nodes.filter((node) => {
      if (node.year && (node.year < yearRange[0] || node.year > yearRange[1])) return false;
      if (selectedClusters.length > 0 && !selectedClusters.includes(node.cluster_id)) return false;
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const title = node.title?.toLowerCase() || '';
        const abstract = node.abstract?.toLowerCase() || '';
        const keywords = (node.keywords || []).map((k: string) => k.toLowerCase()).join(' ');
        if (!title.includes(query) && !abstract.includes(query) && !keywords.includes(query)) return false;
      }
      visibleIds.add(node.paper_id);
      return true;
    });

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    const positioned = filteredNodes
      .map((node) => {
        if (!graph.hasNode(node.paper_id)) return null;
        const attrs = graph.getNodeAttributes(node.paper_id);
        const x = typeof attrs.x === 'number' ? attrs.x : 0;
        const y = typeof attrs.y === 'number' ? attrs.y : 0;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
        return { node, x, y, size: attrs.baseSize || attrs.size || 6, color: colorMap[node.cluster_id] || '#64748b' };
      })
      .filter(Boolean) as { node: Node; x: number; y: number; size: number; color: string }[];

    const VIEW_W = 1000;
    const VIEW_H = 700;
    const PAD = 60;
    const spanX = Math.max(maxX - minX, 1e-6);
    const spanY = Math.max(maxY - minY, 1e-6);
    const project = (x: number, y: number) => ({
      px: PAD + ((x - minX) / spanX) * (VIEW_W - PAD * 2),
      py: PAD + ((y - minY) / spanY) * (VIEW_H - PAD * 2),
    });

    const projectedById = new Map<string, { px: number; py: number; size: number; color: string }>();
    for (const item of positioned) {
      const { px, py } = project(item.x, item.y);
      projectedById.set(item.node.paper_id, { px, py, size: item.size, color: item.color });
    }

    const edgeLines = graphData.edges
      .filter((e) => projectedById.has(e.source) && projectedById.has(e.target))
      .slice(0, 6000);

    return (
      <div className="w-full h-full flex flex-col relative overflow-hidden bg-gradient-to-br from-[#0a0e1a] via-[#0d1420] to-[#0a0e1a]">
        <div className="absolute top-6 left-6 right-6 z-10 pointer-events-none flex justify-between items-start">
          <div className="bg-black/50 backdrop-blur-md border border-white/10 rounded-lg p-3 pointer-events-auto shadow-2xl">
            {stats && (
              <div className="flex items-center gap-6">
                <div>
                  <p className="text-[10px] text-muted uppercase tracking-widest mono-text mb-0.5">Total Papers</p>
                  <p className="text-sm text-white font-medium mono-text">{stats.total_nodes?.toLocaleString() || '?'}</p>
                </div>
                <div className="w-px h-8 bg-white/10"></div>
                <div>
                  <p className="text-[10px] text-muted uppercase tracking-widest mono-text mb-0.5">Visible</p>
                  <p className="text-sm text-white font-medium mono-text">{positioned.length.toLocaleString()}</p>
                </div>
                <div className="w-px h-8 bg-white/10"></div>
                <div>
                  <p className="text-[10px] text-muted uppercase tracking-widest mono-text mb-0.5">Edges</p>
                  <p className="text-sm text-white font-medium mono-text">{edgeLines.length.toLocaleString()}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="relative flex-1 m-6 mt-24 rounded-xl border border-white/10 bg-black/30 overflow-hidden">
          <svg
            viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
            preserveAspectRatio="xMidYMid meet"
            className="w-full h-full"
          >
            <defs>
              <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="rgba(255,255,255,0.4)" />
                <stop offset="100%" stopColor="rgba(255,255,255,0)" />
              </radialGradient>
            </defs>
            <g stroke="rgba(148,163,184,0.25)" strokeWidth={0.6}>
              {edgeLines.map((edge, i) => {
                const a = projectedById.get(edge.source)!;
                const b = projectedById.get(edge.target)!;
                return (
                  <line key={i} x1={a.px} y1={a.py} x2={b.px} y2={b.py} />
                );
              })}
            </g>
            <g>
              {positioned.map(({ node }) => {
                const p = projectedById.get(node.paper_id)!;
                const isSelected = selectedPaperId === node.paper_id;
                const r = Math.max(2.5, Math.min(18, p.size * 0.7));
                return (
                  <g
                    key={node.paper_id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => onSelectPaper(node.paper_id)}
                  >
                    <title>{node.title}</title>
                    {isSelected && (
                      <circle cx={p.px} cy={p.py} r={r * 2.2} fill="url(#nodeGlow)" />
                    )}
                    <circle
                      cx={p.px}
                      cy={p.py}
                      r={isSelected ? r * 1.5 : r}
                      fill={p.color}
                      fillOpacity={0.9}
                      stroke={isSelected ? '#ffffff' : 'rgba(255,255,255,0.4)'}
                      strokeWidth={isSelected ? 1.5 : 0.6}
                    />
                  </g>
                );
              })}
            </g>
          </svg>
          <div className="absolute left-4 bottom-3 right-4 flex justify-between text-[10px] text-muted mono-text pointer-events-none">
            <span>Force-directed citation network</span>
            <span>Node size reflects citation impact - colors are research clusters</span>
          </div>
        </div>
      </div>
    );
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
