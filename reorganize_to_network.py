#!/usr/bin/env python3
"""
Citation Network Project Reorganizer

This script moves ONLY citation network files into a /network folder.
Keeps all existing Python scripts and analysis tools in their original locations.
JSON data files remain untouched in output_filtered/

Usage:
    python reorganize_to_network.py
    python3 reorganize_to_network.py
"""

import os
import shutil
import sys
from pathlib import Path

# Colors for output
class Colors:
    RESET = '\033[0m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'

def colored(text, color):
    """Return colored text"""
    if sys.platform == 'win32':
        return text  # No colors on Windows
    return f"{color}{text}{Colors.RESET}"

def print_header():
    """Print script header"""
    print(colored("\n=====================================", Colors.BLUE))
    print(colored("Citation Network Folder Reorganizer", Colors.BLUE))
    print(colored("=====================================\n", Colors.BLUE))

def create_directories(base_path):
    """Create the network folder structure"""
    print(colored("Step 1: Creating network folder structure...", Colors.YELLOW))
    
    dirs = [
        'network/frontend',
        'network/backend',
        'network/backend/scripts',
        'network/data',
        'network/docs',
    ]
    
    for dir_path in dirs:
        full_path = os.path.join(base_path, dir_path)
        os.makedirs(full_path, exist_ok=True)
    
    print(colored("✓ Network folder structure created\n", Colors.GREEN))

def move_frontend_files(base_path):
    """Move Next.js frontend files"""
    print(colored("Step 2: Moving Next.js frontend files to /network/frontend...", Colors.YELLOW))
    
    moves = [
        ('app', 'network/frontend'),
        ('lib', 'network/frontend'),
    ]
    
    files_to_move = [
        ('package.json', 'network/frontend'),
        ('next.config.js', 'network/frontend'),
        ('tsconfig.json', 'network/frontend'),
        ('tailwind.config.ts', 'network/frontend'),
        ('postcss.config.js', 'network/frontend'),
    ]
    
    # Move directories
    for src, dest in moves:
        src_path = os.path.join(base_path, src)
        if os.path.exists(src_path):
            dest_path = os.path.join(base_path, dest, src)
            if not os.path.exists(dest_path):
                print(f"  → Moving {src}/ ...")
                shutil.move(src_path, dest_path)
                print(colored(f"  ✓ {src}/", Colors.GREEN))
    
    # Move files
    for src, dest in files_to_move:
        src_path = os.path.join(base_path, src)
        if os.path.isfile(src_path):
            dest_path = os.path.join(base_path, dest, src)
            print(f"  → Moving {src} ...")
            shutil.move(src_path, dest_path)
            print(colored(f"  ✓ {src}", Colors.GREEN))
    
    # Create public/data folder
    public_data = os.path.join(base_path, 'network/frontend/public/data')
    os.makedirs(public_data, exist_ok=True)
    print(colored("  ✓ public/data folder created", Colors.GREEN))
    print()

def move_backend_files(base_path):
    """Move citation network Python scripts"""
    print(colored("Step 3: Moving citation network Python scripts to /network/backend...", Colors.YELLOW))
    
    citation_net = os.path.join(base_path, 'scripts/citation_network')
    if os.path.exists(citation_net):
        dest_path = os.path.join(base_path, 'network/backend/scripts/citation_network')
        print(f"  → Moving scripts/citation_network/ ...")
        shutil.move(citation_net, dest_path)
        print(colored("  ✓ citation_network scripts", Colors.GREEN))
    
    print()

def move_docs(base_path):
    """Move documentation files"""
    print(colored("Step 4: Moving documentation files to /network/docs...", Colors.YELLOW))
    
    docs = [
        ('CITATION_NETWORK_README.md', 'README.md'),
        ('SETUP.md', 'SETUP.md'),
    ]
    
    for src, dest_name in docs:
        src_path = os.path.join(base_path, src)
        if os.path.isfile(src_path):
            dest_path = os.path.join(base_path, 'network/docs', dest_name)
            print(f"  → Moving {src} ...")
            shutil.move(src_path, dest_path)
            print(colored(f"  ✓ {src}", Colors.GREEN))
    
    print()

