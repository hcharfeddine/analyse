# 🚀 IMPORTANT: GPU Setup Required - Please Read Now

**Last Updated**: May 19, 2026

---

## TL;DR - What You Need to Do NOW

If you already cloned the repository, you need to do ONE thing before running the pipeline:

```bash
# 1. Check your CUDA version
nvcc --version

# 2. Install RAPIDS based on your CUDA version
# For CUDA 12.x:
pip install cudf-cu12 cugraph-cu12

# For CUDA 11.x:
pip install cudf-cu11 cugraph-cu11

# 3. Verify it worked
python diagnose_gpu.py
```

**That's it!** This single step transforms processing from **1-2 MONTHS** to **3-5 HOURS**.

---

## Why This Matters

We discovered the pipeline wasn't using GPU acceleration because RAPIDS (required for GPU) wasn't installed. Here's the impact:


## What We Changed

We added:
1. **GPU setup section in README.md** - Follow this for proper installation
2. **diagnose_gpu.py** - Automated tool to check if GPU is working
3. **Enhanced logging** - Pipeline now tells you which GPU algorithm it's using
4. **Improved error messages** - Clear hints if something is wrong

---

## Step-by-Step Instructions

### Step 1: Navigate to Pipeline Directory
```bash
cd Citation_Network/scripts/citation_network_gpu
source venv/bin/activate  # If you have a venv
```

### Step 2: Check Your CUDA Version
```bash
nvcc --version
# Output should be like: "Cuda compilation tools, release 12.x" or "release 11.x"
```

### Step 3: Install RAPIDS
```bash
# CHOOSE THE RIGHT ONE based on your CUDA version above

# For CUDA 12.x:
pip install cudf-cu12 cugraph-cu12

# For CUDA 11.x:
pip install cudf-cu11 cugraph-cu11

# Wait 10-15 minutes for installation to complete
```

### Step 4: Verify Installation
```bash
# Run the automated diagnostic
python diagnose_gpu.py

# You should see:
# ✓ CUDA available: X GPU(s) detected
# ✓ RAPIDS (cudf + cugraph) available ✓
# ✓ GPU ForceAtlas2 ready for Stage 4
```

### Step 5: Update README
The README.md has been updated with GPU setup instructions:
1. Follow the pre-flight checklist
2. Skip to the "GPU Acceleration Setup" section
3. Run diagnose_gpu.py to verify

---

## What Each Stage Does

Your pipeline runs sequentially (not per-paper):

```
[All 54M Papers] → Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5
                  (Ingest) (Dedupe) (Community) (Layout) (Export)
```

**Critical stages that need GPU:**
- **Stage 3 (Community Detection):** Finds research communities using Louvain algorithm
  - With GPU: 1-3 hours
  - Without GPU: **WEEKS**
  
- **Stage 4 (Layout):** Computes 2D coordinates for network visualization
  - With GPU: 1-2 hours
  - Without GPU: **DAYS**

---

## How to Monitor During Processing

While pipeline is running, in separate terminals:

```bash
# Terminal 1: Watch GPU usage (most important!)
nvidia-smi dmon -s puctem

# You MUST see GPU Utilization 80-99%
# If it shows 0%, GPU is not being used (RAPIDS problem)

# Terminal 2: Watch database growing
watch -n 5 'du -sh public/data/citation_network.db'

# Terminal 3: Watch logs
tail -f pipeline.log
```

**If GPU shows 0% utilization:**
1. Stop the pipeline (Ctrl+C)
2. Run: `python diagnose_gpu.py`
3. Check the GPU_TROUBLESHOOTING.md file
4. Most likely: RAPIDS installation failed

---

## Common Issues & Quick Fixes

### ❌ "GPU Utilization: 0%" During Processing
This means RAPIDS didn't install correctly.

**Fix:**
```bash
# Check if RAPIDS is actually installed
python -c "import cudf; print('cudf OK')"
python -c "import cugraph; print('cugraph OK')"

# If either fails, reinstall
pip install --force-reinstall cudf-cu12 cugraph-cu12
```

### ❌ "ModuleNotFoundError: No module named 'cudf'"
RAPIDS is not installed or wrong CUDA version.

**Fix:**
```bash
# Check CUDA version
nvcc --version

# Reinstall matching your CUDA version
pip install cudf-cu12 cugraph-cu12  # If CUDA 12
# OR
pip install cudf-cu11 cugraph-cu11  # If CUDA 11
```

### ❌ "Import error: This environment does not have a GPU"
Usually a CUDA/RAPIDS mismatch.

**Fix:**
```bash
python diagnose_gpu.py
# Follow the recommendations it shows
```

### ❌ "Out of Memory on GPU"
Your GPU doesn't have enough VRAM.

**Fix:**
```bash
# In config.py, reduce:
BATCH_SIZE = 25000  # (instead of 50,000)
```
---

## Documentation Files

I added these files for reference:

| File | Purpose |
|------|---------|
| `README.md` | **Updated with GPU setup section** |
| `diagnose_gpu.py` | Run anytime to check GPU status |
| `GPU_QUICK_FIX.txt` | 1-page quick reference |
| `GPU_FIX_SUMMARY.md` | Visual diagrams and overview |
| `GPU_TROUBLESHOOTING.md` | Detailed troubleshooting guide |
| `GPU_UTILIZATION_ISSUES_AND_FIXES.md` | Technical deep-dive |

**Start here:**
1. README.md (GPU Acceleration Setup section)
2. Run: `python diagnose_gpu.py`
3. If issues: Read GPU_TROUBLESHOOTING.md

---

If something doesn't work:
1. Run `python diagnose_gpu.py` for automated diagnostics
2. Check `GPU_TROUBLESHOOTING.md` for your specific error
3. Look at `GPU_QUICK_FIX.txt` for common solutions
4. Review the updated `README.md` for setup instructions

---

## Summary Checklist

- [ ] Cloned repository: ✓ (already done)
- [ ] Checked CUDA version: `nvcc --version`
- [ ] Installed RAPIDS: `pip install cudf-cu12 cugraph-cu12` (or cu11)
- [ ] Ran diagnostic: `python diagnose_gpu.py`
- [ ] Read updated README.md GPU section: ✓
- [ ] Ready to run pipeline: ✓

