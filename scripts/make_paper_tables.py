#!/usr/bin/env python3
"""
scripts/make_paper_tables.py

Generates publication-quality CSV tables under paper/tables/:
- table_beam_parameters.csv
- table_gas_parameters.csv
- table_simulation_parameters.csv
- table_result_summary.csv
- table_validation_summary.csv

Usage:
    python scripts/make_paper_tables.py --dry_run
    python scripts/make_paper_tables.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.plotting import generate_paper_tables


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate manuscript publication summary tables."
    )
    parser.add_argument(
        "--output_dir",
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "paper" / "tables",
        help="Output directory for generated paper tables.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Validate table definitions without writing CSV files to disk.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"=== Generating Paper Tables [{'DRY RUN' if args.dry_run else 'WRITE'}] ===")

    tables = generate_paper_tables(output_dir=args.output_dir, dry_run=args.dry_run)

    if args.dry_run:
        print(f"  [DRY RUN SUCCESS] Validated {len(tables)} tables:")
        for name, df in tables.items():
            print(f"    - {name}: {len(df)} rows")
    else:
        print(f"  Successfully wrote {len(tables)} tables to: {args.output_dir}")
        for name in tables:
            print(f"    - {name}")


if __name__ == "__main__":
    main()
