#!/usr/bin/env python3
"""
scripts/make_local_neutralization_plots.py

Generates publication-quality figures for local neutralization diagnostics,
z-resolved profiles, radial charge density, and global particle count sanity checks.

Generated Figures:
- plots/{case_name}_particle_counts.png / .pdf
- plots/{case_name}_neutralization_evolution.png / .pdf
- plots/{case_name}_keff_over_k0.png / .pdf
- plots/{case_name}_neutralization_vs_z.png / .pdf
- plots/{case_name}_radial_density_profile.png / .pdf

Usage:
    python scripts/make_local_neutralization_plots.py --case-dir runs/seeded_H2_baseline
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import pandas as pd

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.plotting import (
    plot_particle_counts,
    plot_neutralization_evolution,
    plot_keff_over_k0,
    plot_neutralization_vs_z,
    plot_radial_density_profile,
    setup_publication_style,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate local neutralization diagnostic plots for a case directory."
    )
    parser.add_argument(
        "--case-dir",
        "--case_dir",
        required=True,
        type=Path,
        help="Path to postprocessed case output directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    case_dir = args.case_dir

    if not case_dir.exists():
        print(f"Error: Case directory '{case_dir}' not found.", file=sys.stderr)
        sys.exit(1)

    setup_publication_style()
    plots_dir = case_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    case_name = case_dir.name

    print(f"Generating local neutralization plots for: {case_name}")

    # 1. Global Particle Number Sanity Check
    global_csv = case_dir / "global_particle_number.csv"
    if not global_csv.exists():
        global_csv = case_dir / "neutralization_from_particle_number.csv"

    if global_csv.exists():
        df_g = pd.read_csv(global_csv)
        p1, p2 = plot_particle_counts(
            df_g,
            plots_dir,
            case_name=case_name,
            title=f"Global Particle Number Sanity Check — {case_name}",
        )
        print(f"  Saved: {p1} / {p2}")

    # 2. Local eta and Keff vs time
    local_t_csv = case_dir / "local_neutralization_vs_t.csv"
    if local_t_csv.exists():
        df_lt = pd.read_csv(local_t_csv)
        if not df_lt.empty:
            p1, p2 = plot_neutralization_evolution(
                df_lt,
                plots_dir,
                case_name=case_name,
                title=f"Beam-Core Local Neutralization vs Time — {case_name}",
            )
            print(f"  Saved: {p1} / {p2}")

            p1, p2 = plot_keff_over_k0(
                df_lt,
                plots_dir,
                case_name=case_name,
                title=f"Beam-Core $K_{{eff,local}}/K_0$ vs Time — {case_name}",
            )
            print(f"  Saved: {p1} / {p2}")

    # 3. z-resolved Neutralization Profile
    local_z_csv = case_dir / "local_neutralization_vs_z.csv"
    if local_z_csv.exists():
        df_lz = pd.read_csv(local_z_csv)
        if not df_lz.empty:
            p1, p2 = plot_neutralization_vs_z(
                df_lz,
                plots_dir,
                case_name=case_name,
                z_col_range=(0.0, 0.20),
                title=f"$z$-Resolved Beam-Core Neutralization — {case_name}",
            )
            print(f"  Saved: {p1} / {p2}")

    # 4. Radial Density Profiles
    radial_csv = case_dir / "radial_density_profiles.csv"
    if radial_csv.exists():
        df_r = pd.read_csv(radial_csv)
        if not df_r.empty:
            p1, p2 = plot_radial_density_profile(
                df_r,
                plots_dir,
                case_name=case_name,
                title=f"Radial Species Density Profiles — {case_name}",
            )
            print(f"  Saved: {p1} / {p2}")

    print(f"Plots successfully updated in {plots_dir}.")


if __name__ == "__main__":
    main()
