# Complete Execution Guide: Citation Network Pipeline

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Pre-Execution Setup](#pre-execution-setup)
3. [Stage 1-2: Graph Construction](#stage-1-2-graph-construction)
4. [Stage 3-5: GPU Analysis and Export](#stage-3-5-gpu-analysis-and-export)
5. [Web Visualization Deployment](#web-visualization-deployment)
6. [Data Verification](#data-verification)
7. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Hardware Requirements
- **CPU:** Multi-core processor (4+ cores recommended)
- **RAM:** Minimum 16GB for graph construction; 32GB for full pipeline
- **Storage:** SSD with 50GB free space for database and exports
- **GPU:** NVIDIA GPU with CUDA Compute Capability 3.0+ (for Stages 3-5 only)

### Software Dependencies

#### Core Dependencies
```
Python 3.8+
SQLite3
NumPy
Pandas
NetworkX
```

#### GPU Dependencies (Stages 3-5)
```
CUDA 11.0+
cuGraph
cuDF
PyTorch
```

#### Web Visualization Dependencies (Optional)
```
Node.js (for HTTP server)
or Python 3.6+ (for built-in HTTP server)
```

---

## Pre-Execution Setup

### Step 1: Verify Python Installation
```bash
python --version
python -m pip --version
```

### Step 2: Install Required Packages
```bash
pip install numpy pandas networkx
```

### Step 3: For GPU Stages (Optional)
```bash
pip install cudf-cu11 cugraph pytorch-cuda
```

### Step 4: Prepare Input Data
Ensure JSON paper files are in the designated input directory:
```bash
ls /path/to/papers/*.json
# Should list paper JSON files
```

### Step 5: Create Output Directories
```bash
mkdir -p ./exports
mkdir -p ./logs
```

---

## Stage 1-2: Graph Construction

### Minimal Execution
```bash
cd scripts/citation_network_gpu
python main_stages_1_2.py --input-dir /path/to/papers --reset-db
```

### Full-Featured Execution
```bash
cd scripts/citation_network_gpu
python main_stages_1_2.py \
  --input-dir /path/to/papers \
  --db-path citation_network.db \
  --reset-db \
  --batch-size 5000 \
  --verbose
```

### Option Explanation

| Option | Values | Default | Purpose |
|--------|--------|---------|---------|
| `--input-dir` | PATH | Required | Location of JSON input files |
| `--db-path` | PATH | citation_network.db | SQLite database file location |
| `--reset-db` | Flag | False | Drop existing tables and start fresh |
| `--batch-size` | INTEGER | 10000 | Records processed per batch |
| `--verbose` | Flag | False | Enable detailed logging |

### Post-Execution Verification

#### Check Node Count
```bash
sqlite3 citation_network.db "SELECT COUNT(*) as node_count FROM graph_nodes;"
```

#### Check Edge Count
```bash
sqlite3 citation_network.db "SELECT COUNT(*) as edge_count FROM graph_edges;"
```

#### Check Mapping Tables
```bash
sqlite3 citation_network.db "SELECT COUNT(*) as paper_mappings FROM paper_id_mapping;"
sqlite3 citation_network.db "SELECT COUNT(*) as field_mappings FROM field_of_study_mapping;"
```

#### Sample Node Data
```bash
sqlite3 citation_network.db "SELECT * FROM graph_nodes LIMIT 5;"
```

#### Check for Isolated Papers Removed
```bash
sqlite3 citation_network.db "SELECT COUNT(*) as isolated FROM graph_nodes WHERE in_degree=0 AND out_degree=0;"
```

---

## Stage 3-5: GPU Analysis and Export

### Prerequisites
- Stage 1-2 must be completed first
- Database file `citation_network.db` must exist
- GPU with CUDA support available
- cuGraph and cuDF installed

### Minimal Execution
```bash
cd scripts/citation_network_gpu
python main_stages_3_5.py
```

### Full-Featured Execution
```bash
cd scripts/citation_network_gpu
python main_stages_3_5.py \
  --db-path citation_network.db \
  --gpu-id 0 \
  --layout-algorithm forceatlas2 \
  --layout-iterations 100 \
  --export-dir ./exports \
  --export-batch-size 10000 \
  --verbose
```

### Option Explanation

| Option | Values | Default | Purpose |
|--------|--------|---------|---------|
| `--db-path` | PATH | citation_network.db | Database file location |
| `--gpu-id` | INTEGER | 0 | GPU device ID to use |
| `--layout-algorithm` | forceatlas2, spring, kamada-kawai | forceatlas2 | Graph layout algorithm |
| `--layout-iterations` | INTEGER | 100 | Number of layout iterations |
| `--export-dir` | PATH | ./exports | Output directory for JSON files |
| `--export-batch-size` | INTEGER | 10000 | Records per export batch |
| `--force-recompute` | Flag | False | Ignore checkpoints and recompute |
| `--skip-export` | Flag | False | Skip export, compute analysis only |
| `--verbose` | Flag | False | Enable detailed logging |

### Post-Execution Verification

#### Check Community Detection
```bash
sqlite3 citation_network.db "SELECT COUNT(DISTINCT community_id) as num_communities FROM communities;"
```

#### Check Layout Coordinates
```bash
sqlite3 citation_network.db "SELECT COUNT(*) as nodes_with_coordinates FROM layout_coordinates WHERE x IS NOT NULL AND y IS NOT NULL;"
```

#### Verify Export Files
```bash
ls -lah exports/
file exports/*.json
```

#### Sample Export Data
```bash
head -100 exports/graph_nodes.json
head -100 exports/graph_edges.json
```

---

## Complete Pipeline Execution

### Full Workflow from Start to Finish

```bash
# Set variables for convenience
INPUT_DIR="/path/to/papers"
DB_PATH="citation_network.db"
EXPORT_DIR="./exports"
GPU_ID=0

# Navigate to working directory
cd scripts/citation_network_gpu

# ==============================================================================
# STAGE 1-2: GRAPH CONSTRUCTION (CPU-BASED)
# ==============================================================================
echo "Starting Stage 1-2: Graph Construction..."

python main_stages_1_2.py \
  --input-dir "$INPUT_DIR" \
  --db-path "$DB_PATH" \
  --reset-db \
  --batch-size 5000 \
  --verbose

# Verify Stage 1-2 completion
echo "Verifying Stage 1-2 output..."
sqlite3 "$DB_PATH" "SELECT 'Nodes:' as metric, COUNT(*) as count FROM graph_nodes UNION SELECT 'Edges:', COUNT(*) FROM graph_edges UNION SELECT 'Paper Mappings:', COUNT(*) FROM paper_id_mapping;"

# ==============================================================================
# STAGE 3-5: GPU ANALYSIS AND EXPORT
# ==============================================================================
echo "Starting Stage 3-5: GPU Analysis and Export..."

python main_stages_3_5.py \
  --db-path "$DB_PATH" \
  --gpu-id "$GPU_ID" \
  --layout-algorithm forceatlas2 \
  --layout-iterations 100 \
  --export-dir "$EXPORT_DIR" \
  --export-batch-size 10000 \
  --verbose

# Verify Stage 3-5 completion
echo "Verifying Stage 3-5 output..."
sqlite3 "$DB_PATH" "SELECT 'Communities:' as metric, COUNT(DISTINCT community_id) as count FROM communities UNION SELECT 'Coordinates:', COUNT(*) FROM layout_coordinates;"

# List exported files
echo "Exported files:"
ls -lah "$EXPORT_DIR"

echo "Pipeline execution complete."
```

### Alternative: Graph-Only Mode (No GPU)

For testing without GPU execution:

```bash
cd scripts/citation_network_gpu

python main_stages_1_2.py \
  --input-dir /path/to/papers \
  --db-path citation_network.db \
  --reset-db

# Verify results
sqlite3 citation_network.db "SELECT COUNT(*) as nodes FROM graph_nodes;"
```

### Alternative: Recompute with Different Layout

To regenerate layout with different algorithm:

```bash
cd scripts/citation_network_gpu

python main_stages_3_5.py \
  --db-path citation_network.db \
  --gpu-id 0 \
  --layout-algorithm spring \
  --layout-iterations 150 \
  --export-dir ./exports \
  --force-recompute \
  --verbose
```

---

## Web Visualization Deployment

### Option 1: Python Built-in Server (No Installation Required)

```bash
# Navigate to exports directory
cd exports

# Start HTTP server on port 8000
python -m http.server 8000

# Access visualization
# Open browser and go to: http://localhost:8000
```

To stop the server, press `Ctrl+C` in the terminal.

### Option 2: Node.js HTTP Server

#### Install HTTP Server
```bash
npm install -g http-server
```

#### Run Server
```bash
cd exports
http-server -p 8000 -o
```

This will automatically open the default browser.

### Option 3: Direct File Access

Open the visualization HTML file directly in a web browser:

```bash
# macOS
open exports/index.html

# Linux
xdg-open exports/index.html

# Windows
start exports/index.html
```

### Option 4: Docker Container (If Dockerfile Exists)

```bash
# Build Docker image
docker build -t citation-network-viz .

# Run container with port mapping
docker run -d -p 8000:8000 \
  -v $(pwd)/exports:/app/data \
  --name citation-viz \
  citation-network-viz

# Access visualization
# Open browser and go to: http://localhost:8000

# Stop container
docker stop citation-viz
docker rm citation-viz
```

### Verification of Visualization Deployment

#### Check Required Files
```bash
# Verify all necessary files exist
ls -lah exports/index.html
ls -lah exports/graph_nodes.json
ls -lah exports/graph_edges.json
ls -lah exports/communities.json
ls -lah exports/layout_coords.json
```

#### Verify File Integrity
```bash
# Check JSON validity
python -m json.tool exports/graph_nodes.json > /dev/null && echo "graph_nodes.json is valid"
python -m json.tool exports/graph_edges.json > /dev/null && echo "graph_edges.json is valid"
```

#### Test Server Connectivity
```bash
# Test HTTP server response
curl -I http://localhost:8000/index.html

# Fetch and verify graph data
curl http://localhost:8000/graph_nodes.json | head -c 500
```

---

## Data Verification

### Database Integrity Check

```bash
# Check database file size
ls -lah citation_network.db

# Verify database is not corrupted
sqlite3 citation_network.db "PRAGMA integrity_check;"

# List all tables
sqlite3 citation_network.db ".tables"

# Check table row counts
sqlite3 citation_network.db << EOF
SELECT 'graph_nodes' as table_name, COUNT(*) as row_count FROM graph_nodes
UNION ALL
SELECT 'graph_edges', COUNT(*) FROM graph_edges
UNION ALL
SELECT 'paper_metadata', COUNT(*) FROM paper_metadata
UNION ALL
SELECT 'paper_id_mapping', COUNT(*) FROM paper_id_mapping
UNION ALL
SELECT 'field_of_study_mapping', COUNT(*) FROM field_of_study_mapping
UNION ALL
SELECT 'communities', COUNT(*) FROM communities
UNION ALL
SELECT 'layout_coordinates', COUNT(*) FROM layout_coordinates;
EOF
```

### Data Quality Checks

#### Verify No Missing Mappings
```bash
# Check for unmapped nodes
sqlite3 citation_network.db "SELECT COUNT(*) as unmapped_nodes FROM graph_nodes WHERE node_id NOT IN (SELECT node_id FROM paper_id_mapping);"
```

#### Verify Graph Connectivity
```bash
# Check for orphaned edges
sqlite3 citation_network.db "SELECT COUNT(*) as orphaned_edges FROM graph_edges WHERE source_id NOT IN (SELECT node_id FROM graph_nodes) OR target_id NOT IN (SELECT node_id FROM graph_nodes);"
```

#### Verify Complete Layout
```bash
# Check for nodes without coordinates
sqlite3 citation_network.db "SELECT COUNT(*) as missing_coordinates FROM graph_nodes WHERE node_id NOT IN (SELECT node_id FROM layout_coordinates);"
```

### Export File Verification

```bash
# Check export file sizes
du -h exports/*.json

# Verify JSON formatting
for file in exports/*.json; do
  echo "Checking $file..."
  python -m json.tool "$file" > /dev/null 2>&1 && echo "  Valid" || echo "  ERROR"
done

# Sample export content
echo "Sample nodes:"
head -5 exports/graph_nodes.json

echo "Sample edges:"
head -5 exports/graph_edges.json
```

---

## Troubleshooting

### Problem: Database File Locked
**Symptom:** Error message "database is locked"
**Solution:**
```bash
# Ensure no other processes are using the database
lsof | grep citation_network.db

# If processes exist, terminate them
kill -9 <PID>

# Verify no process holds the lock
sqlite3 citation_network.db "SELECT 1;"
```

### Problem: Out of Memory During Execution
**Symptom:** Memory allocation errors
**Solution:**
```bash
# Reduce batch size
python main_stages_1_2.py --input-dir /data/papers --batch-size 2000

# Or increase system swap
sudo swapon --show
```

### Problem: GPU Memory Insufficient
**Symptom:** CUDA out of memory errors
**Solution:**
```bash
# Use smaller batch size for exports
python main_stages_3_5.py --export-batch-size 5000

# Or reduce layout iterations
python main_stages_3_5.py --layout-iterations 50
```

### Problem: Missing Input Files
**Symptom:** "Input directory not found" error
**Solution:**
```bash
# Verify input directory exists
ls -la /path/to/papers

# Verify JSON files are present
ls /path/to/papers/*.json | wc -l

# Check file format
file /path/to/papers/*.json
```

### Problem: Web Visualization Not Loading
**Symptom:** Blank page or JavaScript errors
**Solution:**
```bash
# Verify export files exist
ls -la exports/

# Verify JSON files are valid
python -m json.tool exports/graph_nodes.json > /dev/null

# Check server is running on correct port
netstat -tuln | grep 8000

# Check browser console for errors (F12 in browser)
```

### Problem: Slow Performance
**Symptom:** Execution takes longer than expected
**Solution:**
```bash
# Use verbose mode to identify bottleneck
python main_stages_1_2.py --input-dir /data/papers --verbose

# Increase batch size for faster processing
python main_stages_1_2.py --input-dir /data/papers --batch-size 15000

# Ensure no other resource-intensive processes are running
top
```

---

## Summary

The Citation Network pipeline provides a comprehensive framework for analyzing citation networks through two independent entry points:

1. **Stages 1-2:** Graph construction (CPU-based, independent)
2. **Stages 3-5:** Analysis and export (GPU-accelerated)

Execute the complete pipeline using the commands provided in this guide, with verification steps to ensure correctness at each stage. Web visualization is available through multiple deployment options for analysis and presentation of results.
