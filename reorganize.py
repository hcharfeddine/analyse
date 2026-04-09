#!/usr/bin/env python3
"""
Citation Network Visualization - Project Reorganization Script
This script separates frontend (Next.js) and backend (Python) into distinct folders.
Data files (JSON) remain in their original location.

Usage:
    python reorganize.py
"""

import os
import shutil
import sys
from pathlib import Path
from typing import List, Tuple


class ProjectOrganizer:
    """Reorganizes the citation network project structure."""

    # Color codes for terminal output
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

    def __init__(self, root_dir: str = None):
        """Initialize organizer with project root directory."""
        if root_dir is None:
            root_dir = os.path.dirname(os.path.abspath(__file__))
        self.root = Path(root_dir)
        self.frontend_dir = self.root / "frontend"
        self.backend_dir = self.root / "backend"
        self.shared_dir = self.root / "shared"

    def print_header(self):
        """Print script header."""
        print(f"\n{self.BLUE}========================================")
        print("Citation Network - Project Reorganizer")
        print(f"========================================{self.NC}")
        print(f"\nProject root: {self.root}\n")

    def print_step(self, message: str):
        """Print a step message in blue."""
        print(f"{self.BLUE}{message}{self.NC}")

    def print_success(self, message: str):
        """Print a success message in green."""
        print(f"{self.GREEN}✓ {message}{self.NC}")

    def print_error(self, message: str):
        """Print an error message in red."""
        print(f"{self.RED}✗ {message}{self.NC}")

    def create_directories(self):
        """Create main directory structure."""
        self.print_step("Creating directory structure...")
        
        for dir_path in [self.frontend_dir, self.backend_dir, self.shared_dir]:
            dir_path.mkdir(exist_ok=True)
        
        self.print_success("Created /frontend, /backend, /shared directories\n")

    def move_files(self, src_patterns: List[str], dst_dir: Path, label: str):
        """Move files matching patterns to destination."""
        self.print_step(f"Moving {label} files to {dst_dir.name}/...")
        
        moved_count = 0
        for pattern in src_patterns:
            src = self.root / pattern
            if src.exists():
                if src.is_dir():
                    dst = dst_dir / src.name
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.move(str(src), str(dst))
                else:
                    dst = dst_dir / src.name
                    shutil.move(str(src), str(dst))
                self.print_success(f"Moved {pattern}")
                moved_count += 1
        
        print()
        return moved_count

    def move_frontend_files(self):
        """Move all frontend files to frontend directory."""
        frontend_files = [
            "app",
            "lib",
            "next.config.js",
            "tsconfig.json",
            "tailwind.config.ts",
            "postcss.config.js",
            "package.json",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "bun.lockb",
        ]
        
        self.move_files(frontend_files, self.frontend_dir, "frontend")
        
        # Create public/data directory in frontend
        public_data = self.frontend_dir / "public" / "data"
        public_data.mkdir(parents=True, exist_ok=True)
        (public_data / ".gitkeep").touch()
        self.print_success("Created frontend/public/data directory")
        print()

    def move_backend_files(self):
        """Move all backend files to backend directory."""
        backend_files = [
            "scripts",
            "models",
            "analysis",
            "config.py",
            "pyproject.toml",
            "requirements.txt",
            "setup.py",
        ]
        
        self.move_files(backend_files, self.backend_dir, "backend")

    def copy_documentation(self):
        """Copy documentation files to shared directory."""
        self.print_step("Moving documentation files to /shared...")
        
        doc_files = [
            "README.md",
            "SETUP.md",
            "CITATION_NETWORK_README.md",
            ".gitignore",
            ".env.example",
        ]
        
        for doc_file in doc_files:
            src = self.root / doc_file
            if src.exists():
                if doc_file == ".gitignore":
                    dst = self.shared_dir / doc_file
                else:
                    dst = self.shared_dir / doc_file
                
                if src.is_file():
                    shutil.copy2(str(src), str(dst))
                    src.unlink()  # Remove original
                    self.print_success(f"Moved {doc_file}")
        
        print()

    def create_gitignore_files(self):
        """Create .gitignore files for each directory."""
        self.print_step("Creating .gitignore files...")
        
        # Frontend .gitignore
        frontend_gitignore = """# Dependencies
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
"""
        (self.frontend_dir / ".gitignore").write_text(frontend_gitignore)
        self.print_success("Created frontend/.gitignore")
        
        # Backend .gitignore
        backend_gitignore = """# Python
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
"""
        (self.backend_dir / ".gitignore").write_text(backend_gitignore)
        self.print_success("Created backend/.gitignore")
        
        # Root .gitignore
        root_gitignore = """# Data files (keep in original location)
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
"""
        (self.root / ".gitignore").write_text(root_gitignore)
        self.print_success("Created root .gitignore")
        print()

    def create_readme_files(self):
        """Create README files for each directory."""
        self.print_step("Creating README files...")
        
        # Root README
        root_readme = """# Citation Network Visualization

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

For detailed information, see `shared/CITATION_NETWORK_README.md`
"""
        (self.root / "README.md").write_text(root_readme)
        self.print_success("Created root README.md")
        
        # Frontend README
        frontend_readme = """# Citation Network Visualization - Frontend

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
"""
        (self.frontend_dir / "README.md").write_text(frontend_readme)
        self.print_success("Created frontend/README.md")
        
        # Backend README
        backend_readme = """# Citation Network Visualization - Backend

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

Generated in `../frontend/public/data/`:

- `processed_graph.json` - Complete graph with metadata and metrics
- `search_index.json` - Full-text search index

## Configuration

Edit `config.py` to customize:
- Input data paths
- Output locations
- Processing parameters

For complete documentation, see `../shared/CITATION_NETWORK_README.md`
"""
        (self.backend_dir / "README.md").write_text(backend_readme)
        self.print_success("Created backend/README.md")
        print()

    def create_convenience_scripts(self):
        """Create convenience scripts for common tasks."""
        self.print_step("Creating convenience scripts...")
        
        # Install script
        install_script = """#!/bin/bash
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
"""
        install_path = self.root / "install.sh"
        install_path.write_text(install_script)
        os.chmod(install_path, 0o755)
        self.print_success("Created install.sh")
        
        # Dev script
        dev_script = """#!/bin/bash
echo "Starting Citation Network Visualization (Development)"
echo ""

cd frontend
npm run dev
"""
        dev_path = self.root / "dev.sh"
        dev_path.write_text(dev_script)
        os.chmod(dev_path, 0o755)
        self.print_success("Created dev.sh")
        print()

    def print_summary(self):
        """Print final summary."""
        print(f"{self.GREEN}========================================")
        print("✓ PROJECT REORGANIZATION COMPLETE")
        print(f"========================================{self.NC}\n")
        
        print("📁 New Structure:")
        print("   frontend/     - Next.js web application")
        print("   backend/      - Python data processing")
        print("   shared/       - Documentation")
        print("   (original)    - JSON data files remain untouched\n")
        
        print("🚀 Next Steps:\n")
        
        print("1. Install dependencies:")
        print(f"   {self.BLUE}bash install.sh{self.NC}\n")
        
        print("2. Process data (from backend directory):")
        print(f"   {self.BLUE}cd backend{self.NC}")
        print(f"   {self.BLUE}python scripts/citation_network/extract_graph_data.py{self.NC}")
        print(f"   {self.BLUE}python scripts/citation_network/process_graph.py{self.NC}\n")
        
        print("3. Start development server (from project root):")
        print(f"   {self.BLUE}bash dev.sh{self.NC}")
        print(f"   or")
        print(f"   {self.BLUE}cd frontend && npm run dev{self.NC}\n")
        
        print("📖 For detailed information, see:")
        print(f"   {self.BLUE}shared/CITATION_NETWORK_README.md{self.NC}\n")

    def run(self):
        """Execute the reorganization."""
        try:
            self.print_header()
            self.create_directories()
            self.move_frontend_files()
            self.move_backend_files()
            self.copy_documentation()
            self.create_gitignore_files()
            self.create_readme_files()
            self.create_convenience_scripts()
            self.print_summary()
            return True
        except Exception as e:
            self.print_error(f"Reorganization failed: {e}")
            return False


def main():
    """Main entry point."""
    organizer = ProjectOrganizer()
    success = organizer.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
