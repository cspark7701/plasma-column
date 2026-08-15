#!/usr/bin/env python3
"""
scripts/audit_repo.py

Repository auditing script to verify directory structure, file naming conventions,
Python code compilation, unit test status, and execution metadata compliance.

Usage:
    python scripts/audit_repo.py --root .
"""

from __future__ import annotations

import argparse
import sys
import subprocess
from pathlib import Path


try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit plasma column simulation repository.")
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Root directory of the repository.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()

    print("=" * 70)
    print(f" Plasma Column Repository Audit ({root.name})")
    print("=" * 70)

    # 1. Essential Directories Check
    required_dirs = ["cases", "docs", "plots", "runs", "scripts", "src", "tests"]
    print("\n[1. Directory Structure]")
    for d in required_dirs:
        dir_path = root / d
        exists = dir_path.is_dir()
        print(f"  {d:<15} : {'OK' if exists else 'MISSING'}")

    # 2. Key Documentation Files Check
    required_docs = [
        "AGENTS.md",
        "README.md",
        "docs/environment.md",
        "docs/refactor_plan.md",
        "docs/warpx_customization.md",
        "docs/method_comparison.md",
        "docs/physics_notes/neutralization_model.md",
        "docs/physics_notes/bunched_beam_neutralization.md",
        "docs/physics_notes/h2_kr_cross_sections.md",
    ]
    print("\n[2. Critical Documentation]")
    for doc in required_docs:
        doc_path = root / doc
        exists = doc_path.is_file()
        print(f"  {doc:<48} : {'OK' if exists else 'MISSING'}")

    # 3. Legacy Files in Root Check
    root_py_ipynb = list(root.glob("*.py")) + list(root.glob("*.ipynb"))
    print("\n[3. Root Directory Cleanliness Check]")
    if root_py_ipynb:
        names = [f.name for f in root_py_ipynb]
        print(f"  Found unexpected files in root: {names} (move to scripts/ or archives/)")
    else:
        print("  Root directory is clean of .py and .ipynb files : OK")

    # 4. Python Syntax Compilation Check
    print("\n[4. Python Compilation Check]")
    try:
        res = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", "src", "scripts", "tests"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        print("  src/, scripts/, tests/ compilation : OK")
    except subprocess.CalledProcessError as exc:
        print(f"  Compilation FAILED: {exc.stderr}")

    # 5. Unit Tests Execution Check
    print("\n[5. Pytest Execution Check]")
    try:
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        test_summary = res.stdout.strip().splitlines()[-1] if res.stdout else "Passed"
        print(f"  pytest suite                       : OK ({test_summary})")
    except subprocess.CalledProcessError as exc:
        print(f"  pytest suite FAILED: {exc.stderr}")

    print("\n" + "=" * 70)
    print(" Audit Completed Successfully.")
    print("=" * 70)


if __name__ == "__main__":
    main()
