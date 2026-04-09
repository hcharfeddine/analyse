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

        const response = await fetch('/data/processed_graph.json');
        if (!response.ok) throw new Error('Failed to load graph data');

        const data = await response.json();
        const foundPaper = data.nodes.find((n: PaperData) => n.paper_id === paperId);

        if (foundPaper) {
          setPaper(foundPaper);
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
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
          <p className="text-sm text-muted">Loading details...</p>
        </div>
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-4">
        <p className="text-sm text-red-500 mb-4">{error || 'Paper not found'}</p>
        <button
          onClick={onClose}
          className="text-sm text-primary hover:underline"
        >
          Close
        </button>
      </div>
    );
  }

  const uniqueCountries = [...new Set(paper.authors.flatMap((a) => a.countries))];
  const uniqueOrganizations = [
    ...new Set(paper.authors.flatMap((a) => a.affiliations)),
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border p-4 flex justify-between items-start gap-2">
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-1">Paper Details</h3>
          <p className="text-xs text-muted truncate">{paper.paper_id}</p>
        </div>
        <button
          onClick={onClose}
          className="text-muted hover:text-foreground text-xl leading-none"
        >
          ×
        </button>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Title */}
        <div>
          <p className="text-lg font-bold text-foreground leading-tight">
            {paper.title}
          </p>
        </div>

        {/* Basic Info */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="bg-muted/10 rounded p-2">
            <p className="text-xs text-muted">Year</p>
            <p className="font-semibold text-foreground">{paper.year}</p>
          </div>
          <div className="bg-muted/10 rounded p-2">
            <p className="text-xs text-muted">Type</p>
            <p className="font-semibold text-foreground capitalize">{paper.publication_type}</p>
          </div>
          <div className="bg-muted/10 rounded p-2">
            <p className="text-xs text-muted">Citations</p>
            <p className="font-semibold text-foreground">{paper.cited_by_count.toLocaleString()}</p>
          </div>
          <div className="bg-muted/10 rounded p-2">
            <p className="text-xs text-muted">References</p>
            <p className="font-semibold text-foreground">{paper.out_degree}</p>
          </div>
        </div>

        {/* Field of Study */}
        {paper.field_of_study && (
          <div>
            <p className="text-xs font-semibold text-muted mb-1">Research Field</p>
            <p className="text-sm text-foreground">{paper.field_of_study}</p>
          </div>
        )}

        {/* Journal/Venue */}
        {(paper.journal_name || paper.venue) && (
          <div>
            <p className="text-xs font-semibold text-muted mb-1">Publication Venue</p>
            <p className="text-sm text-foreground">
              {paper.journal_name || paper.venue}
            </p>
            {paper.publisher && (
              <p className="text-xs text-muted mt-1">{paper.publisher}</p>
            )}
          </div>
        )}

        {/* DOI */}
        {paper.doi && (
          <div>
            <p className="text-xs font-semibold text-muted mb-1">DOI</p>
            <a
              href={`https://doi.org/${paper.doi}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary hover:underline break-all"
            >
              {paper.doi}
            </a>
          </div>
        )}

        {/* PDF Link */}
        {paper.pdf_url && paper.pdf_url !== 'PDF URL not available' && (
          <div>
            <a
              href={paper.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary hover:underline inline-flex items-center gap-1"
            >
              📄 View PDF
            </a>
          </div>
        )}

        {/* Authors */}
        {paper.authors.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-muted mb-2">Authors ({paper.authors.length})</p>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {paper.authors.slice(0, 5).map((author, idx) => (
                <div key={idx} className="text-xs p-2 bg-muted/10 rounded">
                  <p className="font-medium text-foreground">{author.author_id}</p>
                  {author.affiliations.length > 0 && (
                    <p className="text-muted">{author.affiliations[0]}</p>
                  )}
                  {author.countries.length > 0 && (
                    <p className="text-muted text-xs">{author.countries.join(', ')}</p>
                  )}
                </div>
              ))}
              {paper.authors.length > 5 && (
                <p className="text-xs text-muted">
                  +{paper.authors.length - 5} more authors
                </p>
              )}
            </div>
          </div>
        )}

        {/* Keywords */}
        {paper.keywords.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-muted mb-2">Keywords</p>
            <div className="flex flex-wrap gap-1">
              {paper.keywords.slice(0, 8).map((keyword, idx) => (
                <span
                  key={idx}
                  className="text-xs bg-primary/20 text-primary px-2 py-1 rounded"
                >
                  {keyword}
                </span>
              ))}
              {paper.keywords.length > 8 && (
                <span className="text-xs text-muted py-1">
                  +{paper.keywords.length - 8} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Abstract */}
        {paper.abstract && (
          <div>
            <button
              onClick={() => setExpandedAbstract(!expandedAbstract)}
              className="text-xs font-semibold text-muted hover:text-foreground mb-1 flex items-center gap-1"
            >
              <span>{expandedAbstract ? '−' : '+'}</span> Abstract
            </button>
            {expandedAbstract && (
              <p className="text-xs text-foreground leading-relaxed text-pretty">
                {paper.abstract}
              </p>
            )}
          </div>
        )}

        {/* Countries & Organizations */}
        {(uniqueCountries.length > 0 || uniqueOrganizations.length > 0) && (
          <div>
            {uniqueCountries.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-muted mb-1">Countries</p>
                <p className="text-xs text-foreground">{uniqueCountries.join(', ')}</p>
              </div>
            )}
            {uniqueOrganizations.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-semibold text-muted mb-1">
                  Institutions ({uniqueOrganizations.length})
                </p>
                <div className="text-xs text-foreground space-y-1">
                  {uniqueOrganizations.slice(0, 5).map((org, idx) => (
                    <p key={idx}>{org}</p>
                  ))}
                  {uniqueOrganizations.length > 5 && (
                    <p className="text-muted">
                      +{uniqueOrganizations.length - 5} more
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PaperDetails;
