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
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['year']));

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
    <div className="space-y-4">
      {/* Filter Header */}
      <div className="flex justify-between items-center">
        <h3 className="font-semibold text-foreground">Filters</h3>
        {isFiltered && (
          <button
            onClick={resetFilters}
            className="text-xs text-primary hover:underline"
          >
            Reset
          </button>
        )}
      </div>

      {/* Year Range Filter */}
      <div className="border border-border rounded-lg overflow-hidden">
        <button
          onClick={() => toggleSection('year')}
          className="w-full px-3 py-2 bg-muted/10 hover:bg-muted/20 flex justify-between items-center text-sm font-medium text-foreground transition-colors"
        >
          <span>Publication Year</span>
          <span className="text-xs text-muted">
            {expandedSections.has('year') ? '−' : '+'}
          </span>
        </button>

        {expandedSections.has('year') && (
          <div className="p-3 space-y-3 border-t border-border">
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-muted">
                <span>Min Year</span>
                <span className="font-semibold text-foreground">{localYearRange[0]}</span>
              </div>
              <input
                type="range"
                min={years.min}
                max={years.max}
                value={localYearRange[0]}
                onChange={(e) => handleYearChange('min', parseInt(e.target.value))}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs text-muted">
                <span>Max Year</span>
                <span className="font-semibold text-foreground">{localYearRange[1]}</span>
              </div>
              <input
                type="range"
                min={years.min}
                max={years.max}
                value={localYearRange[1]}
                onChange={(e) => handleYearChange('max', parseInt(e.target.value))}
                className="w-full"
              />
            </div>
          </div>
        )}
      </div>

      {/* Cluster Filter */}
      {clusters.length > 0 && (
        <div className="border border-border rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('clusters')}
            className="w-full px-3 py-2 bg-muted/10 hover:bg-muted/20 flex justify-between items-center text-sm font-medium text-foreground transition-colors"
          >
            <span>Research Clusters</span>
            <span className="text-xs text-muted">
              {expandedSections.has('clusters') ? '−' : '+'}
            </span>
          </button>

          {expandedSections.has('clusters') && (
            <div className="p-3 space-y-2 border-t border-border max-h-64 overflow-y-auto">
              {clusters.map((cluster) => (
                <label
                  key={cluster.id}
                  className="flex items-center gap-2 cursor-pointer hover:bg-muted/10 p-2 rounded transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedClusters.includes(cluster.id)}
                    onChange={() => toggleCluster(cluster.id)}
                    className="w-4 h-4 cursor-pointer"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-foreground truncate">
                      {cluster.label}
                    </p>
                    <p className="text-xs text-muted">
                      {cluster.size.toLocaleString()} papers
                    </p>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Info */}
      <div className="text-xs text-muted p-3 bg-muted/5 rounded-lg">
        <p>💡 Click on papers in the network to view detailed information.</p>
      </div>
    </div>
  );
};

export default FilterPanel;
