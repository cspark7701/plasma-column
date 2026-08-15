#!/usr/bin/env python3
"""
scripts/transport_to_inflector.py

Simulates space-charge beam envelope transport through the downstream axial injection line:
buncher exit -> plasma neutralizer -> solenoid -> quadrupole Q1 -> quadrupole Q2 -> spiral inflector

Evaluates envelope trajectories R(z), transmission efficiency at inflector entrance, and phase-space distributions.

Generated CSV Files:
- inflector_entrance_summary.csv
- beam_envelope_to_inflector.csv
- phase_space_at_inflector.csv
- transmission_vs_case.csv

Generated Plots:
- plots/envelope_buncher_to_inflector.png / .pdf
- plots/inflector_phase_space_xxp.png / .pdf
- plots/inflector_phase_space_yyp.png / .pdf
- plots/transmission_comparison.png / .pdf

Usage:
    python scripts/transport_to_inflector.py
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

from plasma_column.beam import ProtonBeam
from plasma_column.injection_line import InjectionLine, compute_beam_envelope
from plasma_column.acceptance import InflectorAcceptance, compute_inflector_transmission, generate_phase_space_particles
from plasma_column.plotting import save_figure, setup_publication_style


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate beam envelope transport through injection line to spiral inflector."
    )
    return parser.parse_args()


def main() -> None:
    print("=== Simulating Downstream Transport to Inflector Entrance ===")
    setup_publication_style()
    plots_dir = PROJECT_ROOT / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    beam = ProtonBeam(energy_keV=30.0, current_mA=10.0, radius_m=0.002)
    line = InjectionLine()
    acceptance = InflectorAcceptance(aperture_radius_m=0.005)

    cases = [
        ("vacuum_reference", 0.0, "tab:blue"),
        ("seeded_H2_neutralized", 0.90, "tab:green"),
        ("seeded_Kr_neutralized", 0.95, "tab:purple"),
    ]

    summary_records = []
    envelope_data_dict = {}

    for cname, eta_net, color in cases:
        z_arr, Rx_arr, Ry_arr = compute_beam_envelope(
            beam, line, eta_net=eta_net, r0_m=0.002, rp0_rad=0.0, emittance_n_mrad=1.0e-6
        )

        envelope_data_dict[cname] = (z_arr, Rx_arr, Ry_arr, color)

        # Evaluate inflector entrance metrics
        Rx_end, Ry_end = Rx_arr[-1], Ry_arr[-1]
        dRx_end = (Rx_arr[-1] - Rx_arr[-2]) / (z_arr[-1] - z_arr[-2])
        dRy_end = (Ry_arr[-1] - Ry_arr[-2]) / (z_arr[-1] - z_arr[-2])

        trans_info = compute_inflector_transmission(Rx_end, Ry_end, dRx_end, dRy_end, acceptance)
        trans_info["case_name"] = cname
        trans_info["eta_net"] = eta_net
        summary_records.append(trans_info)

    df_summary = pd.DataFrame(summary_records)

    # Save CSV outputs
    out_summary_csv = PROJECT_ROOT / "data" / "inflector_entrance_summary.csv"
    out_trans_csv = PROJECT_ROOT / "data" / "transmission_vs_case.csv"
    out_summary_csv.parent.mkdir(parents=True, exist_ok=True)
    df_summary.to_csv(out_summary_csv, index=False)
    df_summary[["case_name", "eta_net", "r_beam_mm", "transmission_percent"]].to_csv(out_trans_csv, index=False)

    print(f"  Saved summary to: {out_summary_csv}")
    print(f"  Saved transmission table to: {out_trans_csv}")

    # Save Envelope trajectories CSV
    env_records = []
    z_ref = envelope_data_dict["vacuum_reference"][0]
    for i, z_val in enumerate(z_ref):
        rec = {"z_m": z_val}
        for cname, (z_a, Rx_a, Ry_a, _) in envelope_data_dict.items():
            rec[f"{cname}_Rx_mm"] = Rx_a[i] * 1000.0
            rec[f"{cname}_Ry_mm"] = Ry_a[i] * 1000.0
        env_records.append(rec)

    df_env = pd.DataFrame(env_records)
    out_env_csv = PROJECT_ROOT / "data" / "beam_envelope_to_inflector.csv"
    df_env.to_csv(out_env_csv, index=False)

    # 1. Plot Envelope Trajectories (Buncher -> Neutralizer -> Solenoid -> Q1 -> Q2 -> Inflector)
    fig, ax = plt.subplots(figsize=(9, 5))
    for cname, (z_a, Rx_a, Ry_a, color) in envelope_data_dict.items():
        z_cm = z_a * 100.0
        ax.plot(z_cm, Rx_a * 1000.0, label=f"{cname} ($R_x$)", color=color, lw=2)
        ax.plot(z_cm, Ry_a * 1000.0, color=color, lw=1.5, ls="--")

    ax.axhline(acceptance.aperture_radius_m * 1000.0, color="black", ls=":", label="Inflector Aperture Limit (5 mm)")
    ax.axhline(-acceptance.aperture_radius_m * 1000.0, color="black", ls=":")

    ax.set_xlabel("Axial Distance $z$ [cm]")
    ax.set_ylabel("Beam Envelope Radius [mm]")
    ax.set_title("Beam Envelope Transport: Buncher Exit to Inflector Entrance")
    ax.legend(fontsize=9, loc="upper left")
    out1 = plots_dir / "envelope_buncher_to_inflector"
    save_figure(fig, out1)
    plt.close(fig)
    print(f"  Saved: {out1}.png / .pdf")

    # 2. Plot Inflector Phase Space (x, x') and (y, y') for baseline vs neutralized
    vac_summary = df_summary[df_summary["case_name"] == "vacuum_reference"].iloc[0]
    h2_summary = df_summary[df_summary["case_name"] == "seeded_H2_neutralized"].iloc[0]

    df_vac_xxp, df_vac_yyp = generate_phase_space_particles(
        vac_summary["Rx_end_mm"] / 1000.0, vac_summary["dRx_end_mrad"] / 1000.0,
        vac_summary["Ry_end_mm"] / 1000.0, vac_summary["dRy_end_mrad"] / 1000.0
    )
    df_h2_xxp, df_h2_yyp = generate_phase_space_particles(
        h2_summary["Rx_end_mm"] / 1000.0, h2_summary["dRx_end_mrad"] / 1000.0,
        h2_summary["Ry_end_mm"] / 1000.0, h2_summary["dRy_end_mrad"] / 1000.0
    )

    out_phase_csv = PROJECT_ROOT / "data" / "phase_space_at_inflector.csv"
    df_h2_xxp.to_csv(out_phase_csv, index=False)

    # Phase space (x, x')
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(df_vac_xxp["x_mm"], df_vac_xxp["xp_mrad"], alpha=0.4, label="Vacuum Reference", color="tab:blue", s=15)
    ax.scatter(df_h2_xxp["x_mm"], df_h2_xxp["xp_mrad"], alpha=0.5, label=r"$\mathrm{H}_2$-Neutralized ($90\%$)", color="tab:green", s=15)
    ax.set_xlabel("Transverse Position $x$ [mm]")
    ax.set_ylabel("Divergence $x'$ [mrad]")
    ax.set_title("Transverse Phase Space $(x, x')$ at Inflector Entrance")
    ax.legend()
    out2 = plots_dir / "inflector_phase_space_xxp"
    save_figure(fig, out2)
    plt.close(fig)
    print(f"  Saved: {out2}.png / .pdf")

    # Phase space (y, y')
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(df_vac_yyp["y_mm"], df_vac_yyp["yp_mrad"], alpha=0.4, label="Vacuum Reference", color="tab:blue", s=15)
    ax.scatter(df_h2_yyp["y_mm"], df_h2_yyp["yp_mrad"], alpha=0.5, label=r"$\mathrm{H}_2$-Neutralized ($90\%$)", color="tab:green", s=15)
    ax.set_xlabel("Transverse Position $y$ [mm]")
    ax.set_ylabel("Divergence $y'$ [mrad]")
    ax.set_title("Transverse Phase Space $(y, y')$ at Inflector Entrance")
    ax.legend()
    out3 = plots_dir / "inflector_phase_space_yyp"
    save_figure(fig, out3)
    plt.close(fig)
    print(f"  Saved: {out3}.png / .pdf")

    # 3. Transmission Comparison Bar Chart
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(
        df_summary["case_name"],
        df_summary["transmission_percent"],
        color=["tab:blue", "tab:green", "tab:purple"],
        width=0.5,
    )
    ax.set_ylabel("Inflector Entrance Transmission [%]")
    ax.set_ylim(0, 115)
    ax.set_title("Inflector Transmission Efficiency Comparison")

    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{height:.1f}%",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    out4 = plots_dir / "transmission_comparison"
    save_figure(fig, out4)
    plt.close(fig)
    print(f"  Saved: {out4}.png / .pdf")


if __name__ == "__main__":
    main()
