'use client';

import React, { useState, useEffect } from 'react';

interface SearchResult {
  paper_id: string;
  title: string;
  year: number;
  field_of_study: string;
  cited_by_count: number;
  authors: Array<{ author_id: string }>;
}

interface Props {
  onSearch: (query: string) => void;
  onSelectPaper: (paperId: string) => void;
}

const SearchPanel: React.FC<Props> = ({ onSearch, onSelectPaper }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (query.length > 0) {
        performSearch(query);
        onSearch(query);
      } else {
        setResults([]);
        setShowResults(false);
        onSearch('');
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query, onSearch]);

  const performSearch = async (searchQuery: string) => {
    try {
      setIsSearching(true);
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery }),
      });

      if (response.ok) {
        const data = await response.json();
        setResults(data.results.slice(0, 10)); // Limit to 10 results
        setShowResults(true);
      }
    } catch (err) {
      console.error('[v0] Search error:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectResult = (paperId: string) => {
    onSelectPaper(paperId);
    setShowResults(false);
    setQuery('');
  };

  return (
    <div className="space-y-4 relative">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-muted uppercase tracking-wider mono-text">
          Search Directory
        </label>
      </div>
      
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg width="16" height="16" style={{width:'16px',height:'16px',flexShrink:0,color:'var(--color-muted)'}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
        </div>
        <input
          type="text"
          placeholder="Title, abstract, keywords..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query.length > 0 && setShowResults(true)}
          className="w-full pl-10 pr-10 py-2.5 bg-black/40 border border-border rounded-lg text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
        />
        {isSearching && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
            <svg className="animate-spin h-4 w-4 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
          </div>
        )}
      </div>

      {/* Search Results */}
      {showResults && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 border border-border rounded-lg glass-panel shadow-2xl overflow-hidden max-h-80 overflow-y-auto z-50">
          {results.map((paper) => (
            <button
              key={paper.paper_id}
              onClick={() => handleSelectResult(paper.paper_id)}
              className="w-full text-left px-4 py-3 hover:bg-primary/10 border-b border-border/50 last:border-b-0 transition-colors group"
            >
              <p className="font-medium text-sm text-foreground line-clamp-2 group-hover:text-primary transition-colors">
                {paper.title}
              </p>
              <div className="flex justify-between items-center mt-2">
                <span className="text-xs text-muted mono-text">
                  {paper.year} • {paper.authors?.length || 0} authors
                </span>
                <span className="text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded mono-text">
                  {paper.cited_by_count} cites
                </span>
              </div>
              <p className="text-[11px] text-muted/70 mt-1 uppercase tracking-wide">{paper.field_of_study}</p>
            </button>
          ))}
        </div>
      )}

      {showResults && query.length > 0 && results.length === 0 && !isSearching && (
        <div className="absolute top-full left-0 right-0 mt-2 border border-border rounded-lg glass-panel p-4 text-center text-sm text-muted z-50">
          No papers found matching "{query}"
        </div>
      )}
    </div>
  );
};

export default SearchPanel;
