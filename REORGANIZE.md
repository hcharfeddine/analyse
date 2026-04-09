# Project Reorganization Guide

This guide explains how to separate your citation network project into frontend and backend directories while keeping JSON data files in their original location.

## Why Reorganize?

The current structure mixes frontend (Next.js) and backend (Python) code. Reorganizing provides:
- **Clear separation** between frontend and backend concerns
- **Easier maintenance** - each part can be developed/deployed independently
- **Cleaner git history** - easier to track changes by component
- **Data preservation** - heavy JSON files stay in original location
- **Modular deployment** - can deploy frontend and backend separately

## Available Scripts

You have two options to reorganize your project:

### Option 1: Bash Script (Recommended for Linux/Mac)

```bash
bash reorganize.sh
```

**Requirements**: Bash shell (built-in on Linux/Mac, requires WSL on Windows)

**Features**:
- Color-coded output for clarity
- Progress indication with checkmarks
- Full error handling
- Creates convenience scripts

### Option 2: Python Script (Cross-platform)

```bash
python reorganize.py
```

**Requirements**: Python 3.6+ (should already be available)

**Features**:
- Works on Windows, Mac, and Linux
- Same functionality as bash version
- Cleaner error messages
- No additional dependencies

## What Gets Moved?

### ✅ Moved to `/frontend`
- `app/` - Next.js app directory
- `lib/` - Frontend utilities
- `next.config.js`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`
- `package.json`, lock files (package-lock.json, pnpm-lock.yaml, yarn.lock)
- `public/` - Static assets

### ✅ Moved to `/backend`
- `scripts/` - Python scripts
- `models/` - Data models
- `analysis/` - Analysis modules
- `config.py`, `requirements.txt`, `setup.py`, `pyproject.toml`

### ✅ Moved to `/shared`
- `README.md`, `SETUP.md`, `CITATION_NETWORK_README.md`
- `.gitignore`, `.env.example`

### ✅ Left in Place
- `output_filtered/modified_per_year/` - **JSON data files stay here** (not moved)
- All other original directories

## New Directory Structure

After running the reorganization script:

```
project-root/
├── frontend/                          # Next.js application
│   ├── app/
│   │   ├── api/
│   │   ├── components/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── lib/
│   ├── public/
│   │   └── data/                      # (empty, filled by backend)
│   ├── .gitignore
│   ├── .env.local                     # (create as needed)
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   └── README.md
│
├── backend/                           # Python backend
│   ├── scripts/
│   │   └── citation_network/
│   │       ├── extract_graph_data.py
│   │       └── process_graph.py
│   ├── models/
│   ├── analysis/
│   ├── .gitignore
│   ├── config.py
│   ├── requirements.txt
│   └── README.md
│
├── shared/                            # Documentation
│   ├── CITATION_NETWORK_README.md
│   ├── SETUP.md
│   ├── README.md
│   └── .gitignore
│
├── output_filtered/                   # INPUT DATA (unchanged)
│   └── modified_per_year/
│       └── *.json                     # Data files stay here
│
├── .gitignore                         # Root-level git config
├── README.md                          # Root README
├── install.sh                         # Installation script
├── dev.sh                             # Development startup script
└── reorganize.sh / reorganize.py      # (can be deleted after running)
```

## Quick Start After Reorganization

### 1. Install Dependencies

```bash
bash install.sh
```

Or manually:

```bash
# Frontend
cd frontend
npm install

