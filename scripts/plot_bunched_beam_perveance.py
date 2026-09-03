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

try:
    import _path_setup  # noqa: F401
except ImportError:
    from scripts import _path_setup  # noqa: F401

from plasma_column.beam import RFFocusedBeam
from plasma_column.plotting import plot_bunched_beam_perveance_scan


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

    args.output_dir.mkdir(parents=True, exist_ok=True)
    png_path, pdf_path = plot_bunched_beam_perveance_scan(
        eta_levels=eta_avg_levels,
        output_dir=args.output_dir,
        bunching_factor_max=10.0,
        output_name="bunched_beam_perveance",
    )

    print(f"\nSaved bunched beam perveance figures:")
    print(f"  PNG: {png_path}")
    print(f"  PDF: {pdf_path}")


if __name__ == "__main__":
    main()
