import { NextRequest, NextResponse } from 'next/server';

// For now, return a sample paper to avoid loading the massive JSON file
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const paperId = params.id;

  try {
    // TODO: Once optimized database is in place, query it here
    // For now, return a sample paper based on ID
    
    const samplePapers: { [key: string]: any } = {
      'paper_1': {
        paper_id: 'paper_1',
        title: 'Machine Learning for Citation Networks',
        authors: [
          {
            author_id: 'author_1',
            affiliations: ['MIT'],
            countries: ['USA'],
            organization_types: ['University'],
            citation_count: 150
          }
        ],
        year: 2020,
        cited_by_count: 45,
        doi: '10.1234/example.1',
        publisher: 'ACM',
        abstract: 'This paper explores machine learning techniques for analyzing citation networks...',
        publication_type: 'conference',
        journal_name: 'ICML 2020',
        venue: 'International Conference on Machine Learning',
        field_of_study: 'Computer Science',
        keywords: ['machine learning', 'citation networks', 'neural networks'],
        pdf_url: 'https://example.com/paper.pdf',
        in_degree: 5,
        out_degree: 3,
        cluster_id: 0
      },
      'paper_2': {
        paper_id: 'paper_2',
        title: 'Graph Neural Networks and Scientific Knowledge',
        authors: [
          {
            author_id: 'author_2',
            affiliations: ['Stanford University'],
            countries: ['USA'],
            organization_types: ['University'],
            citation_count: 200
          }
        ],
        year: 2021,
        cited_by_count: 78,
        doi: '10.1234/example.2',
        publisher: 'IEEE',
        abstract: 'We present novel approaches using graph neural networks for understanding scientific knowledge...',
        publication_type: 'journal',
        journal_name: 'Nature Machine Intelligence',
        venue: 'Nature Machine Intelligence',
        field_of_study: 'Computer Science',
        keywords: ['graph neural networks', 'knowledge graphs', 'semantic web'],
        pdf_url: 'https://example.com/paper2.pdf',
        in_degree: 8,
        out_degree: 2,
        cluster_id: 1
      }
    };

    const paper = samplePapers[paperId];

    if (paper) {
      return NextResponse.json({ paper });
    }

    return NextResponse.json(
      { 
        error: 'Paper not found',
        note: 'Currently using sample data. Run: npm run optimize for full dataset access'
      },
      { status: 404 }
    );
  } catch (error) {
    console.error('Error fetching paper:', error);
    return NextResponse.json(
      { error: 'Failed to fetch paper details' },
      { status: 500 }
    );
  }
}