# Backend
cd backend
pip install -r requirements.txt
cd ..
```

### 2. Process Data

```bash
cd backend
python scripts/citation_network/extract_graph_data.py
python scripts/citation_network/process_graph.py
```

This creates `frontend/public/data/processed_graph.json` and search index.

### 3. Start Development

```bash
bash dev.sh
```

Or manually:

```bash
cd frontend
npm run dev
```

Visit http://localhost:3000

## File Structure Details

### Frontend Configuration

**`frontend/package.json`**
- Contains Next.js and React dependencies
- Frontend build scripts
- Dev server configuration

**`frontend/.env.local`** (create if needed)
```env
NEXT_PUBLIC_DATA_URL=/data/processed_graph.json
NEXT_PUBLIC_SEARCH_INDEX_URL=/data/search_index.json
```

### Backend Configuration

**`backend/requirements.txt`**
- Python dependencies (networkx, etc.)
- For installation: `pip install -r requirements.txt`

**`backend/config.py`**
- Input data path: `../output_filtered/modified_per_year/`
- Output path: `../frontend/public/data/`
- Processing parameters

## Data Flow After Reorganization

```
output_filtered/modified_per_year/*.json
           ↓
    [Backend Processing]
    (extract_graph_data.py)
    (process_graph.py)
           ↓
frontend/public/data/processed_graph.json
           ↓
    [Frontend Loading]
    (CitationNetworkVisualization.tsx)
           ↓
     Browser Visualization
```

## Development Workflow

### Working on Frontend

```bash
cd frontend
npm run dev
# Make changes, HMR auto-refreshes
```

### Working on Backend

```bash
cd backend
python scripts/citation_network/extract_graph_data.py
python scripts/citation_network/process_graph.py
# Regenerate data files when data processing scripts change
```

### Running Both Simultaneously

**Terminal 1:**
```bash
cd backend
python scripts/citation_network/process_graph.py
# Regenerate data as needed
```

**Terminal 2:**
```bash
bash dev.sh  # or: cd frontend && npm run dev
```

## Git Management

### Ignoring Large Files

Files ignored by git (see `.gitignore`):

**Root .gitignore**:
- `output_filtered/` - Original JSON data
- Large compressed files

**Frontend .gitignore**:
- `node_modules/`
- `.next/` build directory
- `.env.local` secrets

**Backend .gitignore**:
- `__pycache__/`
- `venv/` virtual environment
- Generated `.jsonl` files

### Committing Changes

After reorganization, git will see:
- **Moved files**: All existing code files with history preserved
- **New files**: README files, convenience scripts
- **Deleted files**: None (just reorganized)

Your commit history should remain intact!

## Troubleshooting

### Script Fails to Run (Bash)

**Issue**: `Permission denied` error

**Solution**:
```bash
chmod +x reorganize.sh
bash reorganize.sh
```

### Script Fails to Run (Python)

**Issue**: Python not found

**Solution**:
```bash
python3 reorganize.py
# or ensure python is in PATH
```

### Frontend Not Finding Data

**Issue**: `404 error for /data/processed_graph.json`

**Solution**:
1. Ensure backend scripts have been run
2. Check `frontend/public/data/` directory exists
3. Verify `processed_graph.json` was generated:
   ```bash
   ls -la frontend/public/data/
   ```

### Backend Can't Find Input Data

**Issue**: `output_filtered/modified_per_year/ not found`

**Solution**:
- Ensure JSON data is in root `output_filtered/` directory
- Check paths in `backend/config.py`
- The backend uses relative paths: `../output_filtered/modified_per_year/`

## Running the Reorganization Script

### Before Running

1. **Backup your project** (optional but recommended):
   ```bash
   cp -r . ../backup-before-reorganize
   ```

2. **Ensure all files are committed** to git:
   ```bash
   git status  # Check for uncommitted changes
   git commit -am "Before reorganization"
   ```

### Running the Script

**Bash version:**
```bash
bash reorganize.sh
```

**Python version:**
```bash
python reorganize.py
```

Both scripts will:
1. Create frontend/, backend/, shared/ directories
2. Move appropriate files to each directory
3. Create .gitignore files
4. Generate README files for each directory
5. Create convenience scripts (install.sh, dev.sh)

### After Running

1. **Verify structure**:
   ```bash
   ls -la frontend/
   ls -la backend/
   ls -la shared/
   ```

2. **Check git status**:
   ```bash
   git status
   ```
   You should see many files marked as "renamed" or "deleted/added" (depending on git version)

3. **Commit the reorganization**:
   ```bash
   git add -A
   git commit -m "refactor: reorganize project structure into frontend/backend"
   ```

4. **Proceed with installation**:
   ```bash
   bash install.sh
   ```

## Reverting the Reorganization

If you need to revert:

```bash
git reset --hard HEAD~1  # Undo the reorganization commit
```

Or restore from backup:

```bash
rm -rf *
cp -r ../backup-before-reorganize/* .
```

## Next Steps

See the README files in each directory:
- `frontend/README.md` - Frontend development guide
- `backend/README.md` - Backend development guide
- `shared/CITATION_NETWORK_README.md` - Full project documentation

Happy coding! 🚀
