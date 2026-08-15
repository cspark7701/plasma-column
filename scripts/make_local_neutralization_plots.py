#!/usr/bin/env python3
"""
scripts/make_local_neutralization_plots.py

Generates publication-quality figures for local neutralization diagnostics,
z-resolved profiles, radial charge density, and global particle count sanity checks.

Generated Figures:
- plots/local_Keff_over_K0_vs_time.png / .pdf
- plots/local_eta_vs_time.png / .pdf
- plots/radial_density_profiles.png / .pdf
- plots/z_resolved_neutralization.png / .pdf
- plots/global_particle_number_sanity_check.png / .pdf

Usage:
    python scripts/make_local_neutralization_plots.py --case-dir runs/seeded_H2_baseline
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Ensure src/ is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from plasma_column.plotting import save_figure, setup_publication_style


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
        fig, ax = plt.subplots(figsize=(7, 4.5))
        t_ns = df_g["time"].values * 1.0e9 if "time" in df_g.columns else np.arange(len(df_g))

        if "Np" in df_g.columns:
            ax.plot(t_ns, df_g["Np"], label=r"Protons $N_p$", color="tab:blue", lw=2)
        if "Ne" in df_g.columns:
            ax.plot(t_ns, df_g["Ne"], label=r"Electrons $N_e$", color="tab:green", lw=2)
        if "Ni" in df_g.columns:
            ax.plot(t_ns, df_g["Ni"], label=r"Ions $N_i$", color="tab:red", lw=2)

        ax.set_xlabel("Time [ns]")
        ax.set_ylabel("Particle Count")
        ax.set_title(f"Global Particle Number Sanity Check — {case_name}")
        ax.legend()
        out_path = plots_dir / "global_particle_number_sanity_check"
        save_figure(fig, out_path)
        plt.close(fig)
        print(f"  Saved: {out_path}.png / .pdf")

    # 2. Local eta vs time (and electron-only vs net)
    local_t_csv = case_dir / "local_neutralization_vs_t.csv"
    if local_t_csv.exists():
        df_lt = pd.read_csv(local_t_csv)
        if not df_lt.empty:
            t_ns = df_lt["time"].values * 1.0e9 if "time" in df_lt.columns else np.arange(len(df_lt))

            fig, ax = plt.subplots(figsize=(7, 4.5))
            if "eta_electron_only_local" in df_lt.columns:
                ax.plot(t_ns, df_lt["eta_electron_only_local"], label=r"$\eta_{\text{electron\_only,local}} = \langle n_e \rangle / \langle n_p \rangle$", color="tab:green", lw=2)
            if "eta_net_local" in df_lt.columns:
                ax.plot(t_ns, df_lt["eta_net_local"], label=r"$\eta_{\text{net,local}} = (\langle n_e \rangle - \langle n_i \rangle) / \langle n_p \rangle$", color="tab:purple", lw=2, ls="--")

            ax.set_xlabel("Time [ns]")
            ax.set_ylabel("Local Neutralization Fraction")
            ax.set_ylim(-0.05, 1.1)
            ax.set_title(f"Beam-Core Local Neutralization vs Time — {case_name}")
            ax.legend()
            out_path = plots_dir / "local_eta_vs_time"
            save_figure(fig, out_path)
            plt.close(fig)
            print(f"  Saved: {out_path}.png / .pdf")

            # 3. Local Keff/K0 vs time
            fig, ax = plt.subplots(figsize=(7, 4.5))
            if "keff_over_k0_electron_only_local" in df_lt.columns:
                ax.plot(t_ns, df_lt["keff_over_k0_electron_only_local"], label=r"$K_{\text{eff,electron\_only}}/K_0$", color="tab:green", lw=2)
            if "keff_over_k0_local" in df_lt.columns:
                ax.plot(t_ns, df_lt["keff_over_k0_local"], label=r"$K_{\text{eff,net}}/K_0 = 1 - \eta_{\text{net,local}}$", color="tab:red", lw=2, ls="--")

            ax.axhline(0.0, color="gray", lw=1, ls=":")
            ax.set_xlabel("Time [ns]")
            ax.set_ylabel(r"Effective Perveance Ratio $K_{\text{eff,local}}/K_0$")
            ax.set_title(f"Beam-Core $K_{{eff,local}}/K_0$ vs Time — {case_name}")
            ax.legend()
            out_path = plots_dir / "local_Keff_over_K0_vs_time"
            save_figure(fig, out_path)
            plt.close(fig)
            print(f"  Saved: {out_path}.png / .pdf")

    # 4. z-resolved Neutralization Profile
    local_z_csv = case_dir / "local_neutralization_vs_z.csv"
    if local_z_csv.exists():
        df_lz = pd.read_csv(local_z_csv)
        if not df_lz.empty:
            fig, ax = plt.subplots(figsize=(7, 4.5))
            z_cm = df_lz["z"].values * 100.0 if "z" in df_lz.columns else np.arange(len(df_lz))

            if "eta_net_local_z" in df_lz.columns:
                ax.plot(z_cm, df_lz["eta_net_local_z"], label=r"$\eta_{\text{net,local}}(z)$", color="tab:purple", lw=2)
            if "eta_electron_only_local_z" in df_lz.columns:
                ax.plot(z_cm, df_lz["eta_electron_only_local_z"], label=r"$\eta_{\text{electron\_only,local}}(z)$", color="tab:green", lw=2, ls="--")

            ax.axvspan(0.0, 20.0, color="gray", alpha=0.15, label="Plasma Cell Bounds")
            ax.set_xlabel("Longitudinal Position $z$ [cm]")
            ax.set_ylabel("Local Neutralization Fraction")
            ax.set_title(f"$z$-Resolved Beam-Core Neutralization — {case_name}")
            ax.legend()
            out_path = plots_dir / "z_resolved_neutralization"
            save_figure(fig, out_path)
            plt.close(fig)
            print(f"  Saved: {out_path}.png / .pdf")

    # 5. Radial Density Profiles
    radial_csv = case_dir / "radial_density_profiles.csv"
    if radial_csv.exists():
        df_r = pd.read_csv(radial_csv)
        if not df_r.empty:
            fig, ax = plt.subplots(figsize=(7, 4.5))
            r_mm = df_r["r"].values * 1000.0 if "r" in df_r.columns else np.arange(len(df_r))

            if "np_r" in df_r.columns:
                ax.plot(r_mm, df_r["np_r"], label=r"Protons $n_p(r)$", color="tab:blue", lw=2)
            if "ne_r" in df_r.columns:
                ax.plot(r_mm, df_r["ne_r"], label=r"Electrons $n_e(r)$", color="tab:green", lw=2)
            if "ni_r" in df_r.columns:
                ax.plot(r_mm, df_r["ni_r"], label=r"Ions $n_i(r)$", color="tab:red", lw=2)

            ax.set_xlabel("Radial Distance $r$ [mm]")
            ax.set_ylabel(r"Number Density [$\mathrm{m}^{-3}$]")
            ax.set_title(f"Radial Species Density Profiles — {case_name}")
            ax.legend()
            out_path = plots_dir / "radial_density_profiles"
            save_figure(fig, out_path)
            plt.close(fig)
            print(f"  Saved: {out_path}.png / .pdf")

    print(f"Plots successfully updated in {plots_dir}.")


if __name__ == "__main__":
    main()
