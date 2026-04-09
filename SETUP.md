# Citation Network Visualization - Setup Guide

## Prerequisites

- Node.js 18+ and npm/pnpm/yarn
- Python 3.8+
- Your JSON data files in `output_filtered/modified_per_year/`

## Installation

### 1. Install Node.js Dependencies

```bash
npm install
# or
pnpm install
# or
yarn install
```

### 2. Install Python Dependencies

```bash
pip install networkx
```

## Running the Data Pipeline

### Step 1: Extract Graph Data

Extract nodes and edges from your JSON files:

```bash
npm run extract
# or
python scripts/citation_network/extract_graph_data.py
```

This will:
- Stream through all JSON files in `output_filtered/modified_per_year/`
- Extract paper metadata and references
- Output to `public/data/nodes.jsonl` and `public/data/edges.jsonl`

**Expected output**: JSON object with node_count, edge_count, file paths

### Step 2: Process Graph

Process the extracted data to calculate metrics, detect communities, and build search index:

```bash
npm run process
# or
python scripts/citation_network/process_graph.py
```

This will:
- Load extracted nodes and edges
- Detect research clusters using Louvain community detection
- Calculate citation metrics
- Build full-text search index
- Output optimized `public/data/processed_graph.json` and `public/data/search_index.json`

**Expected output**: JSON object with status, node count, edge count, cluster count

## Running the Web Application

After completing the data pipeline:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Features

### Visualization
- **Interactive Network**: Zoom, pan, and explore the citation network
- **Node Sizing**: Papers sized by citation count
- **Node Coloring**: Colored by research cluster (detected via community detection)

### Interaction
- **Click Nodes**: View detailed paper information
- **Search**: Find papers by title, abstract, keywords, or author
- **Filters**:
  - Publication year range
  - Research clusters
  - Text search

### Paper Details Panel
Shows comprehensive information:
- Title, abstract, keywords
- Authors with affiliations and countries
- Citation metrics and references
- Journal/venue information
- DOI and PDF links
- Publication type and publisher

## Project Structure

```
/vercel/share/v0-project/
├── app/
│   ├── api/
│   │   └── search/
│   │       └── route.ts          # Search API endpoint
│   ├── components/
│   │   ├── CitationNetworkVisualization.tsx  # Main Sigma.js visualization
│   │   ├── SearchPanel.tsx       # Search component
│   │   ├── FilterPanel.tsx       # Filter controls
│   │   └── PaperDetails.tsx      # Paper detail panel
│   ├── globals.css               # Global styles
│   ├── layout.tsx                # Root layout
│   └── page.tsx                  # Main page
├── public/
│   └── data/
│       ├── nodes.jsonl           # Extracted nodes (generated)
│       ├── edges.jsonl           # Extracted edges (generated)
│       ├── processed_graph.json   # Final graph data (generated)
│       └── search_index.json      # Search index (generated)
├── scripts/
│   └── citation_network/
│       ├── extract_graph_data.py  # Data extraction script
│       └── process_graph.py       # Graph processing script
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
└── postcss.config.js
```

## Data Files

### nodes.jsonl
Streaming JSON format with one paper per line:
```json
{
  "paper_id": "W4235678817",
  "title": "...",
  "authors": [...],
  "year": 2023,
  "cited_by_count": 150,
  "doi": "...",
  "abstract": "...",
  "field_of_study": "Computer Science",
  "keywords": [...],
  "references": [...]
}
```

### processed_graph.json
Optimized graph for visualization:
```json
{
  "nodes": [...],
  "edges": [...],
  "clusters": {...},
  "statistics": {
    "total_nodes": 42000000,
    "total_edges": 500000000,
    "total_clusters": 150,
    "years": {"min": 1900, "max": 2024}
  }
}
```

## Troubleshooting

### "Graph data not found" error
- Ensure extraction and processing scripts were run successfully
- Check that `public/data/processed_graph.json` exists

### Slow extraction/processing
- For large datasets (42M papers), this can take several hours
- Consider running on a machine with sufficient RAM
- Monitor console output for progress

### Search not working
- Ensure search_index.json was generated
- Check browser console for API errors

### Visualization not rendering
- Ensure Sigma.js is properly installed
- Check browser console for WebGL errors
- Try updating your browser

## Performance Notes

- **Node Count**: 42M+ papers
- **Edge Count**: ~500M+ citations
- **Memory**: Processing may require 8GB+ RAM
- **Frontend**: Sigma.js WebGL rendering handles large networks efficiently
- **Data**: JSONL format for streaming-friendly extraction

## Deployment

To deploy to Vercel:

1. Push your code to GitHub
2. Create a new Vercel project
3. Set root directory to `./`
4. Build command: `npm run build`
5. Install command: `npm install`
6. Output directory: `.next`

Note: You'll need to run the Python scripts locally and commit the generated `public/data/` files to your repository, or run them as part of your build process using a custom build script.

## License

See main project LICENSE file.
