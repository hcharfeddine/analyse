# Citation Network - Server Setup Guide

Complete step-by-step guide to set up and run the GPU-accelerated citation network pipeline on your server. This guide assumes you have the metadata papers ready to add to the repository.

---

## 📋 Table of Contents

1. [Pre-Flight Checklist](#pre-flight-checklist)
2. [Clone Repository](#clone-repository)
3. [Add Metadata (Papers)](#add-metadata-papers)
4. [Setup Python Environment](#setup-python-environment)
5. [Install Dependencies](#install-dependencies)
6. [Configure Pipeline](#configure-pipeline)
7. [Run Test (Optional)](#run-test-optional)
8. [Run Full Pipeline](#run-full-pipeline)
9. [Monitor Progress](#monitor-progress)
10. [Verify Results](#verify-results)
11. [Troubleshooting](#troubleshooting)
12. [Performance Tuning](PERFORMANCE_TUNING.md) — Optimize Stages 1–2 with CPU workers, WAL pragmas, and NVMe storage

---

## ✅ Pre-Flight Checklist

Before you start, verify your server has the required resources:

```bash
# Check Python version (need 3.8+)
python3 --version

# Check CUDA (need 11.8+)
nvcc --version

# Check GPUs available
nvidia-smi

# Check system RAM
free -h

# Check disk space (need 500GB+ free)
df -h /

# Check git installed
git --version
```

**All green?** Let's proceed! ✅

---

## 🔄 Clone Repository

Start by cloning the project from GitHub to your server:

```bash
# Clone the repository
git clone https://github.com/hcharfeddine/Citation_Network.git

# Navigate to project
cd Citation_Network-main
```

---

## 📁 Add Metadata (Papers)

Your papers need to be in the correct directory structure before running the pipeline.

### Step 1: Create Directory for Papers

```bash
# Create the metadata directory
mkdir -p data/papers

# Verify it's created
ls -la data/
```

### Step 2: Add Your Paper JSON Files

Your papers should be organized by year in JSON format:

```
data/papers/
├── 1908.json
├── 1909.json
├── ...
├── 2023.json
└── 2024.json
```

Each JSON file should contain an array of papers:

```json
[
  {
    "id": "paper_123",
    "title": "Example Paper Title",
    "authors": ["Author A", "Author B"],
    "year": 2020,
    "abstract": "This is the paper abstract...",
    "citations": ["paper_456", "paper_789"]
  },
  {
    "id": "paper_456",
    "title": "Another Paper",
    "authors": ["Author C"],
    "year": 2020,
    "abstract": "...",
    "citations": []
  }
]
```

### Step 3: Verify Papers Are in Place

```bash
# Check number of JSON files
ls -la data/papers/ | wc -l

# Check total papers (rough count)
find data/papers -name "*.json" -exec wc -l {} +

# Sample first paper (verify structure)
head -c 500 data/papers/2020.json
```

✅ Papers should now be ready!

---

## 🐍 Setup Python Environment

Create an isolated Python environment for the citation network:

### Step 1: Create Virtual Environment

```bash
# Navigate to citation network directory
cd scripts/citation_network_gpu

# Create virtual environment
python3 -m venv venv

# Output should show:
# created virtual environment CPython3.x.x
```

### Step 2: Activate Virtual Environment

```bash
# Activate (Linux/macOS)
source venv/bin/activate

# You should see (venv) at the start of your terminal prompt
```

### Step 3: Verify Environment

```bash
# Check Python path
which python
# Should show: .../venv/bin/python

# Check Python version
python --version
# Should show: 3.8+
```

✅ Environment ready!

---

## 📦 Install Dependencies

Install all required packages (this takes 15-30 minutes):

### Step 1: Upgrade pip

```bash
pip install --upgrade pip setuptools wheel
```

### Step 2: Install Requirements

```bash
# Make sure you're in scripts/citation_network_gpu directory
pwd
# Should end with: .../scripts/citation_network_gpu

# Install all dependencies
pip install -r requirements.txt

# This will take 15-30 minutes depending on your internet speed
```

### Step 3: Verify Installation

```bash
# Test critical imports (run each one)
python -c "import torch; print('✓ PyTorch OK')"
python -c "import pandas; print('✓ Pandas OK')"
python -c "import networkx; print('✓ NetworkX OK')"
python -c "import sqlite3; print('✓ SQLite OK')"

# All should print ✓ ... OK
```

**If any import fails:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

✅ All dependencies installed!

---

## ⚡ GPU Acceleration Setup (CRITICAL FOR PERFORMANCE!)

**⚠️ IMPORTANT:** Without RAPIDS, processing takes MONTHS instead of hours. Do this step now!

### Step 1: Check Your CUDA Version

```bash
# Check which CUDA version you have
nvcc --version

# Look for output like: "Cuda compilation tools, release 12.x"
# OR: "Cuda compilation tools, release 11.x"
```

### Step 2: Install RAPIDS (Choose One Below)

**For CUDA 12.x:**
```bash
pip install cudf-cu12 cugraph-cu12
# This takes 10-15 minutes
```

**For CUDA 11.x:**
```bash
pip install cudf-cu11 cugraph-cu11
# This takes 10-15 minutes
```

### Step 3: Verify GPU Setup

```bash
# Run diagnostic script to confirm everything is working
python diagnose_gpu.py

# Expected output should show:
# ✓ CUDA available: X GPU(s) detected
# ✓ RAPIDS (cudf + cugraph) available
# ✓ GPU ForceAtlas2 ready for Stage 4

# If something shows ✗, that's a problem - review GPU_TROUBLESHOOTING.md
```

---

## ⚙️ Configure Pipeline

Review and adjust the pipeline configuration:

### Step 1: View Configuration

```bash
# Check current settings
cat config.py

# Key settings:
# BATCH_SIZE: Number of papers per batch (50,000)
# NUM_WORKERS: Number of parallel workers (8)
# GPU_MEMORY_LIMIT: GB per GPU (20)
```

### Step 2: Adjust Settings (if needed)

If your server has different specs, edit the config:

```bash
# Using nano editor (easier)
nano config.py

# Or using vim
vim config.py
```

**Common adjustments:**

- **Fewer GPUs?** Set `PARALLEL_WORKERS = 4` (or your GPU count)
- **Lower RAM?** Set `BATCH_SIZE = 25000` (reduce from 50,000)
- **More disk space?** Keep default settings

After editing, save and exit.

### Step 3: Create Output Directory

```bash
# Create directory for results
mkdir -p public/data

# Verify
ls -la public/
```

✅ Configuration complete!

---

## 🧪 Run Test (Optional)

Before running on all papers, test with a small sample (recommended):

### Step 1: Create Test Data

```bash
# Copy just one year for testing
mkdir -p /tmp/test_papers
cp ../../data/papers/2020.json /tmp/test_papers/

# Verify
ls -la /tmp/test_papers/
```

### Step 2: Run Test Pipeline

```bash
# Make sure virtual environment is still active
source venv/bin/activate

# Run test (should take 5-10 minutes for 1 year)
python main.py \
  --input-dir /tmp/test_papers \
  --db /tmp/test_citation_network.db \
  --num-gpus 8 \
  --verbose
```

### Step 3: Check Test Results

```bash
# Verify database was created
ls -lh /tmp/test_citation_network.db

# Count papers in test database
sqlite3 /tmp/test_citation_network.db "SELECT COUNT(*) FROM nodes;"

# Check output files
ls -lh /tmp/
# Should show test_citation_network.db and JSON files
```

✅ Test successful? Great! Move to full pipeline.

---

## 🚀 Run Full Pipeline

Time to process all papers!

### Step 1: Prepare

```bash
# Activate environment
source venv/bin/activate

# Verify input directory
ls -la ../../data/papers/ | head -10

# Verify output directory exists
mkdir -p public/data
```

### Step 2: Start Pipeline

```bash
# Run the full citation network pipeline
# This will take 5-7 hours for large datasets
python main.py \
  --input-dir ../../data/papers \
  --db public/data/citation_network.db \
  --num-gpus 8 \
  --verbose

# Expected output:
# [INFO] Stage 1: Ingesting papers...
# [PROGRESS] Processing...
# [INFO] Stage 2: Deduplicating edges...
# [INFO] Stage 3: Community detection...
# [INFO] Stage 4: Computing layout...
# [INFO] Stage 5: Exporting...
# [INFO] PIPELINE COMPLETE!
```

### Step 3: Run in Background (Recommended)

If you want to close your terminal, use one of these methods:

**Option A: Using nohup**
```bash
nohup python main.py \
  --input-dir ../../data/papers \
  --db public/data/citation_network.db \
  --num-gpus 8 \
  --verbose > pipeline.log 2>&1 &

# Check status anytime:
tail -f pipeline.log
```

**Option B: Using tmux**
```bash
# Create new tmux session
tmux new-session -d -s citation-pipeline

# Attach to it
tmux attach -t citation-pipeline

# In the session, run:
source venv/bin/activate
python main.py --input-dir ../../data/papers --db public/data/citation_network.db --num-gpus 8 --verbose

# Detach: Ctrl+B then D
```

**Option C: Using screen**
```bash
# Create new screen session
screen -S citation-pipeline

# In the session, run:
source venv/bin/activate
python main.py --input-dir ../../data/papers --db public/data/citation_network.db --num-gpus 8 --verbose

# Detach: Ctrl+A then D
```

---

## 📊 Monitor Progress

While the pipeline runs, monitor it in separate terminals:

### Terminal 1: Watch GPU Usage (CRITICAL!)

```bash
# Monitor GPU in detail (shows per-process GPU usage)
nvidia-smi dmon -s puctem

# OR for simpler view
watch -n 1 nvidia-smi

# IMPORTANT: You should see:
# - GPU Memory Usage increasing (means data is on GPU)
# - GPU Utilization 80-99% (means GPU is being used)
# - Process: python main.py

# If GPU Utilization is 0%, GPU is NOT being used (problem!)
# See troubleshooting below if this happens
```

**⚠️ Troubleshooting GPU Not Being Used:**
```bash
# While pipeline is running, check if RAPIDS is actually being used
ps aux | grep python

# Then check detailed GPU process info
nvidia-smi -q -d COMPUTE_CAP

# If you see "GPU Utilization: 0%", RAPIDS didn't install correctly
# Run this to fix:
pip install --force-reinstall cudf-cu12 cugraph-cu12
```

### Terminal 2: Watch Database Growth

```bash
# Monitor database file size
watch -n 5 'du -sh public/data/citation_network.db'

# Should steadily increase as papers are processed
```

### Terminal 3: Check Logs

```bash
# If running with nohup
tail -f pipeline.log

# Or if running directly
# Just watch the terminal output
```

### Terminal 4: Monitor System Resources

```bash
# Check memory and CPU
watch -n 2 free -h

# Should see consistent memory usage
```

---

## ✅ Verify Results

After the pipeline completes:

### Step 1: Check Database

```bash
# Verify database was created
ls -lh public/data/citation_network.db
# Should be: 50-100 GB depending on paper count

# Check database integrity
sqlite3 public/data/citation_network.db "PRAGMA integrity_check;"
# Should return: ok
```

### Step 2: Count Papers and Connections

```bash
# Count total papers
sqlite3 public/data/citation_network.db "SELECT COUNT(*) as papers FROM nodes;"

# Count citation connections
sqlite3 public/data/citation_network.db "SELECT COUNT(*) as citations FROM edges;"

# Count communities
sqlite3 public/data/citation_network.db "SELECT COUNT(DISTINCT community_id) as communities FROM nodes;"
```

### Step 3: Check JSON Exports

```bash
# Verify output JSON files
ls -lh public/data/

# Should include:
# - citation_network.db (database)
# - graph_preview.json (web visualization data)
# - pagination_api.json (API specs)
# - map_manifest.json (metadata)
```

### Step 4: Sample the Data

```bash
# Check structure of preview JSON
python3 << 'EOF'
import json

with open('public/data/graph_preview.json', 'r') as f:
    data = json.load(f)
    
print(f"✓ Nodes: {len(data.get('nodes', []))}")
print(f"✓ Edges: {len(data.get('edges', []))}")
print(f"✓ Communities: {len(data.get('communities', {}))}")
print(f"✓ File size: {len(json.dumps(data)) / 1e9:.2f} GB")
EOF
```

✅ Results verified!

---

## 🔧 Troubleshooting

### Issue 1: Out of Memory (OOM)

**Error message**: `CUDA out of memory`

**Solution**:
```bash
# Reduce batch size in config.py
nano config.py
# Change: BATCH_SIZE = 25000  (reduce from 50,000)
# Change: NUM_WORKERS = 4     (use fewer GPUs)

# Or use command line:
python main.py --input-dir ... --batch-size 25000 --num-gpus 4
```

### Issue 2: Python Module Not Found

**Error message**: `ModuleNotFoundError: No module named 'torch'`

**Solution**:
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Issue 3: Database Locked

**Error message**: `database is locked`

**Solution**:
```bash
# Check if another pipeline is running
ps aux | grep main.py

# If yes, wait for it to complete
# Or kill it if it's stuck:
pkill -f "python main.py"

# Then restart:
python main.py --input-dir ... 
```

### Issue 4: Out of Disk Space

**Error message**: `No space left on device`

**Solution**:
```bash
# Check disk usage
df -h /

# Delete backups if any
rm -f *.backup

# Or move database to larger disk and create symlink
ln -s /large-disk/citation_network.db public/data/
```

### Issue 5: GPU Not Detected or Not Being Used (CRITICAL!)

**Error message**: `CUDA device not found` or `No CUDA devices available`
**Or**: GPU shows 0% utilization during processing (RAPIDS not working)

**Solution A: GPU Not Visible at All**
```bash
# Check GPU is visible
nvidia-smi

# Check CUDA version
nvcc --version

# Reinstall PyTorch with correct CUDA version
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**Solution B: GPU Visible But Not Being Used (RAPIDS Problem)**
```bash
# This is usually because RAPIDS (cudf/cugraph) didn't install correctly

# Step 1: Check if RAPIDS is actually installed
python -c "import cudf; print('✓ cudf available')"
python -c "import cugraph; print('✓ cugraph available')"

# If either fails, RAPIDS is missing (this is the problem!)

# Step 2: Run diagnostic
python diagnose_gpu.py

# Step 3: Reinstall RAPIDS (check CUDA version first!)
nvcc --version  # Note if it's CUDA 12.x or 11.x

# For CUDA 12:
pip install --force-reinstall cudf-cu12 cugraph-cu12

# For CUDA 11:
pip install --force-reinstall cudf-cu11 cugraph-cu11

# Step 4: Verify installation worked
python -c "import cudf; print('✓ cudf version:', cudf.__version__)"
python -c "import cugraph; print('✓ cugraph version:', cugraph.__version__)"

# Step 5: Run diagnostic again to confirm
python diagnose_gpu.py
```

**If RAPIDS still won't install:**
- See `GPU_TROUBLESHOOTING.md` for detailed troubleshooting
- Or run: `python diagnose_gpu.py` for automated diagnostics

### Issue 6: Pipeline Crashed Mid-Run

**Solution**: Resume from last checkpoint
```bash
# Find which stage failed
tail -100 pipeline.log

# Resume from that stage
python main.py \
  --input-dir ../../data/papers \
  --db public/data/citation_network.db \
  --resume-from layout \
  --num-gpus 8

# Replace "layout" with whichever stage failed
```

---


## 🎉 What's Next?

After the pipeline completes successfully:

1. **Verify the data** using the commands in [Verify Results](#verify-results)
2. **Access the network visualization** via the web interface (if setup)
3. **Use the SQLite database** for custom queries

---

## 📞 Getting Help

If you encounter issues not covered here:

1. **Check logs**: `tail -f pipeline.log`
2. **Verify GPU**: `nvidia-smi`
3. **Test imports**: `python -c "import torch"`
4. **Check space**: `df -h /`
5. **Review config**: `cat config.py`

---

## 📝 Notes

- **Always activate the virtual environment** before running commands: `source venv/bin/activate`
- **Keep the input papers in** `data/papers/` for easy reference
- **Use `nohup` or `tmux`** for long-running jobs to avoid terminal timeouts
- **Monitor GPU usage** during the first 10 minutes to catch any issues early
- **Backup your database** after successful completion

---


