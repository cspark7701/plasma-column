#!/usr/bin/env python3
"""
scripts/postprocess_case.py

Postprocessing CLI wrapper for simulation case directories.
Evaluates global particle number metrics and local beam-core compensation indicators.

Generates:
- global_particle_number.csv
- neutralization_from_particle_number.csv
- local_neutralization_vs_t.csv
- local_neutralization_vs_z.csv
- beam_core_charge_density.csv
- radial_density_profiles.csv
- diagnostics_summary.json

Usage:
    python scripts/postprocess_case.py --case-dir runs/seeded_H2_baseline --dry_run
    python scripts/postprocess_case.py --case-dir runs/seeded_H2_baseline
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.diagnostics import postprocess_case_directory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Postprocess plasma column simulation output directory."
    )
    parser.add_argument(
        "--case-dir",
        "--case_dir",
        required=True,
        type=Path,
        help="Path to case output directory (e.g., runs/seeded_H2_baseline).",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Validate paths and diagnostic availability without generating output files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    case_dir = args.case_dir

    if not case_dir.exists():
        print(f"Error: Case directory '{case_dir}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"[{'DRY RUN' if args.dry_run else 'POSTPROCESS'}] Case Directory: {case_dir}")

    summary = postprocess_case_directory(case_dir, dry_run=args.dry_run, generate_plots=True)

    if args.dry_run:
        print(f"  Found particle diagnostic: {summary.get('particle_diag_file')}")
        print(f"  Found plotfiles           : {summary.get('plotfile_count', 0)}")
        print(f"  Has local diagnostics     : {summary.get('has_local_diagnostics', False)}")
        print(f"[DRY RUN SUCCESS] Validated diagnostics for {case_dir}.")
    else:
        print(f"  Processed case: {summary.get('case_name')}")
        print(f"  Diagnostics summary saved under: {case_dir / 'diagnostics_summary.json'}")


if __name__ == "__main__":
    main()
