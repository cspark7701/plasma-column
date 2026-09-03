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
import pandas as pd

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
from plasma_column.plotting import plot_cross_section_comparison


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

    # Load full curves and build DataFrames
    e_h2, sig_h2, _ = load_cross_section_table(h2_file)
    e_kr, sig_kr, _ = load_cross_section_table(kr_file)

    h2_df = pd.DataFrame({"energy_kev": e_h2 / 1000.0, "sigma_m2": sig_h2})
    kr_df = pd.DataFrame({"energy_kev": e_kr / 1000.0, "sigma_m2": sig_kr})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    png_path, pdf_path = plot_cross_section_comparison(
        h2_df,
        kr_df,
        output_dir=args.output_dir,
        operating_energy_kev=30.0,
        output_name="h2_kr_cross_sections",
    )

    print(f"\nSaved cross section figures:")
    print(f"  PNG: {png_path}")
    print(f"  PDF: {pdf_path}")


if __name__ == "__main__":
    main()
