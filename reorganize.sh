#!/bin/bash

# Citation Network Visualization - Project Reorganization Script
# This script separates frontend (Next.js) and backend (Python) into distinct folders
# Data files (JSON) remain in their original location

set -e

echo "========================================"
echo "Citation Network - Project Reorganizer"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Project root: $PROJECT_ROOT"
echo ""

# Create main directories
echo -e "${BLUE}Creating directory structure...${NC}"
mkdir -p "$PROJECT_ROOT/frontend"
mkdir -p "$PROJECT_ROOT/backend"
mkdir -p "$PROJECT_ROOT/shared"

echo -e "${GREEN}✓ Created /frontend, /backend, /shared directories${NC}"
echo ""

# ============================================
# MOVE FRONTEND FILES
# ============================================
echo -e "${BLUE}Moving frontend files to /frontend...${NC}"

# Next.js app directory
if [ -d "$PROJECT_ROOT/app" ]; then
  mv "$PROJECT_ROOT/app" "$PROJECT_ROOT/frontend/"
  echo -e "${GREEN}✓ Moved app/${NC}"
fi

# Frontend lib
if [ -d "$PROJECT_ROOT/lib" ]; then
  mv "$PROJECT_ROOT/lib" "$PROJECT_ROOT/frontend/"
  echo -e "${GREEN}✓ Moved lib/${NC}"
fi

# Public assets
if [ -d "$PROJECT_ROOT/public" ]; then
  mkdir -p "$PROJECT_ROOT/frontend/public"
  # Don't move, copy data folder structure but keep JSON in original location
  if [ -d "$PROJECT_ROOT/public/data" ]; then
    # Keep data folder reference, we'll create a symlink later
    mkdir -p "$PROJECT_ROOT/frontend/public"
  fi
fi

# Next.js config files
for file in next.config.js tsconfig.json tailwind.config.ts postcss.config.js; do
  if [ -f "$PROJECT_ROOT/$file" ]; then
    mv "$PROJECT_ROOT/$file" "$PROJECT_ROOT/frontend/"
    echo -e "${GREEN}✓ Moved $file${NC}"
  fi
done

# Move package.json and lock files to frontend
if [ -f "$PROJECT_ROOT/package.json" ]; then
  mv "$PROJECT_ROOT/package.json" "$PROJECT_ROOT/frontend/"
  echo -e "${GREEN}✓ Moved package.json${NC}"
fi

if [ -f "$PROJECT_ROOT/package-lock.json" ]; then
  mv "$PROJECT_ROOT/package-lock.json" "$PROJECT_ROOT/frontend/"
fi

if [ -f "$PROJECT_ROOT/pnpm-lock.yaml" ]; then
  mv "$PROJECT_ROOT/pnpm-lock.yaml" "$PROJECT_ROOT/frontend/"
fi

if [ -f "$PROJECT_ROOT/yarn.lock" ]; then
  mv "$PROJECT_ROOT/yarn.lock" "$PROJECT_ROOT/frontend/"
fi

if [ -f "$PROJECT_ROOT/bun.lockb" ]; then
  mv "$PROJECT_ROOT/bun.lockb" "$PROJECT_ROOT/frontend/"
fi

echo ""

# ============================================
# MOVE BACKEND FILES
# ============================================
echo -e "${BLUE}Moving backend files to /backend...${NC}"

# Python scripts
if [ -d "$PROJECT_ROOT/scripts" ]; then
  mv "$PROJECT_ROOT/scripts" "$PROJECT_ROOT/backend/"
  echo -e "${GREEN}✓ Moved scripts/${NC}"
fi

# Python config files
for file in config.py models pyproject.toml requirements.txt setup.py; do
  if [ -f "$PROJECT_ROOT/$file" ]; then
    mv "$PROJECT_ROOT/$file" "$PROJECT_ROOT/backend/"
    echo -e "${GREEN}✓ Moved $file${NC}"
  fi
done

if [ -d "$PROJECT_ROOT/models" ]; then
  mv "$PROJECT_ROOT/models" "$PROJECT_ROOT/backend/"
  echo -e "${GREEN}✓ Moved models/${NC}"
fi

if [ -d "$PROJECT_ROOT/analysis" ]; then
  mv "$PROJECT_ROOT/analysis" "$PROJECT_ROOT/backend/"
  echo -e "${GREEN}✓ Moved analysis/${NC}"
fi

echo ""

# ============================================
# MOVE SHARED/CONFIG FILES
# ============================================
echo -e "${BLUE}Moving shared configuration files to /shared...${NC}"

for file in .gitignore .env.example .env.local pytest.ini; do
  if [ -f "$PROJECT_ROOT/$file" ]; then
    mv "$PROJECT_ROOT/$file" "$PROJECT_ROOT/shared/" 2>/dev/null || true
  fi
done

