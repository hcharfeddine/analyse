'use client';

import React, { useState, useEffect, useCallback } from 'react';

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
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-semibold text-foreground mb-2">
          Search Papers
        </label>
        <div className="relative">
          <input
            type="text"
            placeholder="Search by title, abstract, keywords..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => query.length > 0 && setShowResults(true)}
            className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground placeholder-muted focus:outline-none focus:ring-2 focus:ring-primary"
          />
          {isSearching && (
            <div className="absolute right-3 top-2.5">
              <div className="animate-spin h-5 w-5 text-primary"></div>
            </div>
          )}
        </div>
      </div>

      {/* Search Results */}
      {showResults && results.length > 0 && (
        <div className="border border-border rounded-lg bg-background shadow-lg overflow-hidden max-h-96 overflow-y-auto">
          {results.map((paper) => (
            <button
              key={paper.paper_id}
              onClick={() => handleSelectResult(paper.paper_id)}
              className="w-full text-left px-3 py-2 hover:bg-primary/10 border-b border-border last:border-b-0 transition-colors"
            >
              <p className="font-medium text-sm text-foreground line-clamp-2">
                {paper.title}
              </p>
              <div className="flex justify-between items-center mt-1">
                <span className="text-xs text-muted">
                  {paper.year} • {paper.authors?.length || 0} authors
                </span>
                <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded">
                  {paper.cited_by_count} cites
                </span>
              </div>
              <p className="text-xs text-muted mt-1">{paper.field_of_study}</p>
            </button>
          ))}
        </div>
      )}

      {showResults && query.length > 0 && results.length === 0 && !isSearching && (
        <div className="text-center py-4 text-muted text-sm">
          No papers found matching your search.
        </div>
      )}
    </div>
  );
};

export default SearchPanel;
