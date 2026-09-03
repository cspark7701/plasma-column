#!/usr/bin/env python3
"""
scripts/analyze_bunched_beam_neutralization.py

Evaluates RF-bunched beam perveance scaling, bunch duration/length, and average vs peak-bunch
compensation ratios across bunching factors B_f = 1, 2, 3, 5, 10.

Generated CSV Files:
- data/bunched_beam_compensation_scan.csv

Generated Plots:
- plots/peak_Keff_vs_bunching_factor.png / .pdf
- plots/bunch_length_vs_phase_width.png / .pdf
- plots/average_vs_peak_compensation.png / .pdf

Usage:
    python scripts/analyze_bunched_beam_neutralization.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.beam import compute_bunched_beam_compensation_scan
from plasma_column.plotting import (
    plot_peak_keff_vs_bunching_factor,
    plot_bunch_length_vs_phase_width,
    plot_average_vs_peak_compensation,
    setup_publication_style,
)


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

    # 1. Compute bunching factor scan B_f = 1, 2, 3, 5, 10
    df_scan = compute_bunched_beam_compensation_scan()
    out_csv = PROJECT_ROOT / "data" / "bunched_beam_compensation_scan.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_scan.to_csv(out_csv, index=False)
    print(f"  Wrote scan summary to: {out_csv}")

    # 2. Plot Peak Keff/K0 vs Bunching Factor
    p1, p2 = plot_peak_keff_vs_bunching_factor(df_scan, plots_dir)
    print(f"  Saved: {p1} / {p2}")

    # 3. Plot Bunch length vs phase width
    p1, p2 = plot_bunch_length_vs_phase_width(plots_dir, energy_keV=30.0, rf_frequency_hz=50.0e6)
    print(f"  Saved: {p1} / {p2}")

    # 4. Plot Average vs Peak Compensation
    p1, p2 = plot_average_vs_peak_compensation(df_scan, plots_dir, bunching_factor=5.0)
    print(f"  Saved: {p1} / {p2}")


if __name__ == "__main__":
    main()
