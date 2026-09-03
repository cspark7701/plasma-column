#!/usr/bin/env python3
"""
scripts/print_environment.py

Prints diagnostic information about the local Python environment, installed packages,
git status of the plasma_column repository, and WarpX source tree status.
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path


def get_git_info(repo_dir: str | Path) -> dict[str, str]:
    path = Path(repo_dir).resolve()
    if not path.is_dir():
        return {"error": f"Directory {path} does not exist"}

    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=path, text=True
        ).strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=path, text=True
        ).strip()
        status_short = subprocess.check_output(
            ["git", "status", "--short"], cwd=path, text=True
        ).strip()
        return {
            "branch": branch,
            "commit": commit,
            "dirty": bool(status_short),
            "status_summary": status_short if status_short else "Clean",
        }
    except Exception as exc:
        return {"error": f"Failed to get git info: {exc}"}


def main() -> None:
    print("=" * 60)
    print(" Plasma Column Simulation Environment Audit ")
    print("=" * 60)

    # 1. Python Environment
    print(f"\n[Python Environment]")
    print(f"  Python Executable : {sys.executable}")
    print(f"  Python Version    : {sys.version.split()[0]}")
    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "N/A (Derived path: " + str(Path(sys.executable).parent.parent.name) + ")")
    print(f"  Conda Environment : {conda_env}")

    # 2. Hardware & Threading Configuration
    print(f"\n[Hardware & Parallel Runtime]")
    cpu_count = os.cpu_count() or 1
    omp_threads = os.environ.get("OMP_NUM_THREADS", "Not set")
    omp_bind = os.environ.get("OMP_PROC_BIND", "Not set")
    cuda_vis = os.environ.get("CUDA_VISIBLE_DEVICES", "Not set")
    warpx_accel = os.environ.get("WARPX_ACCELERATOR", "Not set")
    print(f"  Available CPUs    : {cpu_count}")
    print(f"  OMP_NUM_THREADS   : {omp_threads}")
    print(f"  OMP_PROC_BIND     : {omp_bind}")
    print(f"  CUDA_VISIBLE_DEVICES: {cuda_vis}")
    print(f"  WARPX_ACCELERATOR : {warpx_accel}")

    # 3. Key Package Dependencies
    print(f"\n[Package Dependencies]")
    packages = ["plasma_column", "numpy", "pandas", "matplotlib", "scipy", "yaml"]
    for pkg in packages:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "Available")
            print(f"  {pkg:<17} : {ver}")
        except ImportError:
            print(f"  {pkg:<17} : NOT INSTALLED")

    # 3. PyWarpX / PICMI Check
    print(f"\n[WarpX / PyWarpX Interface]")
    try:
        import pywarpx
        warpx_file = getattr(pywarpx, "__file__", "Unknown location")
        print(f"  pywarpx import    : OK")
        print(f"  pywarpx location  : {warpx_file}")
    except Exception as exc:
        print(f"  pywarpx import    : FAILED ({exc})")

    # 4. Plasma Column Repository State
    repo_dir = Path(__file__).resolve().parent.parent
    print(f"\n[Plasma Column Repository]")
    print(f"  Path              : {repo_dir}")
    repo_git = get_git_info(repo_dir)
    if "error" in repo_git:
        print(f"  Git Status        : {repo_git['error']}")
    else:
        print(f"  Branch            : {repo_git['branch']}")
        print(f"  Commit            : {repo_git['commit']}")
        print(f"  Status            : {'Modified' if repo_git['dirty'] else 'Clean'}")

    # 5. WarpX Source Tree State
    warpx_src_dir = Path("/home/cspark/Work/simulation_codes-working/warpx")
    print(f"\n[WarpX Source Tree]")
    print(f"  Path              : {warpx_src_dir}")
    warpx_git = get_git_info(warpx_src_dir)
    if "error" in warpx_git:
        print(f"  Git Status        : {warpx_git['error']}")
    else:
        print(f"  Branch            : {warpx_git['branch']}")
        print(f"  Commit            : {warpx_git['commit']}")
        print(f"  Status            : {'Modified' if warpx_git['dirty'] else 'Clean'}")
        if warpx_git['dirty']:
            print("  Modified Files    :")
            for line in warpx_git['status_summary'].splitlines():
                print(f"    {line}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
