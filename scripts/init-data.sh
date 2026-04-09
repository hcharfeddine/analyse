#!/bin/bash

# Citation Network Visualization - Data Initialization Script
# This script runs the data extraction and processing pipeline

set -e

echo "========================================"
echo "Citation Network Visualization"
echo "Data Initialization Pipeline"
echo "========================================"
echo ""

# Check if output_filtered directory exists
if [ ! -d "output_filtered/modified_per_year" ]; then
    echo "❌ Error: output_filtered/modified_per_year directory not found"
    echo ""
    echo "Please ensure your JSON data files are in: output_filtered/modified_per_year/"
    exit 1
fi

echo "✓ Data directory found"
echo ""

# Create output directory
mkdir -p public/data
echo "✓ Output directory created"
echo ""

# Step 1: Extract graph data
echo "========================================"
echo "Step 1: Extracting graph data..."
echo "========================================"
echo ""

if command -v python3 &> /dev/null; then
    python3 scripts/citation_network/extract_graph_data.py
elif command -v python &> /dev/null; then
    python scripts/citation_network/extract_graph_data.py
else
    echo "❌ Error: Python not found"
    exit 1
fi

echo ""
echo "✓ Graph data extracted"
echo ""

# Step 2: Process graph
echo "========================================"
echo "Step 2: Processing graph..."
echo "========================================"
echo ""

if command -v python3 &> /dev/null; then
    python3 scripts/citation_network/process_graph.py
elif command -v python &> /dev/null; then
    python scripts/citation_network/process_graph.py
else
    echo "❌ Error: Python not found"
    exit 1
fi

echo ""
echo "✓ Graph processed"
echo ""

# Verify output files
echo "========================================"
echo "Verifying output files..."
echo "========================================"
echo ""

if [ -f "public/data/processed_graph.json" ]; then
    echo "✓ processed_graph.json created"
    NODE_COUNT=$(grep -o '"paper_id"' public/data/processed_graph.json | wc -l)
    echo "  - Contains ~$NODE_COUNT nodes"
else
    echo "❌ processed_graph.json not found"
    exit 1
fi

if [ -f "public/data/search_index.json" ]; then
    echo "✓ search_index.json created"
else
    echo "❌ search_index.json not found"
    exit 1
fi

echo ""
echo "========================================"
echo "✓ Data initialization complete!"
echo "========================================"
echo ""
echo "You can now run the web server:"
echo "  npm run dev"
echo ""
echo "Then open http://localhost:3000 in your browser"
echo ""
