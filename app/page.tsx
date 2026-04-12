'use client';

import { useState } from 'react';
import CitationNetworkVisualization from './components/CitationNetworkVisualization';
import SearchPanel from './components/SearchPanel';
import FilterPanel from './components/FilterPanel';
import PaperDetails from './components/PaperDetails';

export default function Home() {
  const [selectedPaper, setSelectedPaper] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [yearRange, setYearRange] = useState<[number, number]>([1900, 2024]);
  const [selectedClusters, setSelectedClusters] = useState<number[]>([]);

  return (
    <main className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      {/* Left Sidebar - Controls */}
      <div className="flex w-80 flex-col border-r border-border bg-background shadow-lg">
        <div className="border-b border-border p-4">
          <h1 className="text-2xl font-bold text-primary">Citation Network</h1>
          <p className="mt-1 text-sm text-muted">Explore scientific paper citations</p>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Search Component */}
          <SearchPanel
            onSearch={setSearchQuery}
            onSelectPaper={setSelectedPaper}
          />

          {/* Filter Component */}
          <FilterPanel
            onYearRangeChange={setYearRange}
            onClusterChange={setSelectedClusters}
            yearRange={yearRange}
            selectedClusters={selectedClusters}
          />
        </div>
      </div>

      {/* Main Visualization Area */}
      <div className="flex-1 flex flex-col">
        <CitationNetworkVisualization
          selectedPaperId={selectedPaper}
          onSelectPaper={setSelectedPaper}
          searchQuery={searchQuery}
          yearRange={yearRange}
          selectedClusters={selectedClusters}
        />
      </div>

      {/* Right Sidebar - Paper Details */}
      {selectedPaper && (
        <div className="w-96 border-l border-border bg-background shadow-lg overflow-y-auto">
          <PaperDetails paperId={selectedPaper} onClose={() => setSelectedPaper(null)} />
        </div>
      )}
    </main>
  );
}
