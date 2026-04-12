/**
 * Data loading utilities with caching and performance optimization
 */

interface GraphData {
  nodes: any[];
  edges: any[];
  clusters: Record<number, any>;
  statistics: any;
}

interface SearchIndex {
  [key: string]: string[];
}

let graphCache: GraphData | null = null;
let searchIndexCache: SearchIndex | null = null;

/**
 * Load the processed graph data with caching
 */
export async function loadGraphData(): Promise<GraphData> {
  if (graphCache) {
    console.log('[v0] Using cached graph data');
    return graphCache;
  }

  try {
    console.log('[v0] Fetching graph data...');
    const response = await fetch('/data/processed_graph.json', {
      cache: 'force-cache',
    });

    if (!response.ok) {
      throw new Error(`Failed to load graph: ${response.statusText}`);
    }

    graphCache = await response.json();
    console.log('[v0] Graph data loaded:', {
      nodes: graphCache.nodes.length,
      edges: graphCache.edges.length,
    });

    return graphCache;
  } catch (error) {
    console.error('[v0] Error loading graph data:', error);
    throw error;
  }
}

/**
 * Load the search index with caching
 */
export async function loadSearchIndex(): Promise<SearchIndex> {
  if (searchIndexCache) {
    console.log('[v0] Using cached search index');
    return searchIndexCache;
  }

  try {
    console.log('[v0] Fetching search index...');
    const response = await fetch('/data/search_index.json', {
      cache: 'force-cache',
    });

    if (!response.ok) {
      console.warn('[v0] Search index not available');
      return {};
    }

    searchIndexCache = await response.json();
    console.log('[v0] Search index loaded');

    return searchIndexCache;
  } catch (error) {
    console.error('[v0] Error loading search index:', error);
    return {};
  }
}

/**
 * Clear cache (useful for development)
 */
export function clearCache(): void {
  graphCache = null;
  searchIndexCache = null;
  console.log('[v0] Cache cleared');
}

/**
 * Get a paper by ID
 */
export async function getPaperById(paperId: string): Promise<any | null> {
  try {
    const graphData = await loadGraphData();
    return graphData.nodes.find((node) => node.paper_id === paperId) || null;
  } catch (error) {
    console.error('[v0] Error getting paper:', error);
    return null;
  }
}

/**
 * Search papers by query
 */
export async function searchPapers(
  query: string,
  limit: number = 50
): Promise<any[]> {
  try {
    const graphData = await loadGraphData();
    const searchQuery = query.toLowerCase().trim();

    if (!searchQuery) {
      return [];
    }

    const results = graphData.nodes
      .filter((node) => {
        const title = node.title?.toLowerCase() || '';
        const abstract = node.abstract?.toLowerCase() || '';
        const keywords = (node.keywords || [])
          .map((k: string) => k.toLowerCase())
          .join(' ');

        return (
          title.includes(searchQuery) ||
          abstract.includes(searchQuery) ||
          keywords.includes(searchQuery)
        );
      })
      .slice(0, limit);

    console.log(`[v0] Search found ${results.length} results for "${query}"`);

    return results;
  } catch (error) {
    console.error('[v0] Error searching papers:', error);
    return [];
  }
}

/**
 * Get papers by cluster
 */
export async function getPapersByCluster(clusterId: number): Promise<any[]> {
  try {
    const graphData = await loadGraphData();
    return graphData.nodes.filter((node) => node.cluster_id === clusterId);
  } catch (error) {
    console.error('[v0] Error getting papers by cluster:', error);
    return [];
  }
}

/**
 * Get papers by year range
 */
export async function getPapersByYear(
  minYear: number,
  maxYear: number
): Promise<any[]> {
  try {
    const graphData = await loadGraphData();
    return graphData.nodes.filter(
      (node) => node.year >= minYear && node.year <= maxYear
    );
  } catch (error) {
    console.error('[v0] Error getting papers by year:', error);
    return [];
  }
}

/**
 * Get citation graph for a specific paper
 * Returns the paper and its direct citations
 */
export async function getCitationGraph(
  paperId: string,
  depth: number = 1
): Promise<{
  node: any | null;
  citing: any[];
  cited: any[];
}> {
  try {
    const graphData = await loadGraphData();

    const node = graphData.nodes.find((n) => n.paper_id === paperId) || null;

    if (!node) {
      return { node: null, citing: [], cited: [] };
    }

    // Papers that cite this paper
    const citingPaperIds = graphData.edges
      .filter((edge) => edge.target === paperId)
      .map((edge) => edge.source);

    // Papers this paper cites
    const citedPaperIds = graphData.edges
      .filter((edge) => edge.source === paperId)
      .map((edge) => edge.target);

    const citing = graphData.nodes.filter((n) => citingPaperIds.includes(n.paper_id));
    const cited = graphData.nodes.filter((n) => citedPaperIds.includes(n.paper_id));

    return {
      node,
      citing: citing.slice(0, 10),
      cited: cited.slice(0, 10),
    };
  } catch (error) {
    console.error('[v0] Error getting citation graph:', error);
    return { node: null, citing: [], cited: [] };
  }
}

/**
 * Get statistics about the graph
 */
export async function getGraphStatistics(): Promise<any> {
  try {
    const graphData = await loadGraphData();
    return graphData.statistics || {};
  } catch (error) {
    console.error('[v0] Error getting graph statistics:', error);
    return {};
  }
}

/**
 * Export for server-side usage
 */
export type { GraphData, SearchIndex };
