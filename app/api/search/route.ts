import { NextRequest, NextResponse } from 'next/server';

interface Node {
  paper_id: string;
  title: string;
  abstract: string;
  keywords: string[];
  authors: Array<{ author_id: string }>;
  year: number;
  field_of_study: string;
  cited_by_count: number;
}

// Sample papers for search - avoids loading the massive JSON file
const SAMPLE_PAPERS: Node[] = [
  {
    paper_id: 'paper_1',
    title: 'Machine Learning for Citation Networks',
    abstract: 'This paper explores machine learning techniques for analyzing citation networks and scientific knowledge',
    keywords: ['machine learning', 'citation networks', 'neural networks'],
    authors: [{ author_id: 'author_1' }],
    year: 2020,
    field_of_study: 'Computer Science',
    cited_by_count: 45
  },
  {
    paper_id: 'paper_2',
    title: 'Graph Neural Networks and Scientific Knowledge',
    abstract: 'We present novel approaches using graph neural networks for understanding scientific knowledge graphs',
    keywords: ['graph neural networks', 'knowledge graphs', 'semantic web'],
    authors: [{ author_id: 'author_2' }],
    year: 2021,
    field_of_study: 'Computer Science',
    cited_by_count: 78
  },
  {
    paper_id: 'paper_3',
    title: 'Deep Learning for Natural Language Processing',
    abstract: 'A comprehensive survey of deep learning methods applied to NLP tasks',
    keywords: ['deep learning', 'NLP', 'transformers'],
    authors: [{ author_id: 'author_3' }],
    year: 2019,
    field_of_study: 'Computer Science',
    cited_by_count: 120
  },
  {
    paper_id: 'paper_4',
    title: 'Quantum Computing and Future Technologies',
    abstract: 'Exploring quantum computing applications in solving complex scientific problems',
    keywords: ['quantum computing', 'algorithms', 'quantum mechanics'],
    authors: [{ author_id: 'author_4' }],
    year: 2022,
    field_of_study: 'Physics',
    cited_by_count: 32
  },
  {
    paper_id: 'paper_5',
    title: 'Biological Networks and Systems Biology',
    abstract: 'Analysis of biological networks using graph theory and systems biology approaches',
    keywords: ['systems biology', 'networks', 'protein interactions'],
    authors: [{ author_id: 'author_5' }],
    year: 2020,
    field_of_study: 'Biology',
    cited_by_count: 67
  }
];

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { query } = body;

    if (!query || typeof query !== 'string' || query.trim().length === 0) {
      return NextResponse.json({ results: [] });
    }

    const searchQuery = query.toLowerCase().trim();

    // Search through sample papers
    const results = SAMPLE_PAPERS
      .filter((node: Node) => {
        const title = node.title?.toLowerCase() || '';
        const abstract = node.abstract?.toLowerCase() || '';
        const keywords = (node.keywords || []).map((k: string) => k.toLowerCase()).join(' ');

        return (
          title.includes(searchQuery) ||
          abstract.includes(searchQuery) ||
          keywords.includes(searchQuery)
        );
      })
      .slice(0, 50)
      .map((node: Node) => ({
        paper_id: node.paper_id,
        title: node.title,
        year: node.year,
        field_of_study: node.field_of_study,
        cited_by_count: node.cited_by_count,
        authors: node.authors,
      }));

    return NextResponse.json({ results, note: 'Currently using sample data. Run: npm run optimize for full dataset' });
  } catch (err) {
    console.error('[v0] Search error:', err);
    return NextResponse.json(
      { error: 'Search failed', results: [] },
      { status: 500 }
    );
  }
}
