#!/usr/bin/env python3
"""
scripts/analyze_bunching_along_line.py

Local bunching factor B_f(z) from the buncher exit through the plasma neutralizer to the
spiral-inflector entrance (plasma_column.bunching, ballistic drift, no space charge). The buncher
voltage is chosen so that bunching inside the cyclotron phase acceptance is maximal at the
inflector entrance, which is how a buncher is normally set up.

For each z it reports B_f inside the acceptance window and the 2-deg peak current ratio. It also
gives the static-background peak-bunch estimate K_eff,peak/K0,peak ~ 1 - eta_avg / B_f(z) inside
the cell, with eta_avg = the PIC beam-core eta_net of seeded H2 at 1e-5 Torr (DC-beam result
applied to the local bunching; illustrative, not a bunched-beam simulation).

Outputs (default results/bunching_along_line/, git-ignored):
    bunching_along_line.csv
    bunching_summary.json
    bunching_along_line.{png,pdf}

Usage:
    python scripts/analyze_bunching_along_line.py --dry_run
    python scripts/analyze_bunching_along_line.py
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.bunching import BuncherModel, bunching_along_line, optimal_voltage_V
from plasma_column.injection_line import InjectionLine
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.warpx_io import get_git_info

PIC_CASES = PROJECT_ROOT / "paper" / "manuscript" / "pic_data" / "production_cases.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bunching factor along the axial injection line.")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "bunching_along_line")
    p.add_argument("--energy_keV", type=float, default=30.0)
    p.add_argument("--rf_frequency_hz", type=float, default=50.0e6)
    p.add_argument("--acceptance_deg", type=float, default=36.0, help="Cyclotron phase acceptance.")
    p.add_argument("--energy_spread_eV", type=float, default=5.0, help="Source energy spread (rms).")
    p.add_argument("--n_particles", type=int, default=200_000)
    p.add_argument("--dz_m", type=float, default=0.005)
    p.add_argument("--dry_run", action="store_true", help="Compute and print the summary; write nothing.")
    return p.parse_args()


def element_spans(line: InjectionLine) -> list[tuple[str, float, float]]:
    spans, z = [], 0.0
    for name, length in (("plasma cell", line.plasma_cell_length), ("drift", line.drift1_length),
                         ("solenoid", line.solenoid_length), ("drift", line.drift2_length),
                         ("Q1", line.q1_length), ("drift", line.drift3_length), ("Q2", line.q2_length),
                         ("drift", line.drift4_length)):
        spans.append((name, z, z + length))
        z += length
    return spans


def main() -> None:
    args = parse_args()
    line = InjectionLine()
    z_inf = line.total_length
    cell = (0.0, line.plasma_cell_length)
    z = np.round(np.arange(0.0, z_inf + 0.5 * args.dz_m, args.dz_m), 6)

    eta_avg = float("nan")
    if PIC_CASES.exists():
        pic = pd.read_csv(PIC_CASES).set_index("case_name")
        eta_avg = float(pic.loc["seeded_H2_1e-5Torr", "eta_net_local"])

    profiles = {}
    voltages = {}
    for waveform in ("sine", "sawtooth"):
        base = BuncherModel(args.energy_keV, args.rf_frequency_hz, 1.0, waveform, args.energy_spread_eV)
        volt = optimal_voltage_V(z_inf, base, args.acceptance_deg)
        voltages[waveform] = volt
        b = BuncherModel(args.energy_keV, args.rf_frequency_hz, volt, waveform, args.energy_spread_eV)
        profiles[waveform] = bunching_along_line(z, b, args.acceptance_deg, args.n_particles)

    rows = {"z_m": z}
    for wf, prof in profiles.items():
        rows[f"bunching_factor_{wf}"] = prof["bunching_factor"]
        rows[f"peak_current_ratio_2deg_{wf}"] = prof["peak_current_ratio_2deg"]
        rows[f"keff_peak_over_k0_static_{wf}"] = 1.0 - eta_avg / prof["bunching_factor"]
    df = pd.DataFrame(rows)
    in_cell = (df.z_m >= cell[0]) & (df.z_m <= cell[1])

    summary = {
        "model": "ballistic drift, no space charge, thin buncher gap at z = 0 (buncher exit)",
        "acceptance_deg": args.acceptance_deg,
        "energy_spread_rms_eV": args.energy_spread_eV,
        "inflector_entrance_z_m": z_inf,
        "plasma_cell_z_m": list(cell),
        "eta_avg_used": eta_avg,
        "eta_avg_source": "PIC beam-core eta_net, seeded_H2_1e-5Torr (DC beam, task 102)",
        "waveforms": {},
    }
    for wf in profiles:
        bf = df[f"bunching_factor_{wf}"]
        summary["waveforms"][wf] = {
            "buncher_voltage_V": voltages[wf],
            "bunching_factor_cell_entrance": float(bf[in_cell].iloc[0]),
            "bunching_factor_cell_exit": float(bf[in_cell].iloc[-1]),
            "bunching_factor_cell_mean": float(bf[in_cell].mean()),
            "bunching_factor_inflector": float(bf.iloc[-1]),
            "bunching_factor_max": float(bf.max()),
            "z_of_max_m": float(df.z_m[bf.idxmax()]),
            "keff_peak_over_k0_static_cell_exit": float(1.0 - eta_avg / bf[in_cell].iloc[-1]),
            "keff_peak_over_k0_static_if_B_f_inflector": float(1.0 - eta_avg / bf.iloc[-1]),
        }

    print("Bunching along the injection line (ballistic, no space charge)")
    for wf, s in summary["waveforms"].items():
        print(f"  {wf:8s} V = {s['buncher_voltage_V']:.0f} V: B_f cell {s['bunching_factor_cell_entrance']:.2f}"
              f"-{s['bunching_factor_cell_exit']:.2f} (mean {s['bunching_factor_cell_mean']:.2f}), "
              f"inflector {s['bunching_factor_inflector']:.2f}")
    if args.dry_run:
        print("[DRY RUN SUCCESS] nothing written.")
        return

    setup_publication_style()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    shade = {"plasma cell": "tab:green", "solenoid": "tab:orange", "Q1": "tab:red", "Q2": "tab:purple"}
    for name, z0, z1 in element_spans(line):
        if name in shade:
            ax.axvspan(z0 * 100, z1 * 100, color=shade[name], alpha=0.12)
            ax.text(0.5 * (z0 + z1) * 100, 0.97, name, transform=ax.get_xaxis_transform(),
                    ha="center", va="top", fontsize=8)
    for wf, color in (("sine", "tab:blue"), ("sawtooth", "0.4")):
        ax.plot(df.z_m * 100, df[f"bunching_factor_{wf}"], color=color, lw=2,
                label=f"{wf} buncher, V = {voltages[wf]:.0f} V")
    ax.axhline(360.0 / args.acceptance_deg, color="k", ls=":", lw=0.8)
    ax.set_xlabel("z from buncher exit [cm] (inflector entrance at right edge)")
    ax.set_ylabel(rf"$B_f(z)$ in {args.acceptance_deg:.0f}$^\circ$ acceptance")
    ax.set_xlim(0, z_inf * 100)
    ax.set_ylim(0, 360.0 / args.acceptance_deg * 1.15)
    ax.set_title("Local bunching factor (ballistic, no space charge)", fontsize=11)
    ax.legend(loc="center left", fontsize=9)
    fig.tight_layout()

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "bunching_along_line.csv", index=False, float_format="%.6g")
    summary["provenance"] = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
    }
    (out / "bunching_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    save_figure(fig, out / "bunching_along_line")
    plt.close(fig)
    print(f"Wrote {out}/bunching_along_line.csv, bunching_summary.json and figure.")


if __name__ == "__main__":
    main()
