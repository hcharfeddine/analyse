'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import SearchPanel from './components/SearchPanel';
import FilterPanel from './components/FilterPanel';
import PaperDetails from './components/PaperDetails';

// Sigma uses WebGL which is only available in the browser — disable SSR
const CitationNetworkVisualization = dynamic(
  () => import('./components/CitationNetworkVisualization'),
  { ssr: false }
);

export default function Home() {
  const [selectedPaper, setSelectedPaper] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [yearRange, setYearRange] = useState<[number, number]>([1900, 2024]);
  const [selectedClusters, setSelectedClusters] = useState<number[]>([]);

  return (
    <main className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      {/* Left Sidebar - Controls */}
      <div className="flex w-[320px] flex-col border-r border-border glass-panel z-10 relative shadow-2xl">
        <div className="border-b border-border/50 p-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-[0_0_15px_rgba(59,130,246,0.3)]">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 text-white">
                <path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z"></path>
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-white">Citation Explorer</h1>
              <p className="text-xs text-muted mono-text uppercase tracking-wider mt-0.5">Network Visualizer</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
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
      <div className="flex-1 flex flex-col relative bg-[#02040a]">
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
        <div className="w-[384px] border-l border-border glass-panel z-10 shadow-[-10px_0_30px_rgba(0,0,0,0.5)] overflow-hidden">
          <PaperDetails paperId={selectedPaper} onClose={() => setSelectedPaper(null)} />
        </div>
      )}
    </main>
  );
}