# Move documentation files
for file in README.md SETUP.md CITATION_NETWORK_README.md CONTRIBUTING.md; do
  if [ -f "$PROJECT_ROOT/$file" ]; then
    cp "$PROJECT_ROOT/$file" "$PROJECT_ROOT/shared/" 2>/dev/null || true
    rm "$PROJECT_ROOT/$file"
    echo -e "${GREEN}✓ Moved $file${NC}"
  fi
done

echo ""

# ============================================
# CREATE NEW PROJECT STRUCTURE FILES
# ============================================
echo -e "${BLUE}Creating new structure files...${NC}"

# Create frontend/.gitignore
cat > "$PROJECT_ROOT/frontend/.gitignore" << 'EOF'
# Dependencies
node_modules/
/.pnp
.pnp.js

# Next.js build
/.next/
/out/
/build

# Vercel
.vercel

# Environment
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
EOF
echo -e "${GREEN}✓ Created frontend/.gitignore${NC}"

# Create backend/.gitignore
cat > "$PROJECT_ROOT/backend/.gitignore" << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/
.venv

# Data
nodes.jsonl
edges.jsonl

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
EOF
echo -e "${GREEN}✓ Created backend/.gitignore${NC}"

# Create root .gitignore
cat > "$PROJECT_ROOT/.gitignore" << 'EOF'
# Data files (keep in original location)
output_filtered/
output_full_fos/
output/
filtered_output/

# Large files
*.tar.gz
*.zip
*.7z

# IDE
.vscode/
.idea/

# OS
.DS_Store

# Environment
.env
.env.local
EOF
echo -e "${GREEN}✓ Created root .gitignore${NC}"

echo ""

# ============================================
# CREATE FRONTEND README
# ============================================
echo -e "${BLUE}Creating frontend README...${NC}"

cat > "$PROJECT_ROOT/frontend/README.md" << 'EOF'
# Citation Network Visualization - Frontend

Next.js + React + Sigma.js web interface for the citation network visualization.

## Quick Start

```bash
# Install dependencies
npm install
# or
pnpm install

# Run development server
npm run dev
# or
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
frontend/
├── app/
│   ├── components/        # Reusable React components
│   ├── api/              # Next.js API routes
│   ├── layout.tsx        # Root layout
│   ├── page.tsx          # Home page
│   └── globals.css       # Global styles
├── lib/
│   └── dataLoader.ts     # Data loading utilities
├── public/               # Static assets
├── package.json          # Dependencies
└── next.config.js        # Next.js configuration
```

## Environment Variables

Create a `.env.local` file:

```env
# Path to processed graph data
NEXT_PUBLIC_DATA_URL=/data/processed_graph.json
NEXT_PUBLIC_SEARCH_INDEX_URL=/data/search_index.json
```

## Building

```bash
npm run build
npm start
```

## Features

- Interactive citation network visualization with Sigma.js
- Search papers by title, abstract, keywords, authors
- Filter by year and research clusters
- Rich paper details panel with full metadata
- WebGL rendering for 100k+ nodes

For complete documentation, see `../shared/CITATION_NETWORK_README.md`
EOF
echo -e "${GREEN}✓ Created frontend/README.md${NC}"

echo ""

# ============================================
# CREATE BACKEND README
# ============================================
echo -e "${BLUE}Creating backend README...${NC}"

cat > "$PROJECT_ROOT/backend/README.md" << 'EOF'
# Citation Network Visualization - Backend

Python scripts for extracting, processing, and analyzing citation network data.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run extraction script
python scripts/citation_network/extract_graph_data.py

# Run processing script
python scripts/citation_network/process_graph.py
```

## Project Structure

```
backend/
├── scripts/
│   └── citation_network/
│       ├── extract_graph_data.py    # Extract papers and citations
│       └── process_graph.py         # Process graph and detect communities
├── models/                          # Data models
├── analysis/                        # Analysis scripts
├── config.py                        # Configuration
└── requirements.txt                 # Python dependencies
```

## Data Flow

1. **Extraction**: Read JSON files from `output_filtered/modified_per_year/`
2. **Processing**: Calculate metrics, detect communities, build search index
3. **Output**: Generate `processed_graph.json` for frontend

## Output Files

Generated in `../public/data/`:

- `processed_graph.json` - Complete graph with metadata and metrics
- `search_index.json` - Full-text search index

## Configuration

Edit `config.py` to customize:
- Input data paths
- Output locations
- Processing parameters

For complete documentation, see `../shared/CITATION_NETWORK_README.md`
EOF
echo -e "${GREEN}✓ Created backend/README.md${NC}"

echo ""

# ============================================
# CREATE ROOT README
# ============================================
echo -e "${BLUE}Creating root README...${NC}"

cat > "$PROJECT_ROOT/README.md" << 'EOF'
# Citation Network Visualization

Interactive visualization of academic citation networks using 42M+ papers with full metadata.

## 📁 Project Structure

```
citation-network/
├── frontend/              # Next.js web application
│   ├── app/
│   ├── lib/
│   ├── public/
│   ├── package.json
│   └── README.md
├── backend/               # Python data processing
│   ├── scripts/
│   ├── models/
│   ├── analysis/
│   ├── requirements.txt
│   └── README.md
├── shared/                # Documentation
│   ├── CITATION_NETWORK_README.md
│   ├── SETUP.md
│   └── README.md
└── output_filtered/       # Input data (not moved)
    └── modified_per_year/ # JSON data files
