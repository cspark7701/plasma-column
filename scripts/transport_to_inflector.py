#!/usr/bin/env python3
"""
scripts/transport_to_inflector.py

Simulates space-charge beam envelope transport through the downstream axial injection line:
buncher exit -> plasma neutralizer -> solenoid -> quadrupole Q1 -> quadrupole Q2 -> spiral inflector

Evaluates envelope trajectories R(z), transmission efficiency at inflector entrance, and phase-space distributions.

Generated CSV Files:
- data/inflector_entrance_summary.csv
- data/beam_envelope_to_inflector.csv
- data/phase_space_at_inflector.csv
- data/transmission_vs_case.csv

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
from pathlib import Path
import pandas as pd

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.beam import ProtonBeam
from plasma_column.injection_line import InjectionLine, compute_beam_envelope
from plasma_column.acceptance import (
    InflectorAcceptance,
    compute_inflector_transmission,
    generate_phase_space_particles,
)
from plasma_column.plotting import (
    plot_multi_case_beam_envelopes,
    plot_inflector_phase_space_comparison,
    plot_transmission_comparison_bar,
    setup_publication_style,
)


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
    p1, p2 = plot_multi_case_beam_envelopes(
        envelope_data_dict,
        plots_dir,
        aperture_radius_mm=acceptance.aperture_radius_m * 1000.0,
        output_name="envelope_buncher_to_inflector",
    )
    print(f"  Saved: {p1} / {p2}")

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

    p1, p2 = plot_inflector_phase_space_comparison(
        df_vac_xxp, df_h2_xxp, plots_dir, plane="x", output_name="inflector_phase_space_xxp"
    )
    print(f"  Saved: {p1} / {p2}")

    p1, p2 = plot_inflector_phase_space_comparison(
        df_vac_yyp, df_h2_yyp, plots_dir, plane="y", output_name="inflector_phase_space_yyp"
    )
    print(f"  Saved: {p1} / {p2}")

    # 3. Transmission Comparison Bar Chart
    p1, p2 = plot_transmission_comparison_bar(
        df_summary, plots_dir, output_name="transmission_comparison"
    )
    print(f"  Saved: {p1} / {p2}")


if __name__ == "__main__":
    main()
