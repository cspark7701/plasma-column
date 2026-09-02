#!/usr/bin/env python3
"""
scripts/run_scan.py

Parameter scan and matrix launcher for simulation method comparison cases.
Parses matrix YAML files via SimulationCaseConfig, builds isolated case directories (runs/<case_name>/),
logs machine-readable metadata.json and config.yaml for each case, and executes or validates runs.

Usage:
    python scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run
    python scripts/run_scan.py --matrix cases/method_comparison.yaml --run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    import _path_setup  # noqa: F401
except ImportError:
    from scripts import _path_setup  # noqa: F401

from plasma_column.schema import (
    SimulationCaseConfig,
    build_warpx_cmd_flags,
    get_runner_script,
)
from plasma_column.warpx_io import collect_metadata
from plasma_column.hardware import configure_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run or validate a matrix of plasma column simulation cases."
    )
    parser.add_argument(
        "--matrix",
        required=True,
        type=Path,
        help="Path to YAML matrix configuration file (e.g., cases/method_comparison.yaml).",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Validate case configurations and write metadata without executing PIC steps.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute simulation runs for all cases in the matrix.",
    )
    parser.add_argument(
        "--cores",
        type=int,
        default=8,
        help="Number of CPU worker cores / OpenMP threads (default: 8).",
    )
    parser.add_argument(
        "--gpu",
        default="auto",
        help="GPU device ID (e.g. 0) or 'auto' (enables GPU 0 if available, default: auto).",
    )
    return parser.parse_args()


def merge_dicts(default: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = default.copy()
    for key, val in override.items():
        if isinstance(val, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = merge_dicts(merged[key], val)
        else:
            merged[key] = val
    return merged


def main() -> None:
    args = parse_args()

    # Configure hardware runtime (default cores=8, GPU auto-detected)
    configure_runtime(cores=args.cores, gpu=args.gpu)

    if not args.matrix.exists():
        print(f"Error: Matrix configuration file '{args.matrix}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(args.matrix, "r", encoding="utf-8") as f:
        matrix_data = yaml.safe_load(f)

    matrix_name = matrix_data.get("matrix_name", args.matrix.stem)
    defaults = matrix_data.get("defaults", {})
    cases = matrix_data.get("cases", [])

    print("=" * 85)
    print(f" Matrix Scan: {matrix_name} ({'DRY RUN' if args.dry_run else 'RUN'})")
    print("=" * 85)
    print(f"  Matrix File : {args.matrix}")
    print(f"  Total Cases : {len(cases)}\n")

    print(f"{'Case Name':<25} | {'Gas':<5} | {'Pressure [Torr]':<15} | {'Method Category':<30}")
    print("-" * 85)

    for case_item in cases:
        case_name = case_item.get("case_name", "unnamed_case")
        gas = case_item.get("gas", "none")
        pressure = case_item.get("pressure_torr", 0.0)
        cat = case_item.get("method_category", "unspecified")

        print(f"{case_name:<25} | {gas:<5} | {pressure:<15.1e} | {cat:<30}")

        # Build full merged config for case and validate schema
        raw_config = merge_dicts(defaults, case_item)
        try:
            config = SimulationCaseConfig.from_dict(raw_config)
        except Exception as exc:
            print(f"Error validating case '{case_name}': {exc}", file=sys.stderr)
            sys.exit(1)

        # Output directory
        output_dir = Path("results") / case_name
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate metadata
        metadata = collect_metadata(config, args.matrix)

        # Write config.yaml and metadata.json
        with open(output_dir / "config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)

        with open(output_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        if not args.dry_run:
            print(f"  --> Launching PIC simulation for {case_name} (gas={gas}, p={pressure:.1e} Torr)...", flush=True)
            script_path = get_runner_script(config.method)
            cmd = [
                sys.executable,
                str(script_path),
                "--output_dir", str(output_dir),
                "--gas", gas if gas != "none" else "H2",
                "--pressure_torr", str(pressure),
                "--max_steps", str(config.numerics.max_steps),
                "--beam_energy_keV", str(config.beam.energy_keV),
                "--beam_current_mA", str(config.beam.current_mA),
                "--cores", str(args.cores),
                "--gpu", str(args.gpu),
                "--run",
            ]
            # Map physics method to WarpX CLI flags via the single canonical helper (RT-02)
            cmd += build_warpx_cmd_flags(config.method)

            res = subprocess.run(cmd)
            if res.returncode != 0:
                print(f"Error: Simulation failed for {case_name} (exit code {res.returncode})", file=sys.stderr)
                sys.exit(res.returncode)

            # Postprocess case
            postproc_script = Path(__file__).resolve().parent / "postprocess_case.py"
            if postproc_script.exists():
                subprocess.run([sys.executable, str(postproc_script), "--case-dir", str(output_dir)])

    print("-" * 85)
    if args.dry_run:
        print(f"[DRY RUN SUCCESS] All {len(cases)} cases validated and metadata generated under results/", flush=True)
    else:
        print(f"[RUN COMPLETE] Full PIC matrix production execution finished for {len(cases)} cases.", flush=True)


if __name__ == "__main__":
    main()
