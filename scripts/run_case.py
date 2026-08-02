#!/usr/bin/env python3
"""
scripts/run_case.py

Execution wrapper and metadata logger for plasma column simulation cases.
Loads case parameters from YAML via SimulationCaseConfig, builds machine-readable metadata.json and config.yaml,
and executes or validates the simulation.

Usage:
    python scripts/run_case.py --case cases/vacuum.yaml --dry_run
    python scripts/run_case.py --case cases/baseline_h2.yaml --dry_run
    python scripts/run_case.py --case cases/baseline_kr.yaml --dry_run
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Any

import yaml

# Ensure src/ is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from plasma_column.schema import SimulationCaseConfig


def get_git_info(path: Path) -> dict[str, str]:
    if not path.is_dir():
        return {"error": f"Path {path} does not exist"}

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=path, text=True
        ).strip()
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=path, text=True
        ).strip()
        status_short = subprocess.check_output(
            ["git", "status", "--short"], cwd=path, text=True
        ).strip()
        return {
            "commit": commit,
            "branch": branch,
            "dirty": bool(status_short),
            "status": status_short if status_short else "Clean",
        }
    except Exception as exc:
        return {"error": str(exc)}


def collect_metadata(case_config: SimulationCaseConfig, case_path: Path) -> dict[str, Any]:
    warpx_dir = Path("/home/cspark/Work/simulation_codes-working/warpx")

    metadata = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "case_file": str(case_path.resolve()),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "python_executable": sys.executable,
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "warpx_source": {
            "path": str(warpx_dir),
            "git": get_git_info(warpx_dir),
        },
        "case_config": case_config.to_dict(),
    }
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run or validate plasma column simulation case from YAML configuration."
    )
    parser.add_argument(
        "--case",
        required=True,
        type=Path,
        help="Path to YAML case configuration file (e.g., cases/vacuum.yaml).",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Validate parameters and write metadata without running full WarpX PIC steps.",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=None,
        help="Override output directory path.",
    )
    parser.add_argument(
        "--max_steps",
        type=int,
        default=None,
        help="Override maximum simulation steps.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.case.exists():
        print(f"Error: Case file '{args.case}' not found.", file=sys.stderr)
        sys.exit(1)

    # Load and validate case configuration using strongly-typed schema
    try:
        config = SimulationCaseConfig.from_yaml(args.case)
    except Exception as exc:
        print(f"Error: Validation failed for case file '{args.case}': {exc}", file=sys.stderr)
        sys.exit(1)

    if args.max_steps is not None:
        config.numerics.max_steps = args.max_steps
        config.validate()

    case_name = config.case_name
    output_dir = args.output_dir if args.output_dir else Path("results") / case_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate metadata
    metadata = collect_metadata(config, args.case)

    # Save machine-readable config and metadata
    config_dest = output_dir / "config.yaml"
    metadata_dest = output_dir / "metadata.json"

    with open(config_dest, "w", encoding="utf-8") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)

    with open(metadata_dest, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"[{'DRY RUN' if args.dry_run else 'RUN'}] Case: {case_name}")
    print(f"  Configuration file : {args.case}")
    print(f"  Output directory   : {output_dir}")
    print(f"  Config saved to    : {config_dest}")
    print(f"  Metadata saved to  : {metadata_dest}")

    gas = config.plasma.gas
    p_torr = config.plasma.pressure_torr
    e_kev = config.beam.energy_keV
    i_ma = config.beam.current_mA
    steps = config.numerics.max_steps

    print(f"  Physics summary    : {e_kev} keV, {i_ma} mA proton beam in {gas} gas ({p_torr:.1e} Torr), steps={steps}")

    if args.dry_run:
        print(f"\n[DRY RUN SUCCESS] Parameters validated and metadata written to {output_dir}.", flush=True)
        return

    print(f"\n[RUNNING] Executing simulation steps for {case_name} (max_steps={steps})...", flush=True)


if __name__ == "__main__":
    main()
