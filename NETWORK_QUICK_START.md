# Citation Network - Quick Start Guide

## One-Line Organization

Run ONE of these commands to reorganize everything into a `/network` folder:

### Option 1: Bash (Mac/Linux)
```bash
bash reorganize_to_network.sh
```

### Option 2: Python (Windows/Mac/Linux)
```bash
python reorganize_to_network.py
# or
python3 reorganize_to_network.py
```

---

## What Gets Organized?

### ✅ Moves to `/network/frontend`
- `app/` - Next.js application
- `lib/` - Frontend utilities
- `public/data/` - Where processed data goes
- Config files: `package.json`, `next.config.js`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`

### ✅ Moves to `/network/backend`
- `scripts/citation_network/` - Data extraction & processing scripts
- `requirements.txt` - Python dependencies

### ✅ Moves to `/network/docs`
- `CITATION_NETWORK_README.md` → `README.md`
- `SETUP.md`

### ✅ Stays Unchanged (Protected)
- `output_filtered/modified_per_year/` - Your heavy JSON data
- `analysis/` - Your existing analysis scripts
- `models/` - Your existing models
- All other original project files

---

## After Organization

Your structure will look like:

```
project-root/
├── network/
│   ├── frontend/          ← Next.js app
│   ├── backend/           ← Python scripts
│   ├── docs/              ← Documentation
│   └── run-full-pipeline.sh
│
├── output_filtered/       ← Original data (UNTOUCHED)
├── analysis/              ← Your scripts (unchanged)
├── models/                ← Your models (unchanged)
└── NETWORK_PROJECT_SETUP.md
```

---

## Quick Commands

### Start Frontend Development
```bash
cd network/frontend
npm install
npm run dev
```

### Setup & Run Backend
```bash
cd network/backend
bash setup.sh                    # Create venv and install deps
python -m scripts.citation_network.extract_graph_data
python -m scripts.citation_network.process_graph
```

### Run Everything at Once
```bash
bash network/run-full-pipeline.sh
```

---

## Why This Organization?

✓ **Isolation**: Citation network code is separate from your existing analysis  
✓ **Clean**: No mixing of concerns - frontend and backend clearly separated  
✓ **Safe**: Your original JSON data and scripts are untouched  
✓ **Portable**: The `/network` folder can be deployed independently  
✓ **Organized**: Easy to understand what does what  

---

## Troubleshooting

**Windows users**: Use `python reorganize_to_network.py` instead of bash

**Permission denied**: Run `chmod +x *.sh` to make bash scripts executable

**Data not found**: Check that `output_filtered/modified_per_year/` exists with your JSON files

**Need to undo**: All moves use `mv` which tracks history in git - just do `git status` to see what moved

---

## Next Steps

1. Run the reorganization script
2. Read `NETWORK_PROJECT_SETUP.md` in the project root
3. Check `network/docs/README.md` for full documentation
4. Start developing!

```bash
# TL;DR
bash reorganize_to_network.sh
cd network/frontend
npm install && npm run dev
```