def create_convenience_files(base_path):
    """Create convenience files and scripts"""
    print(colored("Step 5: Creating convenience files at project root...", Colors.YELLOW))
    
    # .env.local.example
    env_path = os.path.join(base_path, 'network/frontend/.env.local.example')
    with open(env_path, 'w') as f:
        f.write('# Add environment variables here if needed\n')
        f.write('# NEXT_PUBLIC_API_URL=http://localhost:3000\n')
    print(colored("  ✓ .env.local.example", Colors.GREEN))
    
    # requirements.txt
    req_path = os.path.join(base_path, 'network/backend/requirements.txt')
    with open(req_path, 'w') as f:
        f.write('networkx==3.1\n')
        f.write('python-louvain==0.15\n')
        f.write('numpy==1.24.0\n')
    print(colored("  ✓ requirements.txt", Colors.GREEN))
    
    # NETWORK_PROJECT_SETUP.md
    setup_md = os.path.join(base_path, 'NETWORK_PROJECT_SETUP.md')
    setup_content = '''# Citation Network Visualization - Project Setup

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
```

## Quick Start

### For Frontend Development

```bash
cd network/frontend
npm install
npm run dev
```

### For Backend Processing

```bash
cd network/backend
bash setup.sh          # or python -m venv venv on Windows
pip install -r requirements.txt

# Run extraction
python -m scripts.citation_network.extract_graph_data

# Run processing
python -m scripts.citation_network.process_graph
```

### Run Complete Pipeline

```bash
bash network/run-full-pipeline.sh
```

## Important Notes

- **JSON Data**: All original data in `output_filtered/modified_per_year/` remains untouched
- **Existing Scripts**: All your existing Python analysis scripts are unchanged
- **Separation**: Citation network code is isolated in the `/network` folder
- **Data Output**: Processed network data is saved to `network/frontend/public/data/`

## Next Steps

1. See `network/docs/README.md` for detailed documentation
2. See `network/docs/SETUP.md` for setup instructions
3. Start the frontend: `cd network/frontend && npm run dev`
'''
    
    with open(setup_md, 'w') as f:
        f.write(setup_content)
    print(colored("  ✓ NETWORK_PROJECT_SETUP.md", Colors.GREEN))
    print()

def create_run_scripts(base_path):
    """Create convenience run scripts"""
    print(colored("Step 6: Creating convenience run scripts...", Colors.YELLOW))
    
    # Frontend dev script
    dev_script = os.path.join(base_path, 'network/frontend/dev.sh')
    with open(dev_script, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write('echo "Starting Citation Network Frontend..."\n')
        f.write('npm install\n')
        f.write('npm run dev\n')
    os.chmod(dev_script, 0o755)
    print(colored("  ✓ network/frontend/dev.sh", Colors.GREEN))
    
    # Backend setup script
    setup_script = os.path.join(base_path, 'network/backend/setup.sh')
    with open(setup_script, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write('echo "Setting up Citation Network Backend..."\n')
        f.write('python -m venv venv\n')
        f.write('source venv/bin/activate\n')
        f.write('pip install -r requirements.txt\n')
        f.write('echo "Backend setup complete!"\n')
    os.chmod(setup_script, 0o755)
    print(colored("  ✓ network/backend/setup.sh", Colors.GREEN))
    
    # Master run script
    pipeline_script = os.path.join(base_path, 'network/run-full-pipeline.sh')
    with open(pipeline_script, 'w') as f:
        f.write('''#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "========================================="
echo "Citation Network - Full Pipeline"
echo "========================================="
echo ""

# Step 1: Setup backend
echo "[1/4] Setting up backend..."
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
  python -m venv venv
  source venv/bin/activate
else
  source venv/bin/activate
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
''')
    os.chmod(pipeline_script, 0o755)
    print(colored("  ✓ network/run-full-pipeline.sh", Colors.GREEN))
    print()

def print_summary(base_path):
    """Print final summary"""
    print(colored("=====================================", Colors.BLUE))
    print(colored("✓ Reorganization Complete!", Colors.GREEN))
    print(colored("=====================================\n", Colors.BLUE))
    
    print(colored("Directory Structure:", Colors.YELLOW))
    print("""
network/
├── frontend/               (Next.js app)
│   ├── app/
│   ├── lib/
│   ├── public/data/        (where processed data goes)
│   └── package.json
│
├── backend/                (Python data processing)
│   ├── scripts/citation_network/
│   └── requirements.txt
│
├── docs/                   (Documentation)
└── run-full-pipeline.sh    (Master run script)
""")
    
    print(colored("Original Files Preserved:", Colors.YELLOW))
    print("""
✓ output_filtered/modified_per_year/    (JSON data - UNTOUCHED)
✓ analysis/                             (Your existing scripts)
✓ models/                               (Your existing models)
✓ ... (all other original files)
""")
    
    print(colored("Next Steps:", Colors.YELLOW))
    print("""
1. Frontend Development:
   cd network/frontend
   npm install
   npm run dev

2. Backend Setup:
   cd network/backend
   bash setup.sh

3. Run Full Pipeline:
   bash network/run-full-pipeline.sh

""")
    print(colored("=====================================\n", Colors.BLUE))

def main():
    """Main execution"""
    try:
        print_header()
        
        # Get project root
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Execute reorganization steps
        create_directories(base_path)
        move_frontend_files(base_path)
        move_backend_files(base_path)
        move_docs(base_path)
        create_convenience_files(base_path)
        create_run_scripts(base_path)
        
        # Print summary
        print_summary(base_path)
        
        print(colored("✓ All done! Your project is now organized.", Colors.GREEN))
        
    except Exception as e:
        print(colored(f"\n✗ Error: {str(e)}", Colors.RED))
        sys.exit(1)

if __name__ == '__main__':
    main()
