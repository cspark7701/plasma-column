#!/usr/bin/env python3
"""
scripts/freeze_publication_dataset.py

Freezes the canonical publication dataset, computes SHA-256 checksums,
and generates paper/data/ dataset files and dataset_manifest.json.

Usage:
    python scripts/freeze_publication_dataset.py --dry_run
    python scripts/freeze_publication_dataset.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.warpx_io import freeze_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze canonical publication datasets with SHA-256 cryptographic verification."
    )
    parser.add_argument(
        "--source_dir",
        "--source-dir",
        type=Path,
        default=PROJECT_ROOT / "data",
        help="Source directory containing simulation summary datasets.",
    )
    parser.add_argument(
        "--output_dir",
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "paper" / "data",
        help="Target output directory for frozen datasets and manifest.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Compute SHA-256 checksums and validate manifest without copying files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"=== Freezing Publication Dataset [{'DRY RUN' if args.dry_run else 'WRITE'}] ===")

    manifest = freeze_dataset(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )

    files = manifest.get("files", {})
    print(f"  Processed {len(files)} files:")
    for fname, info in files.items():
        print(f"    - {fname} ({info['size_bytes']} bytes, SHA-256: {info['sha256'][:12]}...)")

    if args.dry_run:
        print(f"  [DRY RUN SUCCESS] Validated dataset manifest without writing files.")
    else:
        print(f"  Wrote dataset manifest to: {args.output_dir / 'dataset_manifest.json'}")


if __name__ == "__main__":
    main()
