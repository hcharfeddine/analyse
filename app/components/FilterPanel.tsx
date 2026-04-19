'use client';

import React, { useState, useEffect } from 'react';

interface FilterPanelProps {
  onYearRangeChange: (range: [number, number]) => void;
  onClusterChange: (clusters: number[]) => void;
  yearRange: [number, number];
  selectedClusters: number[];
}

const FilterPanel: React.FC<FilterPanelProps> = ({
  onYearRangeChange,
  onClusterChange,
  yearRange,
  selectedClusters,
}) => {
  const [clusters, setClusters] = useState<Array<{ id: number; label: string; size: number }>>([]);
  const [years, setYears] = useState<{ min: number; max: number }>({ min: 1900, max: 2024 });
  const [localYearRange, setLocalYearRange] = useState(yearRange);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['year', 'clusters']));

  // Load cluster information from API
  useEffect(() => {
    const loadClusters = async () => {
      try {
        const response = await fetch('/api/graph?type=metadata');
        if (response.ok) {
          const data = await response.json();
          
          const clusterList = Object.entries(data.clusters || {}).map(
            ([id, cluster]: [string, any]) => ({
              id: parseInt(id),
              label: cluster.fields?.[0] || `Cluster ${id}`,
              size: cluster.size || 0,
            })
          );
          
          setClusters(clusterList.sort((a, b) => b.size - a.size));
          
          if (data.statistics) {
            setYears({
              min: data.statistics.years?.min || 1900,
              max: data.statistics.years?.max || 2024,
            });
          }
        }
      } catch (err) {
        console.error('[v0] Error loading clusters:', err);
      }
    };

    loadClusters();
  }, []);

  const handleYearChange = (position: 'min' | 'max', value: number) => {
    const newRange: [number, number] = position === 'min' 
      ? [value, localYearRange[1]]
      : [localYearRange[0], value];
    
    setLocalYearRange(newRange);
    onYearRangeChange(newRange);
  };

  const toggleCluster = (clusterId: number) => {
    const updated = selectedClusters.includes(clusterId)
      ? selectedClusters.filter((c) => c !== clusterId)
      : [...selectedClusters, clusterId];
    
    onClusterChange(updated);
  };

  const toggleSection = (section: string) => {
    const newSections = new Set(expandedSections);
    if (newSections.has(section)) {
      newSections.delete(section);
    } else {
      newSections.add(section);
    }
    setExpandedSections(newSections);
  };

  const resetFilters = () => {
    setLocalYearRange([years.min, years.max]);
    onYearRangeChange([years.min, years.max]);
    onClusterChange([]);
  };

  const isFiltered = localYearRange[0] !== years.min || 
                     localYearRange[1] !== years.max || 
                     selectedClusters.length > 0;

  return (
    <div className="space-y-6">
      {/* Filter Header */}
      <div className="flex justify-between items-center">
        <label className="text-xs font-semibold text-muted uppercase tracking-wider mono-text">
          Filters
        </label>
        {isFiltered && (
          <button
            onClick={resetFilters}
            className="text-[10px] text-primary hover:text-white uppercase tracking-wide px-2 py-1 rounded bg-primary/10 hover:bg-primary/30 transition-colors"
          >
            Clear Filters
          </button>
        )}
      </div>

      <div className="space-y-4">
        {/* Year Range Filter */}
        <div className="border border-border/40 bg-black/20 rounded-xl overflow-hidden backdrop-blur-sm">
          <button
            onClick={() => toggleSection('year')}
            className="w-full px-4 py-3 flex justify-between items-center text-sm font-medium text-foreground/90 hover:bg-white/5 transition-colors"
          >
            <span>Timeline</span>
            <span className="text-muted">
              {expandedSections.has('year') ? (
                <svg width="16" height="16" style={{width:'16px',height:'16px',flexShrink:0}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 15l7-7 7 7"></path></svg>
              ) : (
                <svg width="16" height="16" style={{width:'16px',height:'16px',flexShrink:0}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
              )}
            </span>
          </button>

          {expandedSections.has('year') && (
            <div className="p-4 space-y-5 border-t border-border/40">
              <div className="space-y-3">
                <div className="flex justify-between items-baseline">
                  <span className="text-[11px] text-muted uppercase tracking-wide mono-text">Min Year</span>
                  <span className="font-mono text-sm text-primary">{localYearRange[0]}</span>
                </div>
                <input
                  type="range"
                  min={years.min}
                  max={years.max}
                  value={localYearRange[0]}
                  onChange={(e) => handleYearChange('min', parseInt(e.target.value))}
                />
              </div>

              <div className="space-y-3">
                <div className="flex justify-between items-baseline">
                  <span className="text-[11px] text-muted uppercase tracking-wide mono-text">Max Year</span>
                  <span className="font-mono text-sm text-primary">{localYearRange[1]}</span>
                </div>
                <input
                  type="range"
                  min={years.min}
                  max={years.max}
                  value={localYearRange[1]}
                  onChange={(e) => handleYearChange('max', parseInt(e.target.value))}
                />
              </div>
            </div>
          )}
        </div>

        {/* Cluster Filter */}
        {clusters.length > 0 && (
          <div className="border border-border/40 bg-black/20 rounded-xl overflow-hidden backdrop-blur-sm">
            <button
              onClick={() => toggleSection('clusters')}
              className="w-full px-4 py-3 flex justify-between items-center text-sm font-medium text-foreground/90 hover:bg-white/5 transition-colors"
            >
              <span>Research Clusters</span>
              <span className="text-muted">
                {expandedSections.has('clusters') ? (
                  <svg width="16" height="16" style={{width:'16px',height:'16px',flexShrink:0}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 15l7-7 7 7"></path></svg>
                ) : (
                  <svg width="16" height="16" style={{width:'16px',height:'16px',flexShrink:0}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                )}
              </span>
            </button>

            {expandedSections.has('clusters') && (
              <div className="p-3 space-y-1 border-t border-border/40 max-h-64 overflow-y-auto custom-scrollbar">
                {clusters.map((cluster) => {
                  const isSelected = selectedClusters.includes(cluster.id);
                  return (
                    <label
                      key={cluster.id}
                      className={`flex items-center gap-3 cursor-pointer p-2 rounded-lg transition-colors border border-transparent ${
                        isSelected ? 'bg-primary/10 border-primary/30' : 'hover:bg-white/5'
                      }`}
                    >
                      <div className="relative flex items-center justify-center">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleCluster(cluster.id)}
                          className="peer sr-only"
                        />
                        <div className={`w-4 h-4 rounded flex items-center justify-center border transition-all ${
                          isSelected ? 'bg-primary border-primary' : 'border-muted/50 bg-black/30'
                        }`}>
                          {isSelected && (
                            <svg width="12" height="12" style={{width: '12px', height: '12px', flexShrink: 0, color: 'white'}} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                          )}
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm truncate transition-colors ${isSelected ? 'text-primary font-medium' : 'text-foreground/80'}`}>
                          {cluster.label}
                        </p>
                        <p className="text-[10px] text-muted mono-text mt-0.5">
                          {cluster.size.toLocaleString()} nodes
                        </p>
                      </div>
                    </label>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex gap-3 p-4 bg-primary/5 border border-primary/10 rounded-xl items-start">
        <svg width="16" height="16" style={{width: '16px', height: '16px', flexShrink: 0, color: 'var(--color-primary)', marginTop: '2px'}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        <p className="text-xs text-muted/90 leading-relaxed">
          Select nodes in the network canvas to inspect detailed citation metadata and abstracts.
        </p>
      </div>
    </div>
  );
};

export default FilterPanel;
