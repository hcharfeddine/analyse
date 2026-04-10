#!/bin/bash

# Citation Network Project Reorganizer
# This script moves ONLY citation network files into a /network folder
# Keeps all existing Python scripts and analysis tools in their original locations
# JSON data files remain untouched in output_filtered/

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}Citation Network Folder Reorganizer${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Step 1: Create network folder structure
echo -e "${YELLOW}Step 1: Creating network folder structure...${NC}"
mkdir -p "$PROJECT_ROOT/network/frontend"
mkdir -p "$PROJECT_ROOT/network/backend"
mkdir -p "$PROJECT_ROOT/network/backend/scripts"
mkdir -p "$PROJECT_ROOT/network/data"
mkdir -p "$PROJECT_ROOT/network/docs"
echo -e "${GREEN}✓ Network folder structure created${NC}"
echo ""

# Step 2: Move Next.js frontend files
echo -e "${YELLOW}Step 2: Moving Next.js frontend files to /network/frontend...${NC}"

# Move app directory (Next.js)
if [ -d "$PROJECT_ROOT/app" ]; then
  echo "  → Moving app/ ..."
  mv "$PROJECT_ROOT/app" "$PROJECT_ROOT/network/frontend/"
  echo -e "  ${GREEN}✓ app/${NC}"
fi

# Move lib directory
if [ -d "$PROJECT_ROOT/lib" ]; then
  echo "  → Moving lib/ ..."
  mv "$PROJECT_ROOT/lib" "$PROJECT_ROOT/network/frontend/"
  echo -e "  ${GREEN}✓ lib/${NC}"
fi

# Move Next.js config files
if [ -f "$PROJECT_ROOT/package.json" ]; then
  echo "  → Moving package.json ..."
  mv "$PROJECT_ROOT/package.json" "$PROJECT_ROOT/network/frontend/"
  echo -e "  ${GREEN}✓ package.json${NC}"
fi

if [ -f "$PROJECT_ROOT/next.config.js" ]; then
  echo "  → Moving next.config.js ..."
  mv "$PROJECT_ROOT/next.config.js" "$PROJECT_ROOT/network/frontend/"
  echo -e "  ${GREEN}✓ next.config.js${NC}"
fi

if [ -f "$PROJECT_ROOT/tsconfig.json" ]; then
  echo "  → Moving tsconfig.json ..."
  mv "$PROJECT_ROOT/tsconfig.json" "$PROJECT_ROOT/network/frontend/"
  echo -e "  ${GREEN}✓ tsconfig.json${NC}"
fi

if [ -f "$PROJECT_ROOT/tailwind.config.ts" ]; then
  echo "  → Moving tailwind.config.ts ..."
  mv "$PROJECT_ROOT/tailwind.config.ts" "$PROJECT_ROOT/network/frontend/"
  echo -e "  ${GREEN}✓ tailwind.config.ts${NC}"
fi

if [ -f "$PROJECT_ROOT/postcss.config.js" ]; then
  echo "  → Moving postcss.config.js ..."
  mv "$PROJECT_ROOT/postcss.config.js" "$PROJECT_ROOT/network/frontend/"
  echo -e "  ${GREEN}✓ postcss.config.js${NC}"
fi

# Create public folder for data
mkdir -p "$PROJECT_ROOT/network/frontend/public/data"
echo -e "  ${GREEN}✓ public/data folder created${NC}"

echo ""

# Step 3: Move citation network Python scripts
echo -e "${YELLOW}Step 3: Moving citation network Python scripts to /network/backend...${NC}"

if [ -d "$PROJECT_ROOT/scripts/citation_network" ]; then
  echo "  → Moving scripts/citation_network/ ..."
  mv "$PROJECT_ROOT/scripts/citation_network" "$PROJECT_ROOT/network/backend/scripts/"
  echo -e "  ${GREEN}✓ citation_network scripts${NC}"
fi

echo ""

# Step 4: Move documentation
echo -e "${YELLOW}Step 4: Moving documentation files to /network/docs...${NC}"

if [ -f "$PROJECT_ROOT/CITATION_NETWORK_README.md" ]; then
  echo "  → Moving CITATION_NETWORK_README.md ..."
  mv "$PROJECT_ROOT/CITATION_NETWORK_README.md" "$PROJECT_ROOT/network/docs/README.md"
  echo -e "  ${GREEN}✓ CITATION_NETWORK_README.md${NC}"
fi

if [ -f "$PROJECT_ROOT/SETUP.md" ]; then
  echo "  → Moving SETUP.md ..."
  mv "$PROJECT_ROOT/SETUP.md" "$PROJECT_ROOT/network/docs/"
  echo -e "  ${GREEN}✓ SETUP.md${NC}"
fi

echo ""

# Step 5: Create root-level files for convenience
echo -e "${YELLOW}Step 5: Creating convenience files at project root...${NC}"

# Create network/.env.example
cat > "$PROJECT_ROOT/network/frontend/.env.local.example" << 'EOF'
# Add environment variables here if needed
# NEXT_PUBLIC_API_URL=http://localhost:3000
EOF
echo -e "  ${GREEN}✓ .env.local.example${NC}"

# Create backend/requirements.txt
cat > "$PROJECT_ROOT/network/backend/requirements.txt" << 'EOF'
networkx==3.1
python-louvain==0.15
numpy==1.24.0
EOF
echo -e "  ${GREEN}✓ requirements.txt${NC}"

# Create root README
cat > "$PROJECT_ROOT/NETWORK_PROJECT_SETUP.md" << 'EOF'
# Citation Network Visualization - Project Setup

This project contains a citation network visualization system split into separate frontend and backend components.

## Directory Structure

```
project-root/
├── network/                          # Citation Network Project
│   ├── frontend/                     # Next.js Frontend
│   │   ├── app/                      # Next.js app directory
│   │   ├── lib/                      # Utilities and helpers
│   │   ├── public/data/              # Data files (generated)
│   │   ├── package.json
│   │   ├── next.config.js
│   │   ├── tailwind.config.ts
│   │   └── tsconfig.json
│   │
│   ├── backend/                      # Python Backend
│   │   ├── scripts/
│   │   │   └── citation_network/     # Citation network data scripts
│   │   │       ├── extract_graph_data.py
│   │   │       └── process_graph.py
│   │   └── requirements.txt
│   │
│   └── docs/                         # Documentation
│       ├── README.md                 # Main documentation
│       └── SETUP.md                  # Setup instructions
│
├── output_filtered/                  # Original JSON data (UNTOUCHED)
│   └── modified_per_year/            # Large JSON files stay here
│
├── analysis/                         # Existing analysis scripts (unchanged)
├── models/                           # Existing models (unchanged)
└── ... (other original files)
EOF
echo -e "  ${GREEN}✓ NETWORK_PROJECT_SETUP.md${NC}"

echo ""

# Step 6: Create convenient run scripts
echo -e "${YELLOW}Step 6: Creating convenience run scripts...${NC}"

# Frontend dev script
cat > "$PROJECT_ROOT/network/frontend/dev.sh" << 'EOF'
#!/bin/bash
echo "Starting Citation Network Frontend..."
npm install
npm run dev
EOF
chmod +x "$PROJECT_ROOT/network/frontend/dev.sh"
echo -e "  ${GREEN}✓ network/frontend/dev.sh${NC}"

# Backend setup script
cat > "$PROJECT_ROOT/network/backend/setup.sh" << 'EOF'
#!/bin/bash
echo "Setting up Citation Network Backend..."
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
echo "Backend setup complete!"
EOF
chmod +x "$PROJECT_ROOT/network/backend/setup.sh"
echo -e "  ${GREEN}✓ network/backend/setup.sh${NC}"

# Master run script at root
cat > "$PROJECT_ROOT/network/run-full-pipeline.sh" << 'EOF'
#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
DATA_DIR="$FRONTEND_DIR/public/data"

echo "========================================="
echo "Citation Network - Full Pipeline"
echo "========================================="
echo ""

# Step 1: Setup backend
echo "[1/4] Setting up backend..."
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
  python -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
else
  source venv/bin/activate  # On Windows: venv\Scripts\activate
fi
pip install -r requirements.txt -q
echo "✓ Backend setup complete"
echo ""

# Step 2: Extract data
echo "[2/4] Extracting citation data..."
cd "$BACKEND_DIR"
python -m scripts.citation_network.extract_graph_data
echo "✓ Data extraction complete"
echo ""

# Step 3: Process data
echo "[3/4] Processing citation network..."
cd "$BACKEND_DIR"
python -m scripts.citation_network.process_graph
echo "✓ Data processing complete"
echo ""

# Step 4: Setup and run frontend
echo "[4/4] Setting up frontend..."
cd "$FRONTEND_DIR"
npm install -q
echo "✓ Frontend ready"
echo ""

echo "========================================="
echo "✓ Pipeline Complete!"
echo "========================================="
echo ""
echo "To start the frontend development server:"
echo "  cd $FRONTEND_DIR"
echo "  npm run dev"
echo ""
echo "Frontend will be available at: http://localhost:3000"
EOF
chmod +x "$PROJECT_ROOT/network/run-full-pipeline.sh"
echo -e "  ${GREEN}✓ network/run-full-pipeline.sh${NC}"

echo ""

# Step 7: Summary
echo -e "${BLUE}=====================================${NC}"
echo -e "${GREEN}✓ Reorganization Complete!${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

echo -e "${YELLOW}Directory Structure:${NC}"
echo ""
echo "network/"
echo "├── frontend/               (Next.js app)"
echo "│   ├── app/"
echo "│   ├── lib/"
echo "│   ├── public/data/        (where processed data goes)"
echo "│   └── package.json"
echo ""
echo "├── backend/                (Python data processing)"
echo "│   ├── scripts/citation_network/"
echo "│   └── requirements.txt"
echo ""
echo "├── docs/                   (Documentation)"
echo "└── run-full-pipeline.sh    (Master run script)"
echo ""

echo -e "${YELLOW}Original Files Preserved:${NC}"
echo ""
echo "✓ output_filtered/modified_per_year/    (JSON data - UNTOUCHED)"
echo "✓ analysis/                             (Your existing scripts)"
echo "✓ models/                               (Your existing models)"
echo "✓ ... (all other original files)"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Frontend Development:"
echo "   cd network/frontend"
echo "   npm install"
echo "   npm run dev"
echo ""
echo "2. Backend Setup:"
echo "   cd network/backend"
echo "   bash setup.sh"
echo ""
echo "3. Run Full Pipeline:"
echo "   bash network/run-full-pipeline.sh"
echo ""

echo -e "${BLUE}=====================================${NC}"
