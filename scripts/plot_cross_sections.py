#!/usr/bin/env python3
"""
scripts/plot_cross_sections.py

Plots proton-impact ionization cross sections for H2 and Kr as a function of center-of-mass energy,
marking the 30 keV laboratory operating points. Saves PNG and PDF figures.

Usage:
    python scripts/plot_cross_sections.py --dry_run
    python scripts/plot_cross_sections.py
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

from plasma_column.gas import (
    CrossSectionDatabase,
    load_cross_section_table,
    lab_to_cm_energy,
    MH2,
    MKR,
    MP,
)
from plasma_column.plotting import save_figure


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot H2 and Kr proton-impact ionization cross sections."
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Validate cross-section file paths and operating points without rendering plot files.",
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

    db = CrossSectionDatabase()
    h2_file = db.base_dir / "H2" / "proton_impact_ionization.dat"
    kr_file = db.base_dir / "Kr" / "proton_impact_ionization.dat"

    if not h2_file.exists():
        print(f"Error: Missing H2 cross section file: {h2_file}", file=sys.stderr)
        sys.exit(1)
    if not kr_file.exists():
        print(f"Error: Missing Kr cross section file: {kr_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Found H2 data : {h2_file}")
    print(f"Found Kr data : {kr_file}")

    # Compute 30 keV operating points
    e_lab = 30000.0
    sigma_h2_30k = db.get_proton_impact_cross_section("H2", e_lab)
    sigma_kr_30k = db.get_proton_impact_cross_section("Kr", e_lab)

    e_cm_h2_30k = lab_to_cm_energy(e_lab, MP, MH2)
    e_cm_kr_30k = lab_to_cm_energy(e_lab, MP, MKR)

    print("\n[30 keV Proton Operating Points]")
    print(f"  H2: E_cm = {e_cm_h2_30k:.1f} eV, sigma = {sigma_h2_30k:.4e} m^2")
    print(f"  Kr: E_cm = {e_cm_kr_30k:.1f} eV, sigma = {sigma_kr_30k:.4e} m^2")
    print(f"  Ratio (sigma_Kr / sigma_H2) = {sigma_kr_30k / sigma_h2_30k:.2f}x")

    if args.dry_run:
        print("\n[DRY RUN SUCCESS] Cross-section files and operating points validated.")
        return

    # Load full curves
    e_h2, sig_h2, _ = load_cross_section_table(h2_file)
    e_kr, sig_kr, _ = load_cross_section_table(kr_file)

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(e_h2 / 1000.0, sig_h2 * 1.0e20, label=r"$p^+ + \text{H}_2 \rightarrow p^+ + \text{H}_2^+ + e^-$", color="tab:blue", lw=2)
    ax.plot(e_kr / 1000.0, sig_kr * 1.0e20, label=r"$p^+ + \text{Kr} \rightarrow p^+ + \text{Kr}^+ + e^-$", color="tab:orange", lw=2)

    # Plot operating points
    ax.scatter(
        [e_cm_h2_30k / 1000.0],
        [sigma_h2_30k * 1.0e20],
        color="blue",
        s=80,
        zorder=5,
        label=f"H2 (30 keV lab): {sigma_h2_30k*1e20:.2f} Å²",
    )
    ax.scatter(
        [e_cm_kr_30k / 1000.0],
        [sigma_kr_30k * 1.0e20],
        color="darkorange",
        s=80,
        zorder=5,
        label=f"Kr (30 keV lab): {sigma_kr_30k*1e20:.2f} Å²",
    )

    ax.set_xlabel(r"Center-of-Mass Collision Energy $E_{\text{cm}}$ [keV]", fontsize=12)
    ax.set_ylabel(r"Ionization Cross Section $\sigma_{\text{ion}}$ [$10^{-20} \text{ m}^2$ = Å²]", fontsize=12)
    ax.set_title(r"Proton-Impact Ionization Cross Sections ($\text{H}_2$ vs $\text{Kr}$)", fontsize=13)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.grid(True, which="both", ls="--", alpha=0.5)
    ax.legend(fontsize=10, loc="lower right")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_basename = args.output_dir / "h2_kr_cross_sections"
    png_path, pdf_path = save_figure(fig, out_basename)
    plt.close(fig)

    print(f"\nSaved cross section figures:")
    print(f"  PNG: {png_path}")
    print(f"  PDF: {pdf_path}")


if __name__ == "__main__":
    main()