```

## 🚀 Getting Started

### Backend Setup (Data Processing)

```bash
cd backend
pip install -r requirements.txt
python scripts/citation_network/extract_graph_data.py
python scripts/citation_network/process_graph.py
```

This generates processed graph data files.

### Frontend Setup (Web Interface)

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000

## 📊 Data

- **Input**: `output_filtered/modified_per_year/*.json` (42M+ papers)
- **Processing**: Extracts metadata, detects communities, builds search index
- **Output**: `frontend/public/data/processed_graph.json`

## 🎯 Features

- ✨ Interactive WebGL visualization (Sigma.js)
- 🔍 Full-text search (title, abstract, keywords, authors)
- 📅 Timeline filtering
- 🏷️ Cluster visualization
- 📋 Rich paper details panel

## 📖 Documentation

- [Frontend Guide](./frontend/README.md)
- [Backend Guide](./backend/README.md)
- [Complete Setup Guide](./shared/SETUP.md)
- [Full Documentation](./shared/CITATION_NETWORK_README.md)

## 🛠️ Technologies

**Frontend**: Next.js, React, TypeScript, Sigma.js, TailwindCSS

**Backend**: Python, NetworkX, Louvain algorithm

## 📝 License

See LICENSE file

For detailed information, see `shared/CITATION_NETWORK_README.md`
EOF
echo -e "${GREEN}✓ Created root README.md${NC}"

echo ""

# ============================================
# CREATE SETUP SCRIPTS
# ============================================
echo -e "${BLUE}Creating convenience scripts...${NC}"

# Create install script
cat > "$PROJECT_ROOT/install.sh" << 'EOF'
#!/bin/bash
echo "Installing Citation Network Visualization..."
echo ""

# Frontend
echo "Installing frontend dependencies..."
cd frontend
npm install
cd ..
echo ""

# Backend
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt
cd ..
echo ""

echo "✓ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Run data processing:"
echo "   cd backend && python scripts/citation_network/extract_graph_data.py"
echo "   python scripts/citation_network/process_graph.py"
echo ""
echo "2. Start frontend:"
echo "   cd frontend && npm run dev"
EOF
chmod +x "$PROJECT_ROOT/install.sh"
echo -e "${GREEN}✓ Created install.sh${NC}"

# Create dev script
cat > "$PROJECT_ROOT/dev.sh" << 'EOF'
#!/bin/bash
echo "Starting Citation Network Visualization (Development)"
echo ""

cd frontend
npm run dev
EOF
chmod +x "$PROJECT_ROOT/dev.sh"
echo -e "${GREEN}✓ Created dev.sh${NC}"

echo ""

# ============================================
# CREATE SYMLINK FOR DATA
# ============================================
echo -e "${BLUE}Setting up data directory symlink...${NC}"

mkdir -p "$PROJECT_ROOT/frontend/public/data"

# Create a .gitkeep file in data directory
touch "$PROJECT_ROOT/frontend/public/data/.gitkeep"
echo -e "${GREEN}✓ Created data directory placeholder${NC}"

echo ""

# ============================================
# FINAL SUMMARY
# ============================================
echo -e "${GREEN}========================================"
echo "✓ PROJECT REORGANIZATION COMPLETE"
echo "========================================${NC}"
echo ""
echo "📁 New Structure:"
echo "   frontend/     - Next.js web application"
echo "   backend/      - Python data processing"
echo "   shared/       - Documentation"
echo "   (original)    - JSON data files remain untouched"
echo ""
echo "🚀 Next Steps:"
echo ""
echo "1. Install dependencies:"
echo "   ${BLUE}bash install.sh${NC}"
echo ""
echo "2. Process data (from backend directory):"
echo "   ${BLUE}cd backend${NC}"
echo "   ${BLUE}python scripts/citation_network/extract_graph_data.py${NC}"
echo "   ${BLUE}python scripts/citation_network/process_graph.py${NC}"
echo ""
echo "3. Start development server (from project root):"
echo "   ${BLUE}bash dev.sh${NC}"
echo "   or"
echo "   ${BLUE}cd frontend && npm run dev${NC}"
echo ""
echo "📖 For detailed information, see:"
echo "   ${BLUE}shared/CITATION_NETWORK_README.md${NC}"
echo ""
