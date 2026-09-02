"""
src/plasma_column/hardware.py

Hardware detection and runtime environment configuration for WarpX/AMReX.
Provides automatic detection of GPU availability and configuration of
CPU threads (OpenMP, MKL, NumExpr) and GPU devices (CUDA/HIP).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def detect_gpu() -> int | None:
    """
    Check if an NVIDIA or compatible GPU accelerator is available on the system.

    Detection sequence:
    1. PyTorch CUDA check (if torch is installed and CUDA is available)
    2. nvidia-smi execution and device query
    3. Direct check for /dev/nvidia0 device node

    Returns:
        int: Primary GPU device index (typically 0) if a GPU is detected.
        None: If no compatible GPU device is found.
    """
    # 1. Check via PyTorch if available
    try:
        import torch
        if torch.cuda.is_available() and torch.cuda.device_count() > 0:
            return 0
    except Exception:
        pass

    # 2. Check via nvidia-smi
    if shutil.which("nvidia-smi") is not None:
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0 and res.stdout.strip():
                lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
                if lines:
                    return int(lines[0])
        except Exception:
            pass

    # 3. Check for Linux device node
    if Path("/dev/nvidia0").exists():
        return 0

    return None


def configure_runtime(
    cores: int = 8,
    gpu: int | str | None = "auto",
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Configure CPU thread limits and GPU device selection in the process environment.

    Args:
        cores: Number of CPU threads for OpenMP, MKL, NumExpr. Defaults to 8.
        gpu: GPU selection mode:
            - 'auto': Automatically detect GPU; if available, default to GPU 0.
            - int or str (e.g. 0, '0', 1): Explicit GPU device index.
            - None or 'none': Disable GPU selection (CPU only).
        verbose: Whether to print the applied hardware configuration.

    Returns:
        dict: Summary containing applied cores, selected gpu index, and availability status.
    """
    cores = int(cores) if cores is not None else 8
    if cores < 1:
        cores = 1

    # Configure multi-threading environment variables
    os.environ["OMP_NUM_THREADS"] = str(cores)
    os.environ["OPENMP_NUM_THREADS"] = str(cores)
    os.environ["MKL_NUM_THREADS"] = str(cores)
    os.environ["NUMEXPR_NUM_THREADS"] = str(cores)

    # Determine GPU selection
    selected_gpu: int | None = None
    if isinstance(gpu, str) and gpu.lower() in ("none", "false", "off", "cpu"):
        selected_gpu = None
    elif gpu == "auto":
        selected_gpu = detect_gpu()
    elif gpu is not None:
        try:
            selected_gpu = int(gpu)
        except (ValueError, TypeError):
            selected_gpu = None

    if selected_gpu is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(selected_gpu)
        os.environ["HIP_VISIBLE_DEVICES"] = str(selected_gpu)

    info = {
        "cores": cores,
        "gpu": selected_gpu,
        "gpu_available": selected_gpu is not None,
    }

    if verbose:
        gpu_str = f"GPU {selected_gpu} (enabled)" if selected_gpu is not None else "None (CPU execution)"
        print(f"[Hardware Config] CPU Cores: {cores} | Accelerator: {gpu_str}")

    return info
