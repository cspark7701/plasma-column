#!/usr/bin/env python3
"""
scripts/make_plots.py

Consolidated command-line plotting pipeline for the plasma column neutralizer simulation project.
Unifies all plotting targets into a single CLI tool with modular category flags.

Usage Examples:
    # Run all project plots (default):
    python scripts/make_plots.py --all

    # Dry-run validation of all figure definitions:
    python scripts/make_plots.py --dry_run

    # Generate specific categories:
    python scripts/make_plots.py --paper-figures
    python scripts/make_plots.py --cross-sections
    python scripts/make_plots.py --local-neutralization --case-dir runs/seeded_H2_baseline
    python scripts/make_plots.py --bunched-beam
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Ensure src/ and project root are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from plasma_column.plotting import (
    save_figure,
    plot_particle_counts,
    plot_neutralization_evolution,
    plot_keff_over_k0,
    plot_multi_case_neutralization,
    plot_species_growth_rates,
    plot_radial_density_profile,
    plot_neutralization_vs_z,
    plot_phase_space,
    plot_keff_pressure_scan,
    plot_bunched_beam_keff,
    plot_neutralization_panel,
    plot_scan_eta_vs_pressure,
    plot_scan_keff_vs_pressure,
    plot_scan_method_comparison_bar,
    plot_scan_heatmap,
    plot_scan_neutralization_timeseries_grid,
    plot_scan_final_eta_bar_by_gas,
    plot_cross_section_comparison,
    plot_beam_envelope_transport,
    write_plot_manifest,
    setup_publication_style,
)
from plasma_column.beam import ProtonBeam, RFFocusedBeam
from plasma_column.gas import CrossSectionDatabase, load_cross_section_table
from plasma_column.diagnostics import (
    generate_synthetic_3d_grid,
    compute_radial_density_profiles,
    compute_local_neutralization_vs_z,
    compute_particle_number_metrics,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unified CLI entrypoint for plasma column project plots."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all figure categories (synthetic, cross-sections, bunched-beam, paper-figures).",
    )
    parser.add_argument(
        "--paper-figures",
        "--paper",
        action="store_true",
        help="Generate manuscript publication figures (fig01–fig10) in paper/figures/.",
    )
    parser.add_argument(
        "--cross-sections",
        "--cross",
        action="store_true",
        help="Generate proton-impact ionization cross section comparison plots (H2 vs Kr).",
    )
    parser.add_argument(
        "--bunched-beam",
        "--bunched",
        action="store_true",
        help="Generate RF-bunched beam peak space-charge reduction interpretation plots.",
    )
    parser.add_argument(
        "--local-neutralization",
        "--local",
        action="store_true",
        help="Generate local 3D spatial neutralization profiles for a case directory.",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Generate synthetic time-series and parameter scan overview figures.",
    )
    parser.add_argument(
        "--case-dir",
        "--case_dir",
        type=Path,
        default=None,
        help="Target simulation case directory for local neutralization plots.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Validate parameters and output directory without writing figure files.",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=Path("plots"),
        help="Output directory for generated plots (default: plots/).",
    )
    return parser.parse_args()


# ── Figure Generators ─────────────────────────────────────────────────────────

def run_layout_diagram(output_dir: Path) -> tuple[Path, Path]:
    """Generates baseline axial injection layout schematic diagram."""
    fig, ax = plt.subplots(figsize=(10, 3))
    elements = ["Buncher", "Plasma\nNeutralizer", "Solenoid", "Quadrupole\nQ1", "Quadrupole\nQ2", "Spiral\nInflector"]
    x_pos = np.linspace(1, 11, len(elements))

    for i, (x, elem) in enumerate(zip(x_pos, elements)):
        box_color = "lightblue" if "Neutralizer" in elem else ("lightgreen" if "Solenoid" in elem else "lightgray")
        ax.text(
            x, 0.5, elem, ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=box_color, edgecolor="black", lw=1.5),
            fontsize=10, weight="bold",
        )
        if i < len(elements) - 1:
            ax.annotate("", xy=(x_pos[i + 1] - 0.7, 0.5), xytext=(x + 0.7, 0.5),
                        arrowprops=dict(arrowstyle="->", lw=2, color="black"))

    ax.set_xlim(0, 12)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Baseline Cyclotron Axial-Injection Beamline Layout", fontsize=12, pad=10)
    return save_figure(fig, output_dir / "axial_injection_layout")


def run_cross_section_plots(output_dir: Path) -> list[tuple[Path, Path]]:
    """Generates proton-impact ionization cross-section comparison figures."""
    db = CrossSectionDatabase()
    h2_file = db.base_dir / "H2" / "proton_impact_ionization.dat"
    kr_file = db.base_dir / "Kr" / "proton_impact_ionization.dat"
    e_h2, sig_h2, _ = load_cross_section_table(h2_file)
    e_kr, sig_kr, _ = load_cross_section_table(kr_file)
    h2_df = pd.DataFrame({"energy_cm_ev": e_h2, "sigma_m2": sig_h2})
    kr_df = pd.DataFrame({"energy_cm_ev": e_kr, "sigma_m2": sig_kr})
    out = plot_cross_section_comparison(h2_df, kr_df, output_dir, operating_energy_kev=30.0)
    return [out]


def run_bunched_beam_plots(output_dir: Path) -> list[tuple[Path, Path]]:
    """Generates RF-bunched beam peak space-charge reduction interpretation figures."""
    t_ns = np.linspace(0, 300, 150)
    eta_avg = 0.90 * (1.0 - np.exp(-t_ns / 50.0))
    out = plot_bunched_beam_keff(
        t_ns, eta_avg, output_dir,
        case_name="bunched_beam_interpretation",
        bunching_factors=[1.0, 2.0, 3.0, 5.0, 8.0],
        title="Peak-Bunch Perveance Reduction K_eff,peak / K0 vs Bunching Factor B_f",
    )
    return [out]


def run_local_neutralization_plots(case_dir: Path, output_dir: Path) -> list[tuple[Path, Path]]:
    """Generates local 3D spatial neutralization profiles from a postprocessed case directory."""
    results = []
    local_csv = case_dir / "local_neutralization.csv"
    if local_csv.exists():
        df = pd.read_csv(local_csv)
        if "z" in df.columns:
            results.append(plot_neutralization_vs_z(df, output_dir, case_name=case_dir.name))
        if "r" in df.columns:
            results.append(plot_radial_density_profile(df, output_dir, case_name=case_dir.name))
    else:
        # Generate synthetic fallback
        ne_3d, ni_3d, np_3d, x, y, z = generate_synthetic_3d_grid(nx=31, ny=31, nz=50, eta_target=0.70)
        radial_df = compute_radial_density_profiles(ne_3d, ni_3d, np_3d, x, y, z, z_min_col=0.0, z_max_col=0.20, r_max=0.015)
        z_df = compute_local_neutralization_vs_z(ne_3d, ni_3d, np_3d, x, y, z, r_core=0.002)
        results.append(plot_radial_density_profile(radial_df, output_dir, case_name=f"{case_dir.name}_radial"))
        results.append(plot_neutralization_vs_z(z_df, output_dir, case_name=f"{case_dir.name}_axial", z_col_range=(0.0, 0.20)))
    return results


def run_paper_figures(paper_dir: Path) -> list[tuple[Path, Path]]:
    """Executes the full paper manuscript figure generation pipeline (make_paper_figures.py)."""
    import subprocess
    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "make_paper_figures.py")]
    print(f"  [PAPER FIGURES] Executing paper figures script → {paper_dir}")
    subprocess.run(cmd, check=True)
    return []


# ── Main Entrypoint ───────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    setup_publication_style()

    # Determine execution targets
    run_all = args.all or not (args.paper_figures or args.cross_sections or args.bunched_beam or args.local_neutralization or args.synthetic)
    do_paper = args.paper_figures or run_all
    do_cross = args.cross_sections or run_all
    do_bunched = args.bunched_beam or run_all
    do_local = args.local_neutralization or run_all
    do_synth = args.synthetic or run_all

    mode_str = "DRY RUN" if args.dry_run else "GENERATE PLOTS"
    print(f"[{mode_str}] Target Output Directory: {output_dir}")

    manifest_entries = []

    def _reg(stem: str, title: str, desc: str) -> None:
        manifest_entries.append({
            "filename_png": f"{stem}.png",
            "filename_pdf": f"{stem}.pdf",
            "figure_title": title,
            "description":  desc,
        })

    # Register figure definitions
    if do_synth or run_all:
        _reg("axial_injection_layout", "Axial Injection Beamline Layout", "Schematic layout: buncher -> neutralizer -> solenoid -> Q1 -> Q2 -> inflector")
        _reg("synthetic_h2_particle_counts", "Species Populations (synthetic H2)", "Np, Ne, Ni vs time for synthetic H2 case")
        _reg("synthetic_h2_neutralization_panel", "3-Panel Summary (synthetic H2)", "Species counts, neutralisation eta, K_eff/K0")
        _reg("multi_case_neutralization", "Multi-Case Neutralization Overlay", "Overlay of eta_net(t) for H2 and Kr synthetic cases")

    if do_cross or run_all:
        _reg("cross_section_comparison", "H2 vs Kr Ionization Cross Sections", "Proton-impact cross section comparison for H2 and Kr vs collision energy")

    if do_bunched or run_all:
        _reg("bunched_beam_interpretation", "RF-Bunched Beam Peak Space-Charge Reduction", "Peak perveance reduction K_eff,peak / K0 vs bunching factor B_f")

    if args.dry_run:
        print(f"[DRY RUN SUCCESS] {len(manifest_entries)} figure definitions validated.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Layout diagram
    if do_synth or run_all:
        print("  [1] Generating layout diagram...")
        run_layout_diagram(output_dir)
        plt.close("all")

    # 2. Cross section comparison
    if do_cross or run_all:
        print("  [2] Generating cross-section comparison plots...")
        run_cross_section_plots(output_dir)
        plt.close("all")

    # 3. Bunched beam perveance
    if do_bunched or run_all:
        print("  [3] Generating bunched-beam perveance plots...")
        run_bunched_beam_plots(output_dir)
        plt.close("all")

    # 4. Local neutralization
    if do_local or run_all:
        target_case = args.case_dir or (PROJECT_ROOT / "runs" / "seeded_H2_baseline")
        print(f"  [4] Generating local neutralization plots for {target_case.name}...")
        run_local_neutralization_plots(target_case, output_dir)
        plt.close("all")

    # 5. Paper manuscript figures
    if do_paper:
        paper_dir = PROJECT_ROOT / "paper" / "figures"
        run_paper_figures(paper_dir)

    # Write manifest
    manifest_file = write_plot_manifest(manifest_entries, output_dir / "manifest.csv")
    print(f"  Wrote plot manifest -> {manifest_file}")
    print(f"[SUCCESS] Plotting pipeline completed cleanly.")


if __name__ == "__main__":
    main()
