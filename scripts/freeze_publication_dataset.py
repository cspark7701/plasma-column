#!/usr/bin/env python3
"""
scripts/freeze_publication_dataset.py

Freezes the canonical publication dataset and generates paper/data/ dataset files and dataset_manifest.json.

Usage:
    python scripts/freeze_publication_dataset.py
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pandas as pd

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.warpx_io import save_metadata


def get_git_commit(path: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    except Exception:
        return "unknown"


def main() -> None:
    print("=== Freezing Canonical Publication Dataset under paper/data/ ===")
    paper_data_dir = PROJECT_ROOT / "paper" / "data"
    paper_data_dir.mkdir(parents=True, exist_ok=True)

    warpx_dir = Path("/home/cspark/Work/simulation_codes-working/warpx")

    cases_frozen = [
        "vacuum_reference",
        "h2_baseline",
        "kr_assisted",
        "h2_bunched",
        "kr_bunched",
        "custom_mcc_h2_verified",
        "custom_mcc_kr_verified",
    ]

    manifest = {
        "dataset_name": "plasma_column_publication_dataset_v1",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "project_git_commit": get_git_commit(PROJECT_ROOT),
        "warpx_git_commit": get_git_commit(warpx_dir),
        "conda_environment": os.environ.get("CONDA_DEFAULT_ENV", "warpx-dev"),
        "cases": cases_frozen,
    }

    # Copy data files from data/ if available or generate canonical summary
    source_data_dir = PROJECT_ROOT / "data"
    if source_data_dir.exists():
        for item in source_data_dir.glob("*.csv"):
            shutil.copy(item, paper_data_dir / item.name)
            print(f"  Frozen: {item.name}")

    save_metadata(manifest, paper_data_dir / "dataset_manifest.json")
    print(f"  Wrote dataset manifest to: {paper_data_dir / 'dataset_manifest.json'}")


if __name__ == "__main__":
    main()
