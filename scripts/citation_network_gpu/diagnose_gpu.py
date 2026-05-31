#!/usr/bin/env python3
"""
GPU Diagnostic Script

Checks GPU availability and required RAPIDS libraries.
Run this to diagnose why GPU is not being used:

    python diagnose_gpu.py
"""

import sys
import subprocess
from pathlib import Path

def run_check(name, import_name):
    """Try importing a package and report status."""
    try:
        __import__(import_name)
        print(f"  ✓ {name:<30} Installed")
        return True
    except ImportError as e:
        print(f"  ✗ {name:<30} NOT installed ({e})")
        return False

def check_cuda_devices():
    """Check NVIDIA GPU devices."""
    print("\n" + "=" * 70)
    print("NVIDIA GPU DEVICES")
    print("=" * 70)
    
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=index,name,memory.total,memory.free", "--format=csv,noheader"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if lines and lines[0]:
                print(f"Found {len(lines)} GPU(s):\n")
                for line in lines:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 4:
                        idx, name, total, free = parts[0], parts[1], parts[2], parts[3]
                        print(f"  GPU {idx}: {name}")
                        print(f"    Memory: {free} / {total}")
                return True
        else:
            print("  ✗ nvidia-smi not found. NVIDIA drivers may not be installed.")
            return False
    except FileNotFoundError:
        print("  ✗ nvidia-smi not found. NVIDIA drivers may not be installed.")
        return False
    except Exception as e:
        print(f"  ✗ Error checking GPUs: {e}")
        return False

def check_pytorch():
    """Check PyTorch and CUDA availability."""
    print("\n" + "=" * 70)
    print("PYTORCH & CUDA")
    print("=" * 70)
    
    try:
        import torch
        print(f"  ✓ PyTorch {torch.__version__:<25} Installed")
        
        if torch.cuda.is_available():
            print(f"  ✓ CUDA available:<23 {torch.cuda.device_count()} device(s)")
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                print(f"    GPU {i}: {props.name} ({props.total_memory / 1e9:.1f} GB)")
            return True
        else:
            print(f"  ✗ CUDA NOT available<15 PyTorch can only use CPU")
            return False
    except ImportError:
        print("  ✗ PyTorch NOT installed")
        return False
    except Exception as e:
        print(f"  ✗ Error checking PyTorch: {e}")
        return False

def check_rapids():
    """Check RAPIDS (cudf + cugraph) availability."""
    print("\n" + "=" * 70)
    print("RAPIDS LIBRARIES (for GPU community detection & layout)")
    print("=" * 70)
    
    cudf_ok = run_check("cudf", "cudf")
    cugraph_ok = run_check("cugraph", "cugraph")
    
    if cudf_ok and cugraph_ok:
        print("\n  ✓ RAPIDS is fully installed")
        print("    Stage 3 will use GPU Louvain (fast)")
        print("    Stage 4 will use GPU ForceAtlas2 (fast)")
        return True
    else:
        print("\n  ✗ RAPIDS is missing components")
        print("\n  To install RAPIDS, run:")
        print("    pip install cudf-cu12 cugraph-cu12  # For CUDA 12")
        print("    # OR for CUDA 11:")
        print("    pip install cudf-cu11 cugraph-cu11")
        print("\n  Without RAPIDS:")
        print("    ✗ Stage 3 will use CPU Louvain (WEEKS for 50M papers!)")
        print("    ✗ Stage 4 will use CPU igraph DRL (WEEKS for 50M papers!)")
        return False

def check_fallbacks():
    """Check fallback CPU libraries."""
    print("\n" + "=" * 70)
    print("FALLBACK CPU LIBRARIES")
    print("=" * 70)
    
    igraph_ok = run_check("igraph", "igraph")
    networkx_ok = run_check("networkx", "networkx")
    louvain_ok = run_check("community", "community")
    
    print("\n  Status:")
    if igraph_ok:
        print("    ✓ Stage 4 CPU fallback available (but will be slow)")
    else:
        print("    ✗ Stage 4 CPU fallback unavailable (igraph missing)")
    
    if louvain_ok:
        print("    ✓ Stage 3 CPU fallback available (but will be VERY slow)")
    else:
        print("    ✗ Stage 3 CPU fallback unavailable (community missing)")

def main():
    print("\n" + "=" * 70)
    print("GPU & RAPIDS DIAGNOSTIC")
    print("=" * 70)
    
    gpu_ok = check_cuda_devices()
    pytorch_ok = check_pytorch()
    rapids_ok = check_rapids()
    check_fallbacks()
    
    print("\n" + "=" * 70)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 70)
    
    if not gpu_ok:
        print("\n  ⚠️  NO GPU DETECTED")
        print("     → Your pipeline will run on CPU only (VERY SLOW)")
        print("     → Check NVIDIA drivers: nvidia-smi")
        sys.exit(1)
    
    if not pytorch_ok:
        print("\n  ⚠️  PYTORCH/CUDA NOT AVAILABLE")
        print("     → Install PyTorch with CUDA support:")
        print("       pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu12")
        sys.exit(1)
    
    if not rapids_ok:
        print("\n  ⚠️  WARNING: RAPIDS NOT FULLY INSTALLED")
        print("     ✓ GPU is available but RAPIDS (cudf/cugraph) is missing")
        print("     → Stage 3 & 4 will use CPU algorithms (WEEKS for 50M papers!)")
        print("")
        print("     To enable GPU acceleration, install RAPIDS:")
        print("       pip install cudf-cu12 cugraph-cu12")
        print("")
        print("     Or try the batched FR GPU layout fallback (Stage 4)")
        print("")
        sys.exit(1)
    
    print("\n   GPU SETUP LOOKS GOOD!")
    print("     ✓ GPU detected")
    print("     ✓ PyTorch/CUDA available")
    print("     ✓ RAPIDS (cudf/cugraph) available")
    print("")
    print("  Your pipeline SHOULD use GPU acceleration:")
    print("    • Stage 1 (Ingest): CPU multi-threading (already optimized)")
    print("    • Stage 2 (Deduplicate): SQLite + GPU node isolation")
    print("    • Stage 3 (Community): GPU Louvain via cuGraph (FAST)")
    print("    • Stage 4 (Layout): GPU ForceAtlas2 or batched FR (FAST)")
    print("    • Stage 5 (Export): CPU JSON generation")
    print("")
    print("  Expected performance for 54M papers:")
    print("    • Stage 1: 20-40 min (CPU threading)")
    print("    • Stage 3: 1-3 hours (GPU Louvain)")
    print("    • Stage 4: 1-2 hours (GPU layout)")
    print("    • Total: ~3-5 hours")
    print("")
    print("  Monitor GPU usage during pipeline:")
    print("    nvidia-smi -l 1  (updates every 1 second)")
    print("    nvtop             (interactive GPU monitor)")

if __name__ == "__main__":
    main()
