'use client';

import React, { useState, useEffect } from 'react';

interface PaperData {
  paper_id: string;
  title: string;
  authors: Array<{
    author_id: string;
    affiliations: string[];
    countries: string[];
    organization_types: string[];
    citation_count: number;
  }>;
  year: number;
  cited_by_count: number;
  doi: string;
  publisher: string;
  abstract: string;
  publication_type: string;
  journal_name: string;
  venue: string;
  field_of_study: string;
  keywords: string[];
  pdf_url: string;
  in_degree: number;
  out_degree: number;
  cluster_id: number;
}

interface Props {
  paperId: string;
  onClose: () => void;
}

const PaperDetails: React.FC<Props> = ({ paperId, onClose }) => {
  const [paper, setPaper] = useState<PaperData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedAbstract, setExpandedAbstract] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadPaper = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await fetch(`/api/paper/${paperId}`);
        if (!response.ok) throw new Error('Failed to load paper data');

        const data = await response.json();
        if (data.paper) {
          setPaper(data.paper);
        } else {
          setError('Paper not found');
        }
      } catch (err) {
        console.error('[v0] Error loading paper:', err);
        setError('Failed to load paper details');
      } finally {
        setIsLoading(false);
      }
    };

    loadPaper();
  }, [paperId]);

  if (isLoading) {
    return (
      <div className="flex flex-col h-full bg-background">
        <div className="border-b border-border/50 p-4 flex justify-between items-center">
          <div className="h-4 w-32 bg-muted/20 rounded animate-pulse"></div>
          <div className="h-6 w-6 bg-muted/20 rounded-full animate-pulse"></div>
        </div>
        <div className="p-6 space-y-8">
          <div className="space-y-3">
            <div className="h-6 w-full bg-muted/20 rounded animate-pulse"></div>
            <div className="h-6 w-3/4 bg-muted/20 rounded animate-pulse"></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-16 bg-muted/10 rounded-lg animate-pulse"></div>
            ))}
          </div>
          <div className="space-y-2">
            <div className="h-4 w-24 bg-muted/20 rounded animate-pulse"></div>
            <div className="h-20 bg-muted/10 rounded-lg animate-pulse"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center">
        <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
          <svg width="24" height="24" style={{width:'24px',height:'24px',flexShrink:0,color:'#ef4444'}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
        </div>
        <p className="text-sm text-red-400 mb-4">{error || 'Paper not found'}</p>
        <button
          onClick={onClose}
          className="text-xs px-4 py-2 rounded-md bg-white/5 hover:bg-white/10 transition-colors"
        >
          Dismiss
        </button>
      </div>
    );
  }

  const uniqueCountries = [...new Set(paper.authors.flatMap((a) => a.countries))];
  const uniqueOrganizations = [
    ...new Set(paper.authors.flatMap((a) => a.affiliations)),
  ];

  return (
    <div className="flex flex-col h-full bg-background relative">
      {/* Header */}
      <div className="border-b border-border/50 px-6 py-4 flex justify-between items-center shrink-0 backdrop-blur-md bg-background/80 sticky top-0 z-10">
        <div>
          <h3 className="text-xs font-bold text-white uppercase tracking-widest mono-text">Inspector</h3>
          <p className="text-[10px] text-muted mono-text mt-1 opacity-70">ID: {paper.paper_id}</p>
        </div>
        <button
          onClick={onClose}
          className="text-muted hover:text-white p-1.5 rounded-md hover:bg-white/10 transition-colors"
        >
          <svg width="20" height="20" style={{width:'20px',height:'20px',flexShrink:0}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
        {/* Title */}
        <div className="space-y-3">
          {paper.field_of_study && (
            <span className="inline-block px-2.5 py-1 rounded text-[10px] uppercase tracking-wider font-semibold bg-accent/10 text-accent mono-text">
              {paper.field_of_study}
            </span>
          )}
          <h2 className="text-xl font-medium text-white leading-snug tracking-tight">
            {paper.title}
          </h2>
          <div className="flex items-center gap-2 text-sm text-muted mono-text">
            <span>{paper.year}</span>
            <span className="w-1 h-1 rounded-full bg-muted/40"></span>
            <span className="capitalize">{paper.publication_type || 'Article'}</span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-black/30 border border-border/40 rounded-xl p-4 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <p className="text-[11px] text-muted uppercase tracking-wide mono-text mb-1">Citations</p>
            <p className="text-2xl font-light text-primary">{paper.cited_by_count.toLocaleString()}</p>
          </div>
          <div className="bg-black/30 border border-border/40 rounded-xl p-4 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-secondary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <p className="text-[11px] text-muted uppercase tracking-wide mono-text mb-1">References</p>
            <p className="text-2xl font-light text-secondary">{paper.out_degree}</p>
          </div>
        </div>

        <div className="h-px bg-border/40 w-full"></div>

        {/* Venue / DOI Links */}
        <div className="space-y-4">
          {(paper.journal_name || paper.venue) && (
            <div>
              <p className="text-[11px] text-muted uppercase tracking-wide mono-text mb-1.5">Publication Venue</p>
              <p className="text-sm text-white/90">
                {paper.journal_name || paper.venue}
              </p>
              {paper.publisher && (
                <p className="text-xs text-muted mt-1">{paper.publisher}</p>
              )}
            </div>
          )}

          <div className="flex gap-4 pt-2">
            {paper.doi && (
              <a
                href={`https://doi.org/${paper.doi}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 inline-flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium transition-all"
              >
                <svg width="16" height="16" style={{width:'16px',height:'16px',flexShrink:0,color:'var(--color-muted)'}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                View DOI
              </a>
            )}
            {paper.pdf_url && paper.pdf_url !== 'PDF URL not available' && (
              <a
                href={paper.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 inline-flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-primary/20 hover:bg-primary/30 border border-primary/30 text-primary text-xs font-medium transition-all"
              >
                <svg width="16" height="16" style={{width:'16px',height:'16px',flexShrink:0}} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                PDF
              </a>
            )}
          </div>
        </div>

        {/* Abstract */}
        {paper.abstract && (
          <div className="space-y-2">
            <p className="text-[11px] text-muted uppercase tracking-wide mono-text flex justify-between items-center">
              <span>Abstract</span>
              <button onClick={() => setExpandedAbstract(!expandedAbstract)} className="text-primary hover:text-primary/80 lowercase tracking-normal">
                {expandedAbstract ? 'Show less' : 'Read more'}
              </button>
            </p>
            <p className={`text-sm text-white/80 leading-relaxed ${!expandedAbstract ? 'line-clamp-4' : ''}`}>
              {paper.abstract}
            </p>
          </div>
        )}

        <div className="h-px bg-border/40 w-full"></div>

        {/* Keywords */}
        {paper.keywords.length > 0 && (
          <div className="space-y-3">
            <p className="text-[11px] text-muted uppercase tracking-wide mono-text">Keywords</p>
            <div className="flex flex-wrap gap-2">
              {paper.keywords.slice(0, 8).map((keyword, idx) => (
                <span
                  key={idx}
                  className="text-[11px] bg-white/5 border border-white/10 px-2.5 py-1 rounded-md text-white/90"
                >
                  {keyword}
                </span>
              ))}
              {paper.keywords.length > 8 && (
                <span className="text-[11px] text-muted py-1 mono-text">
                  +{paper.keywords.length - 8}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Authors */}
        {paper.authors.length > 0 && (
          <div className="space-y-3">
            <p className="text-[11px] text-muted uppercase tracking-wide mono-text">
              Authors ({paper.authors.length})
            </p>
            <div className="space-y-2">
              {paper.authors.slice(0, 5).map((author, idx) => (
                <div key={idx} className="p-3 bg-black/20 border border-white/5 rounded-lg flex flex-col gap-1">
                  <p className="text-sm font-medium text-white/90">{author.author_id}</p>
                  {author.affiliations.length > 0 && (
                    <p className="text-xs text-muted truncate">{author.affiliations[0]}</p>
                  )}
                  {author.countries.length > 0 && (
                    <p className="text-[10px] text-muted/70 mono-text uppercase mt-1">{author.countries.join(', ')}</p>
                  )}
                </div>
              ))}
              {paper.authors.length > 5 && (
                <button className="w-full py-2 text-xs text-muted hover:text-white border border-dashed border-white/10 rounded-lg transition-colors">
                  View {paper.authors.length - 5} more authors
                </button>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default PaperDetails;
