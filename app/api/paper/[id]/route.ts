import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: paperId } = await params;

  try {
    const samplePapers: { [key: string]: any } = {
      'paper_1': {
        paper_id: 'paper_1',
        title: 'Machine Learning for Citation Networks',
        authors: [{ author_id: 'author_1', affiliations: ['MIT'], countries: ['USA'], organization_types: ['University'], citation_count: 150 }],
        year: 2020,
        cited_by_count: 45,
        doi: '10.1234/example.1',
        publisher: 'ACM',
        abstract: 'This paper explores machine learning techniques for analyzing citation networks and scientific knowledge graphs.',
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
        authors: [{ author_id: 'author_2', affiliations: ['Stanford University'], countries: ['USA'], organization_types: ['University'], citation_count: 200 }],
        year: 2021,
        cited_by_count: 78,
        doi: '10.1234/example.2',
        publisher: 'IEEE',
        abstract: 'We present novel approaches using graph neural networks for understanding scientific knowledge and paper relationships.',
        publication_type: 'journal',
        journal_name: 'Nature Machine Intelligence',
        venue: 'Nature Machine Intelligence',
        field_of_study: 'Computer Science',
        keywords: ['graph neural networks', 'knowledge graphs', 'semantic web'],
        pdf_url: 'https://example.com/paper2.pdf',
        in_degree: 8,
        out_degree: 2,
        cluster_id: 1
      },
      'paper_3': {
        paper_id: 'paper_3',
        title: 'Deep Learning for Natural Language Processing',
        authors: [{ author_id: 'author_3', affiliations: ['CMU'], countries: ['USA'], organization_types: ['University'], citation_count: 300 }],
        year: 2019,
        cited_by_count: 120,
        doi: '10.1234/example.3',
        publisher: 'ACL',
        abstract: 'A comprehensive survey of deep learning methods applied to NLP tasks and benchmarks.',
        publication_type: 'conference',
        journal_name: 'ACL 2019',
        venue: 'Association for Computational Linguistics',
        field_of_study: 'Computer Science',
        keywords: ['deep learning', 'NLP', 'transformers'],
        pdf_url: '',
        in_degree: 3,
        out_degree: 7,
        cluster_id: 0
      },
      'paper_4': {
        paper_id: 'paper_4',
        title: 'Quantum Computing and Future Technologies',
        authors: [{ author_id: 'author_4', affiliations: ['Caltech'], countries: ['USA'], organization_types: ['University'], citation_count: 90 }],
        year: 2022,
        cited_by_count: 32,
        doi: '10.1234/example.4',
        publisher: 'Nature',
        abstract: 'Exploring quantum computing applications in solving complex scientific problems.',
        publication_type: 'journal',
        journal_name: 'Nature Physics',
        venue: 'Nature Physics',
        field_of_study: 'Physics',
        keywords: ['quantum computing', 'algorithms', 'quantum mechanics'],
        pdf_url: '',
        in_degree: 12,
        out_degree: 4,
        cluster_id: 1
      },
      'paper_5': {
        paper_id: 'paper_5',
        title: 'Biological Networks and Systems Biology',
        authors: [{ author_id: 'author_5', affiliations: ['Harvard'], countries: ['USA'], organization_types: ['University'], citation_count: 110 }],
        year: 2020,
        cited_by_count: 67,
        doi: '10.1234/example.5',
        publisher: 'Cell Press',
        abstract: 'Analysis of biological networks using graph theory and systems biology approaches.',
        publication_type: 'journal',
        journal_name: 'Cell Systems',
        venue: 'Cell Systems',
        field_of_study: 'Biology',
        keywords: ['systems biology', 'networks', 'protein interactions'],
        pdf_url: '',
        in_degree: 6,
        out_degree: 5,
        cluster_id: 0
      }
    };

    const paper = samplePapers[paperId];

    if (paper) {
      return NextResponse.json({ paper });
    }

    return NextResponse.json(
      { error: 'Paper not found' },
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
