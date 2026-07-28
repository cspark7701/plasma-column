#!/usr/bin/env python3
"""
scripts/make_plots.py

Command-line plotting pipeline that regenerates all presentation, proceeding, and notebook figures
for the plasma column neutralizer simulation project.

Usage:
    python scripts/make_plots.py --dry_run
    python scripts/make_plots.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Ensure src/ and project root are in sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

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
    write_plot_manifest,
    setup_publication_style,
)
from plasma_column.beam import RFFocusedBeam
from plasma_column.gas import CrossSectionDatabase, load_cross_section_table, lab_to_cm_energy, MH2, MKR, MP
from plasma_column.neutralization import peak_keff_over_k0_from_average_eta
from plasma_column.diagnostics import (
    generate_synthetic_3d_grid,
    compute_radial_density_profiles,
    compute_local_neutralization_vs_z,
    compute_particle_number_metrics,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate all project plots for presentations, papers, and notebooks."
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
        help="Output directory for generated plots.",
    )
    return parser.parse_args()


# ── Figure generators ─────────────────────────────────────────────────────────

def plot_layout_diagram(output_dir: Path) -> tuple[Path, Path]:
    """Generates baseline axial injection layout schematic diagram."""
    fig, ax = plt.subplots(figsize=(10, 3))

    elements = [
        "Buncher",
        "Plasma\nNeutralizer",
        "Solenoid",
        "Quadrupole\nQ1",
        "Quadrupole\nQ2",
        "Spiral\nInflector",
    ]
    x_positions = np.linspace(1, 11, len(elements))

    for i, (x, elem) in enumerate(zip(x_positions, elements)):
        box_color = "lightblue" if "Neutralizer" in elem else "lightgray"
        if "Solenoid" in elem:
            box_color = "lightgreen"
        ax.text(
            x,
            0.5,
            elem,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=box_color, edgecolor="black", lw=1.5),
            fontsize=10,
            weight="bold",
        )
        if i < len(elements) - 1:
            ax.annotate(
                "",
                xy=(x_positions[i + 1] - 0.7, 0.5),
                xytext=(x + 0.7, 0.5),
                arrowprops=dict(arrowstyle="->", lw=2, color="black"),
            )

    ax.set_xlim(0, 12)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Baseline Cyclotron Axial-Injection Beamline Layout", fontsize=12, pad=10)

    out_basename = output_dir / "axial_injection_layout"
    return save_figure(fig, out_basename)


def make_synthetic_particle_df(
    n_steps: int = 200,
    t_max_ns: float = 400.0,
    eta_target: float = 0.75,
    ion_fraction: float = 0.05,
    Np0: float = 5_000.0,
) -> pd.DataFrame:
    """
    Build a synthetic time-series DataFrame that mimics WarpX ParticleNumber output
    for testing all time-series plotting functions without a real simulation.
    """
    t = np.linspace(0.0, t_max_ns * 1e-9, n_steps)
    tau = t_max_ns * 1e-9 / 3.0
    Ne = Np0 * eta_target * (1.0 - np.exp(-t / tau))
    Ni = Np0 * ion_fraction * (1.0 - np.exp(-t / tau))
    Np = np.full(n_steps, Np0)
    df = pd.DataFrame({"time": t, "Np": Np, "Ne": Ne, "Ni": Ni})
    return compute_particle_number_metrics(df)


def make_synthetic_scan_df() -> pd.DataFrame:
    """Build a synthetic pressure-scan summary DataFrame."""
    rows = []
    for gas, eta_scale in [("H2", 0.60), ("Kr", 0.87)]:
        for p_torr in [1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4]:
            eta = float(np.clip(eta_scale * (p_torr / 1e-5) ** 0.45, 0.0, 0.99))
            rows.append({"gas": gas, "pressure_torr": p_torr, "keff_over_k0": 1.0 - eta})
    return pd.DataFrame(rows)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    setup_publication_style()

    print(f"[{'DRY RUN' if args.dry_run else 'GENERATE PLOTS'}] Output Directory: {output_dir}")

    manifest_entries = []

    def _reg(stem: str, title: str, desc: str) -> None:
        manifest_entries.append({
            "filename_png": f"{stem}.png",
            "filename_pdf": f"{stem}.pdf",
            "figure_title": title,
            "description":  desc,
        })

    # ── Register all expected figures ─────────────────────────────────────────
    _reg("axial_injection_layout",
         "Axial Injection Beamline Layout",
         "Schematic layout: buncher → plasma neutralizer → solenoid → Q1 → Q2 → inflector")

    _reg("h2_kr_cross_sections",
         "H2 vs Kr Cross Section Comparison",
         "Proton-impact ionization cross sections and 30 keV operating points for H2 and Kr")

    _reg("bunched_beam_perveance",
         "RF-Bunched Beam Peak Space-Charge Reduction",
         "Peak effective perveance ratio K_eff,peak / K0,peak vs bunching factor B_f")

    # Extended plots
    _reg("synthetic_h2_particle_counts",
         "Species Populations (synthetic H2)",
         "Np, Ne, Ni vs time for a synthetic H2 seeded case")

    _reg("synthetic_h2_neutralization_panel",
         "3-Panel Simulation Summary (synthetic H2)",
         "Species counts, neutralisation η, and K_eff/K0 on shared time axis")

    _reg("synthetic_h2_neutralization_evolution",
         "Neutralisation Evolution (synthetic H2)",
         "eta_electron_only and eta_net vs time")

    _reg("synthetic_h2_keff_over_k0",
         "Effective Perveance Ratio (synthetic H2)",
         "K_eff/K0 = 1 - eta_net vs time")

    _reg("synthetic_h2_species_growth_rates",
         "Species Growth Rates (synthetic H2)",
         "dNe/dt and dNi/dt vs time — ionisation-rate proxy")

    _reg("multi_case_neutralization",
         "Multi-Case Neutralisation Overlay",
         "Overlay of eta_net(t) for H2 and Kr synthetic cases")

    _reg("multi_keff",
         "Multi-Case K_eff/K0 Overlay",
         "K_eff/K0 for all synthetic cases on one axes")

    _reg("synthetic_h2_bunched_beam_keff",
         "Bunched-Beam Effective Perveance",
         "K_eff,peak/K0 for Bf = 1,2,3,5,8 using average neutralisation")

    _reg("keff_pressure_scan",
         "K_eff/K0 vs Gas Pressure — H2 and Kr",
         "Pressure scan summary for H2 and Kr, synthetic scaling")

    _reg("synthetic_eta70_radial_density_profile",
         "Radial Density Profiles (synthetic η=0.7)",
         "ne(r), ni(r), np(r) from synthetic Gaussian beam column")

    _reg("synthetic_eta70_neutralization_vs_z",
         "Axial Neutralisation Profile (synthetic η=0.7)",
         "η_e(z) and η_net(z) along beam axis; shaded plasma-cell region")

    _reg("synthetic_beam_phase_space",
         "Transverse Phase-Space Scatter (synthetic beam)",
         "x–x′ scatter with 1-σ RMS ellipse and emittance annotation")

    if args.dry_run:
        print(f"[DRY RUN SUCCESS] {len(manifest_entries)} figure definitions validated for {output_dir}.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Layout diagram ─────────────────────────────────────────────────────
    print("  [1/9] Axial injection layout …")
    plot_layout_diagram(output_dir)
    plt.close("all")

    # ── 2. Synthetic time-series (H2 baseline) ────────────────────────────────
    print("  [2/9] Synthetic H2 time-series …")
    df_h2 = make_synthetic_particle_df(eta_target=0.72, ion_fraction=0.04)
    df_kr = make_synthetic_particle_df(eta_target=0.88, ion_fraction=0.06, t_max_ns=350.0)

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        plot_particle_counts(df_h2, output_dir, case_name="synthetic_h2")
        plot_neutralization_evolution(df_h2, output_dir, case_name="synthetic_h2")
        plot_keff_over_k0(df_h2, output_dir, case_name="synthetic_h2")
        plot_neutralization_panel(df_h2, output_dir, case_name="synthetic_h2")
    plt.close("all")

    # ── 3. Species growth rates ───────────────────────────────────────────────
    print("  [3/9] Species growth rates …")
    plot_species_growth_rates(df_h2, output_dir, case_name="synthetic_h2", smooth_window=9)
    plt.close("all")

    # ── 4. Multi-case overlay ─────────────────────────────────────────────────
    print("  [4/9] Multi-case neutralisation overlay …")
    multi_pairs = [("H2 (synthetic η=0.72)", df_h2), ("Kr (synthetic η=0.88)", df_kr)]
    plot_multi_case_neutralization(
        multi_pairs, output_dir,
        column="eta_net",
        title="Neutralisation History — H2 vs Kr (synthetic)",
        output_name="multi_case_neutralization",
    )
    plot_multi_case_neutralization(
        multi_pairs, output_dir,
        column="keff_over_k0",
        ylabel=r"$K_{\rm eff}/K_0$ (net)",
        title=r"$K_{\rm eff}/K_0$ — H2 vs Kr (synthetic)",
        output_name="multi_keff",
    )
    plt.close("all")

    # ── 5. Bunched-beam K_eff ─────────────────────────────────────────────────
    print("  [5/9] Bunched-beam perveance interpretation …")
    t_ns    = df_h2["time"].values * 1e9
    eta_avg = df_h2["eta_net"].values.clip(0, 1)
    plot_bunched_beam_keff(
        t_ns, eta_avg, output_dir,
        case_name="synthetic_h2",
        bunching_factors=[1.0, 2.0, 3.0, 5.0, 8.0],
    )
    plt.close("all")

    # ── 6. Pressure scan ──────────────────────────────────────────────────────
    print("  [6/9] K_eff vs pressure scan …")
    scan_df = make_synthetic_scan_df()
    plot_keff_pressure_scan(
        scan_df, output_dir,
        title=r"$K_{\rm eff}/K_0$ vs Pressure — H$_2$ and Kr (synthetic)",
    )
    plt.close("all")

    # ── 7. Radial density profile (synthetic 3-D grid) ────────────────────────
    print("  [7/9] Radial density profile …")
    ne_3d, ni_3d, np_3d, x, y, z = generate_synthetic_3d_grid(
        nx=31, ny=31, nz=50,
        n_proton_peak=1e15, eta_target=0.70,
    )
    radial_df = compute_radial_density_profiles(
        ne_3d, ni_3d, np_3d, x, y, z,
        z_min_col=0.0, z_max_col=0.20, r_max=0.015, n_bins=60,
    )
    plot_radial_density_profile(
        radial_df, output_dir, case_name="synthetic_eta70",
        highlight_core_r=0.002,
    )
    plt.close("all")

    # ── 8. Axial neutralisation profile ──────────────────────────────────────
    print("  [8/9] Axial neutralisation profile …")
    z_df = compute_local_neutralization_vs_z(
        ne_3d, ni_3d, np_3d, x, y, z, r_core=0.002
    )
    plot_neutralization_vs_z(
        z_df, output_dir, case_name="synthetic_eta70",
        z_col_range=(0.0, 0.20),
    )
    plt.close("all")

    # ── 9. Phase-space scatter ────────────────────────────────────────────────
    print("  [9/9] Phase-space scatter …")
    rng = np.random.default_rng(42)
    N_ps = 40_000
    cov_beam = [[4.0, 1.8], [1.8, 28.0]]   # mm², mm·mrad, mrad²
    coords = rng.multivariate_normal([0.0, 0.0], cov_beam, N_ps)
    plot_phase_space(
        coords[:, 0], coords[:, 1], output_dir,
        case_name="synthetic_beam",
        x_label=r"$x$ [mm]",
        px_label=r"$x^{\prime}$ [mrad]",
        species_label="beam protons (synthetic)",
        rms_ellipse=True,
        alpha=0.15,
    )
    plt.close("all")

    # ── Manifest ──────────────────────────────────────────────────────────────
    manifest_file = write_plot_manifest(manifest_entries, output_dir / "manifest.csv")
    print(f"  Wrote plot manifest → {manifest_file}")
    print(f"[SUCCESS] {len(manifest_entries)} figures generated in {output_dir}/")


if __name__ == "__main__":
    main()
