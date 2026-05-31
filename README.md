# Citation Network — Complete Setup Guide

End-to-end guide: raw paper JSON files → fully running web visualization.

---

## Table of Contents

1. [Server Requirements](#1-server-requirements)
2. [Clone the Repository](#2-clone-the-repository)
3. [Paper Data — Format & Directory](#3-paper-data--format--directory)
4. [Handle Large Files: Subsets & Auto-Chunking](#4-handle-large-files-subsets--auto-chunking)
5. [Python Environment](#5-python-environment)
6. [Install Python Dependencies](#6-install-python-dependencies)
7. [GPU Setup (RAPIDS — Critical for Performance)](#7-gpu-setup-rapids--critical-for-performance)
8. [Pipeline: Stage 1–2 — Ingest & Deduplicate](#8-pipeline-stage-12--ingest--deduplicate)
9. [Pipeline: Stage 3–5 — Community, Layout & Export](#9-pipeline-stage-35--community-layout--export)
10. [Verify Pipeline Output](#10-verify-pipeline-output)
11. [Run the Web App](#11-run-the-web-app)
12. [Run in Background (Long Jobs)](#12-run-in-background-long-jobs)
13. [Monitor Progress](#13-monitor-progress)
14. [Troubleshooting](#14-troubleshooting)
15. [Quick Reference — All Commands](#15-quick-reference--all-commands)

---

## 1. Server Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| **RAM** | 16 GB | 32+ GB (NodeMapping uses 3–6 GB for 54M papers) |
| **CPU** | 8 cores | 16+ cores (Stage 1 parse workers scale with cores) |
| **GPU** | Optional | NVIDIA RTX / A-series with CUDA 11.8+ (Stage 3–4) |
| **VRAM** | — | 20+ GB per GPU for 54M-paper graphs |
| **Disk** | 200 GB free | 500+ GB free (DB + raw JSON + chunks) |
| **Python** | 3.9+ | 3.11 |

```bash
# Verify before starting
python3 --version          # need 3.9+
nvcc --version             # CUDA version (11.x or 12.x)
nvidia-smi                 # GPU count and VRAM
free -h                    # available RAM
df -h /                    # free disk space
```

---

## 2. Clone the Repository

```bash
git clone https://github.com/hcharfeddine/Citation_Network.git
cd Citation_Network
```

The project layout:

```
Citation_Network/
├── citation_network_gpu/       ← Python pipeline (all 5 stages)
│   ├── main_stages_1_2.py      ← run Stage 1 + 2
│   ├── main_stages_3_5.py      ← run Stage 3 + 4 + 5
│   ├── main.py                 ← run all 5 stages at once
│   ├── auto_chunk.py           ← automatic 500 MB file splitter
│   ├── make_subset.py          ← create representative subsets for testing
│   ├── config.py               ← PipelineConfig dataclass + CLI args
│   ├── stage_1_ingest.py       ← JSON → SQLite (producer-consumer)
│   ├── stage_2_deduplicate.py  ← remove duplicate edges
│   ├── stage_3_community.py    ← GPU Louvain community detection
│   ├── stage_4_layout.py       ← GPU ForceAtlas2 / igraph DRL layout
│   ├── stage_5_export.py       ← export graph_preview.json
│   └── utils/                  ← checkpoint, node_mapping, data_loader, ...
├── artifacts/
│   ├── citation-network/       ← React + Vite frontend
│   └── api-server/             ← Express 5 API server
└── public/data/                ← pipeline writes final output here
```

---

## 3. Paper Data — Format & Directory

### Expected directory layout

```
data/papers/
├── 1990.json
├── 1991.json
├── ...
├── 2023.json
└── 2024.json
```

Files can be named anything — the pipeline reads all `.json` files from the directory.
The year filter in `make_subset.py` extracts the year from the filename (e.g. `2020.json`).

### Each file is a JSON array of paper objects

```json
[
  {
    "id": "paper_abc123",
    "title": "Deep Learning for Graph Analysis",
    "authors": ["Alice Smith", "Bob Jones"],
    "year": 2020,
    "abstract": "We propose a novel...",
    "field_of_study": "Computer Science",
    "cited_by_count": 142,
    "citations": ["paper_def456", "paper_ghi789"]
  }
]
```

**Required fields:** `id`, `citations`
**Optional but used:** `title`, `authors`, `year`, `abstract`, `field_of_study`, `cited_by_count`

```bash
mkdir -p data/papers

# Verify your files are readable
python3 -c "
import json, pathlib
f = list(pathlib.Path('data/papers').glob('*.json'))[0]
papers = json.load(open(f))
print(f'First file: {f.name}  |  {len(papers):,} papers')
print('Keys:', list(papers[0].keys()))
"
```

---

## 4. Handle Large Files: Subsets & Auto-Chunking

> **Why this matters:** Files from 2000–2024 are often 2–14 GB each. The pipeline
> auto-chunks anything over 500 MB at startup, but creating year-filtered subsets
> first is the fastest way to benchmark and verify your setup before a full run.

### Option A — Create subsets first (recommended for testing)

`make_subset.py` reads a fraction of each file so you can test the full pipeline
end-to-end in minutes instead of hours.

```bash
cd citation_network_gpu

# Subset all files from year 2000 onward → writes *_sample.json next to originals
python make_subset.py --input-dir ../data/papers/ --year-min 2000

# Subset all files >= 2 GB (2000 MB threshold)
python make_subset.py --input-dir ../data/papers/ --min-size 2000

# Subset years 2000–2024, output to a separate folder (keeps originals untouched)
python make_subset.py \
    --input-dir ../data/papers/ \
    --year-min 2000 --year-max 2024 \
    --output-dir /tmp/subsets/

# Single file
python make_subset.py \
    --input ../data/papers/2020.json \
    --output /tmp/2020_sample.json
```

Typical output:

```
File                      Source     Subset    Papers
------------------------------------------------------
2020.json                 9.2 GB     499 MB    3,400,000
2021.json                11.4 GB     499 MB    3,900,000
2022.json                13.0 GB     500 MB    4,200,000
```

Then run the pipeline on the subsets to validate before committing to a full run:

```bash
python main_stages_1_2.py --input-dir /tmp/subsets/ --no-auto-chunk
```

### Option B — Auto-chunking (built into the pipeline)

Any file over 500 MB is **automatically split** into <=500 MB chunks before
Stage 1 starts. The original file is replaced by `*_chunk_000.json`, `*_chunk_001.json`, etc.

```bash
# Auto-chunk runs by default — no flags needed
python main_stages_1_2.py --input-dir ../data/papers/

# Disable if files are already chunked
python main_stages_1_2.py --input-dir ../data/papers/ --no-auto-chunk

# Custom chunk size (default 500 MB)
python main_stages_1_2.py --input-dir ../data/papers/ --chunk-size 250
```

You can also chunk manually without running the pipeline:

```bash
python auto_chunk.py --input-dir ../data/papers/ --max-mb 500
```

---

## 5. Python Environment

```bash
cd citation_network_gpu

# Create isolated environment
python3 -m venv venv

# Activate (Linux / macOS)
source venv/bin/activate

# Confirm
which python        # should end with .../venv/bin/python
python --version    # 3.9+
```

---

## 6. Install Python Dependencies

```bash
# Always activate the environment first
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install CPU / base packages
pip install -r requirements.txt

# Verify critical imports
python -c "import orjson;   print('OK orjson')"
python -c "import igraph;   print('OK igraph')"
python -c "import networkx; print('OK networkx')"
python -c "import sqlite3;  print('OK sqlite3')"
```

Key packages in `requirements.txt`:

| Package | Purpose |
|---|---|
| `orjson` | 5–10x faster JSON parsing than stdlib json |
| `igraph` | CPU layout (DRL) — fast multi-threaded fallback for Stage 4 |
| `python-louvain` | CPU Louvain community detection fallback for Stage 3 |
| `networkx` | Graph utilities |
| `torch` | GPU tensor support (install separately — see next section) |

---

## 7. GPU Setup (RAPIDS — Critical for Performance)

> Without GPU acceleration, Stage 3 (community detection) and Stage 4 (layout)
> fall back to CPU. CPU works for graphs under ~1M nodes; for 54M papers it takes
> days instead of hours. Stages 1 and 2 are CPU-only regardless.

### Step 1 — Install PyTorch for your CUDA version

```bash
# Check your CUDA version
nvcc --version
# e.g. "Cuda compilation tools, release 12.1"

# CUDA 12.x (RTX 4090, A100, H100)
pip install torch --index-url https://download.pytorch.org/whl/cu121

# CUDA 11.x
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Step 2 — Install RAPIDS (cuDF + cuGraph)

```bash
# CUDA 12.x
pip install --extra-index-url=https://pypi.nvidia.com cugraph-cu12 cuml-cu12

# CUDA 11.x
pip install --extra-index-url=https://pypi.nvidia.com cugraph-cu11 cuml-cu11
```

### Step 3 — Verify

```bash
python diagnose_gpu.py

# Expected output:
#   OK  CUDA available — N GPU(s) detected
#   OK  RAPIDS cudf + cugraph available
#   OK  GPU ForceAtlas2 (Stage 4) ready
```

If `diagnose_gpu.py` reports issues, the pipeline still runs — it falls back to
`igraph DRL` (CPU, multi-threaded) for layout and `python-louvain` for community
detection automatically. No configuration needed.

---

## 8. Pipeline: Stage 1–2 — Ingest & Deduplicate

### What each stage does

| Stage | What it does | Output |
|---|---|---|
| **Stage 1** | Parse JSON files into SQLite (`graph_nodes`, `paper_metadata`, `graph_edges`). | `citation_network.db` |
| **Stage 2** | Remove duplicate `(source, target)` edge pairs, recount degrees via GROUP BY. | Updated `graph_edges` |

### Architecture — why Stage 1 is fast

Stage 1 uses a **producer-consumer** pattern:

- **N parse workers** (one per CPU core, capped at file count): pure JSON parsing + in-memory node ID mapping. Fully parallel. Zero SQLite access.
- **1 write thread**: the sole owner of the SQLite connection. No lock contention, no `database is locked` errors. Parse workers back-pressure automatically via a bounded queue (64 slots).
- `PRAGMA synchronous=OFF` during bulk ingest (3–5x faster writes). Automatically restored to `NORMAL` when ingest finishes. Safe — data can always be regenerated from source files.

### Run Stage 1 + 2

```bash
cd citation_network_gpu
source venv/bin/activate

# Basic run (auto-chunk is on by default)
python main_stages_1_2.py \
    --input-dir ../data/papers/ \
    --db-path ../public/data/citation_network.db

# All options
python main_stages_1_2.py \
    --input-dir ../data/papers/ \
    --db-path ../public/data/citation_network.db \
    --batch-size 10000 \      # papers per internal flush batch (default 10000)
    --chunk-size 500 \        # auto-chunk threshold in MB (default 500)
    --no-auto-chunk \         # skip auto-chunking if files are already split
    --reset-db                # wipe DB and start from scratch
```

### Checkpoint / resume

Stage 1 checkpoints after every file. If the process is killed or crashes, restart
with the exact same command — already-processed files are skipped automatically.

```bash
# Resume after crash (default behaviour — no flag needed)
python main_stages_1_2.py \
    --input-dir ../data/papers/ \
    --db-path ../public/data/citation_network.db

# Force a full restart (wipes DB)
python main_stages_1_2.py \
    --input-dir ../data/papers/ \
    --db-path ../public/data/citation_network.db \
    --reset-db
```

### Expected timing

| Scale | Parse workers | Stage 1 | Stage 2 |
|---|---|---|---|
| 1 year file (~500 MB subset) | 1 | 5–10 min | 1–2 min |
| 10 year files (~5 GB subsets) | 8–10 | 30–60 min | 5–10 min |
| Full 2000–2024 (54M papers, 2–14 GB/file) | 16 | 3–6 h | 30–60 min |

### Quick check after Stage 1–2

```bash
sqlite3 ../public/data/citation_network.db "
  SELECT 'nodes',             COUNT(*) FROM graph_nodes;
  SELECT 'edges',             COUNT(*) FROM graph_edges;
  SELECT 'metadata rows',     COUNT(*) FROM paper_metadata;
  SELECT 'files processed',   COUNT(*) FROM processed_files;
"
```

---

## 9. Pipeline: Stage 3–5 — Community, Layout & Export

### What each stage does

| Stage | What it does | GPU? | Output |
|---|---|---|---|
| **Stage 3** | Louvain community detection — groups papers into research clusters | Yes (cuGraph) | `community_id` column in `graph_nodes` |
| **Stage 4** | ForceAtlas2 / DRL layout — computes (x, y) position for every node | Yes (cuGraph) | `x`, `y` columns in `graph_nodes` |
| **Stage 5** | Export top N nodes + edges to `graph_preview.json` for the browser | No | `public/data/graph_preview.json` |

### Run Stage 3 + 4 + 5

```bash
cd citation_network_gpu
source venv/bin/activate

# Standard run (GPU 0 by default)
python main_stages_3_5.py \
    --db-path ../public/data/citation_network.db \
    --export-dir ../public/data/

# Use a specific GPU
python main_stages_3_5.py --db-path ../public/data/citation_network.db --gpu-id 1

# Force recompute (ignore existing checkpoints)
python main_stages_3_5.py --db-path ../public/data/citation_network.db --force-recompute

# Skip export (only redo community + layout)
python main_stages_3_5.py --db-path ../public/data/citation_network.db --skip-export
```

### GPU fallback chain (automatic — no config needed)

```
cuGraph ForceAtlas2 (GPU)          ← preferred; handles 100M+ nodes
    if unavailable:
Batched Fruchterman-Reingold (GPU) ← tiled to avoid OOM on large graphs
    if unavailable:
igraph DRL (CPU, multi-threaded)   ← best CPU option for large graphs
```

### Run all 5 stages in one command

```bash
python main.py \
    --input-dir ../data/papers/ \
    --db ../public/data/citation_network.db \
    --num-gpus 8 \
    --verbose
```

---

## 10. Verify Pipeline Output

```bash
# 1. Database integrity
sqlite3 public/data/citation_network.db "PRAGMA integrity_check;"
# Should print: ok

# 2. Counts
sqlite3 public/data/citation_network.db "
  SELECT 'nodes',              COUNT(*)                   FROM graph_nodes;
  SELECT 'edges',              COUNT(*)                   FROM graph_edges;
  SELECT 'communities',        COUNT(DISTINCT community_id) FROM graph_nodes;
  SELECT 'nodes with layout',  COUNT(*) FROM graph_nodes WHERE x IS NOT NULL;
"

# 3. Inspect the export
python3 -c "
import json
data = json.load(open('public/data/graph_preview.json'))
print(f'Nodes   : {len(data[\"nodes\"]):,}')
print(f'Edges   : {len(data[\"edges\"]):,}')
print(f'Clusters: {len(set(n[\"cluster\"] for n in data[\"nodes\"])):,}')
print(f'Size    : {len(json.dumps(data)) / 1e6:.1f} MB')
"

# 4. List generated files
ls -lh public/data/
# Should include:
#   citation_network.db
#   graph_preview.json
```

---

## 11. Run the Web App

The web app has two parts: an **Express API server** and a **React + Vite frontend**.
Both must be running at the same time.

### File placement

The API server reads from `public/data/` at the project root:

```
Citation_Network/
└── public/
    └── data/
        ├── graph_preview.json       ← required (network graph view)
        ├── citation_network.db      ← required (search + paper details)
        └── map_manifest.json        ← optional (map view only)
```

If you ran Stage 5 with `--export-dir ../public/data/`, the files are already here.

### Terminal A — API Server (port 8080)

```bash
# From workspace root
pnpm --filter @workspace/api-server run dev
```

Expected:
```
[INFO] API server running on port 8080
[INFO] Loaded graph_preview.json — 500,000 nodes, 4,800,000 edges
```

Test the API:
```bash
curl http://localhost:8080/api/graph/stats
# {"nodeCount":500000,"edgeCount":4800000,"communities":12}

curl "http://localhost:8080/api/search?q=deep+learning"
# {"papers":[...]}
```

### Terminal B — Frontend (React + Vite)

```bash
# From workspace root
pnpm --filter @workspace/citation-network run dev
```

Open the URL shown in terminal output (e.g. `http://localhost:5173`).

### Available API routes

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/graph/stats` | Node / edge / community counts |
| `GET` | `/api/graph/nodes` | Paginated node list |
| `GET` | `/api/graph/nodes/:id` | Single node by integer ID |
| `GET` | `/api/graph/load` | Full preview graph JSON |
| `GET` | `/api/paper/:paperId` | Paper detail (title, abstract, authors, DOI) |
| `GET` | `/api/search?q=...` | Full-text search by title / abstract / keywords |
| `GET` | `/api/map/manifest` | Map tile manifest |
| `GET` | `/api/map/tile/:z/:x/:y` | Map tile image |

---

## 12. Run in Background (Long Jobs)

For a full 54M-paper run (3–10 hours), use one of these methods to survive
terminal disconnects.

### tmux (recommended)

```bash
# Create session
tmux new-session -d -s pipeline

# Attach to it
tmux attach -t pipeline

# Inside the session:
cd citation_network_gpu && source venv/bin/activate
python main_stages_1_2.py --input-dir ../data/papers/ --db-path ../public/data/citation_network.db

# Detach without killing: Ctrl+B then D
# Reattach later:
tmux attach -t pipeline
```

### nohup

```bash
cd citation_network_gpu && source venv/bin/activate

nohup python main_stages_1_2.py \
    --input-dir ../data/papers/ \
    --db-path ../public/data/citation_network.db \
    > stage12.log 2>&1 &

echo "PID: $!"
tail -f stage12.log
```

### screen

```bash
screen -S pipeline
source venv/bin/activate
python main_stages_1_2.py --input-dir ../data/papers/ --db-path ../public/data/citation_network.db
# Detach: Ctrl+A then D
# Reattach: screen -r pipeline
```

---

## 13. Monitor Progress

### GPU utilization (Stage 3–4)

```bash
# Live view (every 1 s)
watch -n 1 nvidia-smi

# Detailed per-process view
nvidia-smi dmon -s puctem

# You should see during Stage 3–4:
#   GPU Utilization : 80–99%
#   Memory-Usage    : growing steadily
```

If GPU utilization stays at 0%, RAPIDS did not install correctly — see [Troubleshooting](#14-troubleshooting).

### Database growth (Stage 1–2)

```bash
watch -n 5 'du -sh public/data/citation_network.db'
```

### Tail pipeline logs

```bash
tail -f citation_network_gpu/pipeline_stages_1_2.log
tail -f citation_network_gpu/pipeline_stages_3_5.log
```

### Live paper count

```bash
watch -n 10 'sqlite3 public/data/citation_network.db "SELECT COUNT(*) FROM graph_nodes;"'
```

### RAM usage

```bash
watch -n 2 free -h
```

---

## 14. Troubleshooting

### `database is locked`

**Cause:** A stale pipeline process is still holding the connection.

```bash
# Find and kill it
ps aux | grep "main_stages" | grep -v grep
pkill -f "main_stages_1_2.py"

# Verify DB is clean
sqlite3 public/data/citation_network.db "PRAGMA integrity_check;"
```

> With the producer-consumer architecture, `database is locked` should not occur
> during normal Stage 1 operation — only 1 thread ever writes to SQLite.

### `CUDA out of memory` during Stage 3–4

```bash
# Reduce GPU edge-loading batch size
python main_stages_3_5.py \
    --db-path ../public/data/citation_network.db \
    --batch-size 1000000    # 1M edges per GPU batch instead of default 5M
```

If OOM persists the pipeline falls back to CPU automatically.

### `ModuleNotFoundError`

```bash
# Check virtual environment is active
which python    # must show .../venv/bin/python

source venv/bin/activate
pip install -r requirements.txt
```

### Pipeline crashed mid-run — how to resume

Stage 1 checkpoints after every file. Restart with the same command:

```bash
python main_stages_1_2.py \
    --input-dir ../data/papers/ \
    --db-path ../public/data/citation_network.db
# Already-processed files are detected and skipped automatically.
```

Force a full restart (deletes existing DB):

```bash
python main_stages_1_2.py --input-dir ../data/papers/ --db-path ../public/data/citation_network.db --reset-db
```

Resume Stage 3–5 from a specific stage:

```bash
python main_stages_3_5.py \
    --db-path ../public/data/citation_network.db \
    --resume-from layout    # options: community | layout | export
```

### Graph preview is empty in the browser

1. Check `public/data/graph_preview.json` exists and has data:
   ```bash
   python3 -c "import json; d=json.load(open('public/data/graph_preview.json')); print(len(d['nodes']), 'nodes')"
   ```
2. Check the API server is running and responding:
   ```bash
   curl http://localhost:8080/api/graph/stats
   ```
3. Open browser DevTools → Console for JavaScript errors (usually a CORS or path mismatch).

### Out of disk space

```bash
df -h /

# Remove intermediate chunks after the full run completes
rm data/papers/*_chunk_*.json

# Move DB to a larger disk and symlink it back
mv public/data/citation_network.db /large-disk/
ln -s /large-disk/citation_network.db public/data/citation_network.db
```

### GPU not detected / RAPIDS missing

```bash
python diagnose_gpu.py

# Reinstall RAPIDS (note your CUDA version first)
nvcc --version

# CUDA 12.x
pip install --force-reinstall --extra-index-url=https://pypi.nvidia.com cugraph-cu12

# CUDA 11.x
pip install --force-reinstall --extra-index-url=https://pypi.nvidia.com cugraph-cu11
```

The pipeline still completes without GPU — it uses igraph DRL (CPU, multi-threaded)
for layout and python-louvain for community detection.

---

## 15. Quick Reference — All Commands

```bash
# ── Setup ────────────────────────────────────────────────────────────────────
git clone https://github.com/hcharfeddine/Citation_Network.git
cd Citation_Network/citation_network_gpu
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt

# GPU (CUDA 12.x)
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install --extra-index-url=https://pypi.nvidia.com cugraph-cu12 cuml-cu12

# GPU (CUDA 11.x)
pip install torch --index-url https://download.pytorch.org/whl/cu118
pip install --extra-index-url=https://pypi.nvidia.com cugraph-cu11 cuml-cu11

# Verify GPU
python diagnose_gpu.py

# ── (Optional) Create subsets for testing ────────────────────────────────────
python make_subset.py \
    --input-dir ../data/papers/ \
    --year-min 2000 --year-max 2024 \
    --output-dir /tmp/subsets/

# ── Stage 1 + 2: Ingest & Deduplicate ────────────────────────────────────────
python main_stages_1_2.py \
    --input-dir ../data/papers/ \
    --db-path ../public/data/citation_network.db

# ── Stage 3 + 4 + 5: Community, Layout & Export ──────────────────────────────
python main_stages_3_5.py \
    --db-path ../public/data/citation_network.db \
    --export-dir ../public/data/

# ── Or run all 5 stages at once ───────────────────────────────────────────────
python main.py \
    --input-dir ../data/papers/ \
    --db ../public/data/citation_network.db \
    --num-gpus 8 --verbose

# ── Verify ────────────────────────────────────────────────────────────────────
sqlite3 ../public/data/citation_network.db "SELECT COUNT(*) FROM graph_nodes;"
python3 -c "import json; d=json.load(open('public/data/graph_preview.json')); print(len(d['nodes']),'nodes')"

# ── Run the web app ───────────────────────────────────────────────────────────
# Terminal A — API server:
pnpm --filter @workspace/api-server run dev

# Terminal B — Frontend:
pnpm --filter @workspace/citation-network run dev
```

---

## Performance Summary

| Bottleneck | Fix applied | Gain |
|---|---|---|
| Stage 1 SQLite lock contention | Producer-consumer: N parse threads + 1 write thread | Parsing fully parallel, zero lock contention |
| Stage 1 write speed | `PRAGMA synchronous=OFF` during bulk ingest | 3–5x faster writes |
| Stage 2 degree recalculation | `GROUP BY` temp table instead of O(N²) Python loop | ~100x faster for 54M papers |
| Stage 3 edge loading | Stream directly to cuDF batches (never load all edges into Python) | Saves ~14 GB RAM, 2–3x faster |
| Stage 4 OOM | Batched tiled repulsive forces instead of N×N matrix | 8 TB → manageable VRAM usage |
| Stage 5 pagination | Keyset pagination (`WHERE rowid > ?`) instead of OFFSET | O(1) vs O(N) per page |
| Large files (2–14 GB) | Auto-chunk to ≤500 MB + `make_subset.py` | ~10x faster parse per file |
