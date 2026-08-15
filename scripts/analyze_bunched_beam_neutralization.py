#!/usr/bin/env python3
"""
scripts/analyze_bunched_beam_neutralization.py

Evaluates RF-bunched beam perveance scaling, bunch duration/length, and average vs peak-bunch
compensation ratios across bunching factors B_f = 1, 2, 3, 5, 10.

Generated Plots:
- plots/peak_Keff_vs_bunching_factor.png / .pdf
- plots/bunch_length_vs_phase_width.png / .pdf
- plots/average_vs_peak_compensation.png / .pdf

Usage:
    python scripts/analyze_bunched_beam_neutralization.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.beam import RFFocusedBeam
from plasma_column.plotting import save_figure, setup_publication_style


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze RF-bunched beam space-charge compensation scaling."
    )
    return parser.parse_args()


def main() -> None:
    print("=== Analyzing RF-Bunched Beam Space-Charge Compensation ===")
    setup_publication_style()
    plots_dir = PROJECT_ROOT / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # 1. Bunching factor scan B_f = 1, 2, 3, 5, 10
    bunching_factors = [1.0, 2.0, 3.0, 5.0, 10.0]
    eta_avg_values = [0.0, 0.50, 0.80, 0.90, 0.95]

    scan_records = []

    for Bf in bunching_factors:
        beam = RFFocusedBeam(
            energy_keV=30.0,
            current_mA=10.0,
            rf_frequency_hz=50.0e6,
            bunch_phase_width_deg=36.0,
            bunching_factor=Bf,
        )

        for eta_avg in eta_avg_values:
            k_avg_ratio = 1.0 - eta_avg
            k_peak_ratio = beam.peak_effective_perveance_ratio(eta_avg)

            scan_records.append({
                "bunching_factor": Bf,
                "eta_avg": eta_avg,
                "rf_frequency_hz": beam.rf_frequency_hz,
                "rf_period_s": 1.0 / beam.rf_frequency_hz,
                "bunch_phase_width_deg": beam.bunch_phase_width_deg,
                "bunch_duration_s": beam.bunch_duration_s,
                "bunch_length_m": beam.bunch_length_m,
                "I_avg_mA": beam.beam_current_average_mA,
                "I_peak_mA": beam.beam_current_peak_mA,
                "K0_avg": beam.perveance_K0,
                "K0_peak": beam.peak_perveance_K0,
                "K_eff_avg_over_K0": k_avg_ratio,
                "K_eff_peak_over_K0_peak": k_peak_ratio,
            })

    df_scan = pd.DataFrame(scan_records)
    out_csv = PROJECT_ROOT / "data" / "bunched_beam_compensation_scan.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_scan.to_csv(out_csv, index=False)
    print(f"  Wrote scan summary to: {out_csv}")

    # Plot 1: Peak Keff/K0 vs Bunching Factor for various eta_avg
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for eta_val in [0.50, 0.80, 0.90, 0.95]:
        sub_df = df_scan[df_scan["eta_avg"] == eta_val]
        ax.plot(
            sub_df["bunching_factor"],
            sub_df["K_eff_peak_over_K0_peak"],
            marker="o",
            lw=2,
            label=rf"Average Compensation $\eta_{{\text{{avg}}}} = {eta_val:.2f}$",
        )

    ax.axhline(1.0, color="gray", ls=":", label="Uncompensated Reference")
    ax.set_xlabel("Bunching Factor $B_f = I_{\\text{peak}} / I_{\\text{avg}}$")
    ax.set_ylabel(r"Peak Perveance Ratio $K_{\text{eff,peak}} / K_{0,\text{peak}}$")
    ax.set_title("Peak-Bunch Space-Charge Perveance Reduction vs Bunching Factor")
    ax.legend()
    out1 = plots_dir / "peak_Keff_vs_bunching_factor"
    save_figure(fig, out1)
    plt.close(fig)
    print(f"  Saved: {out1}.png / .pdf")

    # Plot 2: Bunch length vs phase width
    phase_widths = np.linspace(5.0, 90.0, 50)
    beam_ref = RFFocusedBeam(energy_keV=30.0, rf_frequency_hz=50.0e6)
    bunch_lengths_cm = [
        (beam_ref.velocity * (phi / 360.0) / beam_ref.rf_frequency_hz) * 100.0
        for phi in phase_widths
    ]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(phase_widths, bunch_lengths_cm, color="tab:blue", lw=2)
    ax.set_xlabel(r"RF Bunch Phase Width $\Delta \phi$ [deg]")
    ax.set_ylabel(r"Bunch Spatial Length $\Delta z_b$ [cm]")
    ax.set_title(r"RF Bunch Length vs Phase Width ($30\text{ keV}$ Protons, $50\text{ MHz}$)")
    out2 = plots_dir / "bunch_length_vs_phase_width"
    save_figure(fig, out2)
    plt.close(fig)
    print(f"  Saved: {out2}.png / .pdf")

    # Plot 3: Average vs Peak Compensation
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bf_sub = df_scan[df_scan["bunching_factor"] == 5.0]
    ax.plot(bf_sub["eta_avg"], bf_sub["K_eff_avg_over_K0"], label=r"Average Compensation $K_{\text{eff,avg}}/K_0$", color="tab:green", lw=2)
    ax.plot(bf_sub["eta_avg"], bf_sub["K_eff_peak_over_K0_peak"], label=r"Peak-Bunch Compensation $K_{\text{eff,peak}}/K_{0,\text{peak}}$ ($B_f=5$)", color="tab:red", lw=2, ls="--")

    ax.set_xlabel(r"Average Plasma Neutralization Fraction $\eta_{\text{avg}}$")
    ax.set_ylabel("Effective Perveance Ratio")
    ax.set_title("Average vs Peak-Bunch Space-Charge Compensation ($B_f=5$)")
    ax.legend()
    out3 = plots_dir / "average_vs_peak_compensation"
    save_figure(fig, out3)
    plt.close(fig)
    print(f"  Saved: {out3}.png / .pdf")


if __name__ == "__main__":
    main()
