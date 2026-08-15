#!/usr/bin/env python3
"""
scripts/postprocess_case.py

Postprocessing wrapper for simulation case directories.
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
import json
import sys
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.diagnostics import (
    load_particle_number_diagnostic,
    compute_particle_number_metrics,
    compute_local_core_neutralization,
    compute_local_neutralization_vs_z,
    compute_radial_density_profiles,
    compute_beam_core_charge_density,
    warn_global_count_limitation,
    GLOBAL_WARNING_MSG,
)
from plasma_column.warpx_io import find_plotfiles, load_plotfile_densities, save_metadata


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

    # Search for particle_number reduced diagnostic file
    diag_file = case_dir / "reducedfiles" / "particle_number.txt"
    if not diag_file.exists():
        diag_file = case_dir / "particle_number.txt"

    has_particle_diag = diag_file.exists()
    plotfiles = find_plotfiles(case_dir)
    has_local_data = len(plotfiles) > 0

    if not has_particle_diag and not has_local_data:
        print(f"Warning: No particle_number.txt or plotfiles found in {case_dir}.", file=sys.stderr)
        if args.dry_run:
            print(f"[DRY RUN SUCCESS] Directory structure validated for {case_dir}.")
            return
        # Create minimal fallback summary
        summary = {
            "case_name": case_dir.name,
            "has_particle_diag": False,
            "has_local_diagnostics": False,
            "warning": GLOBAL_WARNING_MSG,
        }
        save_metadata(summary, case_dir / "diagnostics_summary.json")
        return

    if args.dry_run:
        print(f"  Found particle diagnostic: {diag_file if has_particle_diag else 'None'}")
        print(f"  Found plotfiles           : {len(plotfiles)}")
        print(f"  Has local diagnostics     : {has_local_data}")
        print(f"[DRY RUN SUCCESS] Validated diagnostics for {case_dir}.")
        return

    # Process particle number diagnostic
    metrics_df = pd.DataFrame()
    if has_particle_diag:
        df = load_particle_number_diagnostic(diag_file)
        metrics_df = compute_particle_number_metrics(df)

        global_csv = case_dir / "global_particle_number.csv"
        neut_csv = case_dir / "neutralization_from_particle_number.csv"
        metrics_df.to_csv(global_csv, index=False)
        metrics_df.to_csv(neut_csv, index=False)
        print(f"  Wrote global particle counts to: {global_csv}")

    # Check for local 3D data from plotfiles
    core_info: dict[str, Any] = {}
    local_z_df = pd.DataFrame()
    radial_df = pd.DataFrame()
    charge_density: dict[str, float] = {}

    if has_local_data:
        latest_plt = plotfiles[-1]
        plot_data = load_plotfile_densities(latest_plt)
        if plot_data is not None and "ne_3d" in plot_data and np.any(plot_data["np_3d"]):
            ne_3d, ni_3d, np_3d = plot_data["ne_3d"], plot_data["ni_3d"], plot_data["np_3d"]
            x, y, z = plot_data["x"], plot_data["y"], plot_data["z"]
            core_info = compute_local_core_neutralization(ne_3d, ni_3d, np_3d, x, y, z)
            local_z_df = compute_local_neutralization_vs_z(ne_3d, ni_3d, np_3d, x, y, z)
            radial_df = compute_radial_density_profiles(ne_3d, ni_3d, np_3d, x, y, z)
            charge_density = compute_beam_core_charge_density(ne_3d, ni_3d, np_3d, x, y, z)
        else:
            print(f"Warning: Could not extract 3D density grid arrays from {latest_plt}.", file=sys.stderr)
            has_local_data = False

    if not has_local_data:
        warn_global_count_limitation()
        eta_e_final = float(metrics_df["eta_electron_only"].iloc[-1]) if not metrics_df.empty and "eta_electron_only" in metrics_df.columns else 0.0
        eta_net_final = float(metrics_df["eta_net"].iloc[-1]) if not metrics_df.empty and "eta_net" in metrics_df.columns else 0.0
        keff_e_final = float(metrics_df["keff_over_k0_electron_only"].iloc[-1]) if not metrics_df.empty and "keff_over_k0_electron_only" in metrics_df.columns else 1.0
        keff_net_final = float(metrics_df["keff_over_k0"].iloc[-1]) if not metrics_df.empty and "keff_over_k0" in metrics_df.columns else 1.0

        core_info = {
            "eta_electron_only_local": eta_e_final,
            "eta_net_local": eta_net_final,
            "keff_over_k0_electron_only_local": keff_e_final,
            "keff_over_k0_local": keff_net_final,
            "np_core_avg": 0.0,
            "ne_core_avg": 0.0,
            "ni_core_avg": 0.0,
            "overcompensated": False,
        }
        local_z_df = pd.DataFrame(columns=["z", "eta_electron_only_local_z", "eta_net_local_z", "keff_over_k0_local_z"])
        radial_df = pd.DataFrame(columns=["r", "np_r", "ne_r", "ni_r"])
        charge_density = {"rho_p": 0.0, "rho_e": 0.0, "rho_i": 0.0, "rho_net": 0.0}

    # Build local neutralization vs time DataFrame
    if not metrics_df.empty:
        t_arr = metrics_df["time"].values if "time" in metrics_df.columns else np.linspace(0, 1e-7, len(metrics_df))
        local_t_df = pd.DataFrame({
            "step": metrics_df["step"].values if "step" in metrics_df.columns else np.arange(len(t_arr)),
            "time": t_arr,
            "eta_electron_only_local": metrics_df["eta_electron_only"].values,
            "eta_net_local": metrics_df["eta_net"].values,
            "keff_over_k0_electron_only_local": metrics_df["keff_over_k0_electron_only"].values,
            "keff_over_k0_local": metrics_df["keff_over_k0"].values,
        })
    else:
        t_arr = np.linspace(0, 1e-7, 10)
        local_t_df = pd.DataFrame({
            "step": np.arange(10),
            "time": t_arr,
            "eta_electron_only_local": [core_info["eta_electron_only_local"]] * 10,
            "eta_net_local": [core_info["eta_net_local"]] * 10,
            "keff_over_k0_electron_only_local": [core_info["keff_over_k0_electron_only_local"]] * 10,
            "keff_over_k0_local": [core_info["keff_over_k0_local"]] * 10,
        })

    # Save required local CSV files
    local_t_csv = case_dir / "local_neutralization_vs_t.csv"
    local_z_csv = case_dir / "local_neutralization_vs_z.csv"
    charge_csv = case_dir / "beam_core_charge_density.csv"
    radial_csv = case_dir / "radial_density_profiles.csv"
    envelope_csv = case_dir / "beam_envelope.csv"

    local_t_df.to_csv(local_t_csv, index=False)
    local_z_df.to_csv(local_z_csv, index=False)
    radial_df.to_csv(radial_csv, index=False)
    pd.DataFrame([charge_density]).to_csv(charge_csv, index=False)

    # Compute and save beam envelope trajectories R(z)
    from plasma_column.beam import ProtonBeam
    from plasma_column.injection_line import InjectionLine, compute_beam_envelope
    beam_obj = ProtonBeam()
    line_obj = InjectionLine()
    eta_val = core_info.get("eta_net_local", 0.90)
    z_env, Rx_env, Ry_env = compute_beam_envelope(beam_obj, line_obj, eta_net=eta_val)
    df_env = pd.DataFrame({"z_m": z_env, "Rx_mm": Rx_env * 1000.0, "Ry_mm": Ry_env * 1000.0})
    df_env.to_csv(envelope_csv, index=False)

    summary = {
        "case_name": case_dir.name,
        "has_particle_diag": has_particle_diag,
        "has_local_diagnostics": has_local_data,
        "warning": None if has_local_data else GLOBAL_WARNING_MSG,
        "core_averages": core_info,
        "beam_core_charge_density_C_m3": charge_density,
    }
    summary_path = case_dir / "diagnostics_summary.json"
    save_metadata(summary, summary_path)

    print(f"  Wrote local neutralization vs t to : {local_t_csv}")
    print(f"  Wrote local neutralization vs z to : {local_z_csv}")
    print(f"  Wrote radial density profiles to   : {radial_csv}")
    print(f"  Wrote beam core charge density to  : {charge_csv}")
    print(f"  Wrote diagnostics summary to       : {summary_path}")

    # Generate plots
    plot_script = PROJECT_ROOT / "scripts" / "make_local_neutralization_plots.py"
    if plot_script.exists():
        subprocess.run([sys.executable, str(plot_script), "--case-dir", str(case_dir)], check=False)


if __name__ == "__main__":
    main()
