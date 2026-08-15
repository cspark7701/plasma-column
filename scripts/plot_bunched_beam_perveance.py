#!/usr/bin/env python3
"""
scripts/plot_bunched_beam_perveance.py

Plots effective peak-bunch space-charge perveance ratio (K_eff,peak / K0,peak)
as a function of RF bunching factor B_f for various average neutralization levels.

Formula:
    K_eff,peak / K0,peak = 1 - eta_avg / B_f

Usage:
    python scripts/plot_bunched_beam_perveance.py --dry_run
    python scripts/plot_bunched_beam_perveance.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

try:
    import _path_setup  # noqa: F401
except ImportError:
    from scripts import _path_setup  # noqa: F401

from plasma_column.beam import RFFocusedBeam
from plasma_column.neutralization import peak_keff_over_k0_from_average_eta
from plasma_column.plotting import save_figure


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot peak-bunch effective perveance ratio vs bunching factor."
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Validate parameters without creating figure files.",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=Path("plots"),
        help="Output directory for plots.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    beam = RFFocusedBeam(
        energy_keV=30.0,
        current_mA=10.0,
        rf_frequency_hz=5.0e7,
        bunch_phase_width_deg=36.0,
        bunching_factor=5.0,
    )

    print("[RF-Bunched Beam Parameters]")
    print(f"  Kinetic Energy    : {beam.energy_keV:.1f} keV")
    print(f"  Beam Velocity     : {beam.velocity:.4e} m/s (beta = {beam.beta:.4f})")
    print(f"  Average Current   : {beam.beam_current_average_mA:.1f} mA")
    print(f"  Peak Current (B=5): {beam.beam_current_peak_mA:.1f} mA")
    print(f"  Bunch Duration    : {beam.bunch_duration_s*1e9:.2f} ns")
    print(f"  Bunch Length      : {beam.bunch_length_m*100.0:.2f} cm")

    eta_avg_levels = [0.50, 0.70, 0.90]
    for eta in eta_avg_levels:
        k_peak_ratio = beam.peak_effective_perveance_ratio(eta)
        print(f"  eta_avg = {eta:.2f}, B_f = 5.0 -> K_eff,peak / K0,peak = {k_peak_ratio:.4f}")

    if args.dry_run:
        print("\n[DRY RUN SUCCESS] RF-bunched beam parameters validated.")
        return

    bf_arr = np.linspace(1.0, 10.0, 200)

    fig, ax = plt.subplots(figsize=(8, 5))

    colors = ["tab:red", "tab:orange", "tab:blue"]
    for eta, color in zip(eta_avg_levels, colors):
        k_ratios = [peak_keff_over_k0_from_average_eta(eta, bf) for bf in bf_arr]
        ax.plot(bf_arr, k_ratios, label=f"Average neutralization $\\eta_{{\\text{{avg}}}} = {eta*100:.0f}\\%$", color=color, lw=2.5)

    # Highlight B_f = 5 operating points
    for eta, color in zip(eta_avg_levels, colors):
        k_val = peak_keff_over_k0_from_average_eta(eta, 5.0)
        ax.scatter([5.0], [k_val], color=color, s=70, zorder=5)

    ax.axvline(5.0, color="gray", ls=":", alpha=0.7, label="Baseline bunching factor $B_f = 5$")
    ax.set_xlabel(r"Bunching Factor $B_f = I_{\text{peak}} / I_{\text{avg}}$", fontsize=12)
    ax.set_ylabel(r"Peak Effective Perveance Ratio $K_{\text{eff,peak}} / K_{0,\text{peak}}$", fontsize=12)
    ax.set_title(r"RF-Bunched Beam Peak Space-Charge Reduction", fontsize=13)
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, ls="--", alpha=0.5)
    ax.legend(fontsize=10, loc="lower right")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_basename = args.output_dir / "bunched_beam_perveance"
    png_path, pdf_path = save_figure(fig, out_basename)
    plt.close(fig)

    print(f"\nSaved bunched beam perveance figures:")
    print(f"  PNG: {png_path}")
    print(f"  PDF: {pdf_path}")


if __name__ == "__main__":
    main()
