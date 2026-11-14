#!/usr/bin/env python3
"""
scripts/late_bunching_layout.py

Task B3 of docs/physics_notes/simulation_strategy_tasks.md (ALTERNATIVE-PLACEMENT STUDY): move the
sine buncher from its baseline position (upstream of the neutralizer, i.e. at the cell entrance of
the model line) into the drifts downstream, so that the bunch forms late and the peak space
charge acts over a shorter distance. Baseline layout: buncher -> neutralizer -> solenoid -> Q1 ->
Q2 -> inflector; every other buncher position here is an alternative placement.

For each buncher position z_b (middle of a drift) the gap voltage is set for the best 36-deg window
bunching factor at the inflector (plasma_column.bunching.optimal_voltage_V, focus at the inflector,
ballistic, capped at --v_max), B_f(z) = 1 upstream of the buncher, and the peak-slice envelope is
matched with RF-averaged compensation K = K0 (B_f - eta) (task 106), eta_cell = 0.91 (CW1) and
eta_down in {0, 0.5, 0.9}.

Figure of merit: accepted current relative to an unbunched beam with the same compensation,
    G = B_f(inflector) * T_peak / T_DC,
with T_DC from task CW2 (results/transmission_vs_downstream/). T of the peak slice is a lower bound
for the window (the window also holds weaker slices; task B5 resolves the slices).

Outputs (default results/late_bunching_layout/, git-ignored):
    late_bunching_layout.csv / .json, late_bunching_layout.{png,pdf}

Usage:
    python scripts/late_bunching_layout.py --dry_run
    python scripts/late_bunching_layout.py
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
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

from plasma_column.bunching import BuncherModel, bunching_with_buncher_at, optimal_voltage_V
from plasma_column.injection_line import InjectionLine
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.transport import TransportBeam, match_optics, perveance_profile
from plasma_column.warpx_io import get_git_info

ETA_CELL_CW1 = 0.91
ETA_DOWN = (0.0, 0.5, 0.9)
EMITTANCES = (0.25e-6, 0.5e-6)
CW2_CSV = PROJECT_ROOT / "results" / "transmission_vs_downstream" / "transmission_vs_downstream.csv"


def buncher_positions(line: InjectionLine) -> dict[str, float]:
    """Baseline (cell entrance) and the middle of each downstream drift [m from the cell entrance]."""
    z_d1 = line.plasma_cell_length
    z_d2 = z_d1 + line.drift1_length + line.solenoid_length
    z_d3 = z_d2 + line.drift2_length + line.q1_length
    z_d4 = z_d3 + line.drift3_length + line.q2_length
    return {"baseline_cell_entrance": 0.0,
            "drift1_after_cell": z_d1 + 0.5 * line.drift1_length,
            "drift2_solenoid_Q1": z_d2 + 0.5 * line.drift2_length,
            "drift3_Q1_Q2": z_d3 + 0.5 * line.drift3_length,
            "drift4_Q2_inflector": z_d4 + 0.5 * line.drift4_length}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Late-bunching layout (task B3, alternative-placement study).")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "late_bunching_layout")
    p.add_argument("--eta_cell", type=float, default=ETA_CELL_CW1)
    p.add_argument("--v_max", type=float, default=20000.0, help="Upper bound of the buncher voltage search [V].")
    p.add_argument("--waveform", default="sine", choices=("sine", "sawtooth"))
    p.add_argument("--maxiter", type=int, default=40)
    p.add_argument("--processes", type=int, default=2)
    p.add_argument("--dry_run", action="store_true", help="List positions; write nothing.")
    return p.parse_args()


def run_position(task: tuple) -> list[dict]:
    name, z_b, waveform, v_max, eta_cell, maxiter = task
    line = InjectionLine()
    L = line.total_length
    b0 = BuncherModel(waveform=waveform)
    volt = optimal_voltage_V(L - z_b, b0, v_max=v_max)
    b = BuncherModel(voltage_V=volt, waveform=waveform)
    zb = np.linspace(0.0, L, 225)
    bf = bunching_with_buncher_at(zb, z_b, b)
    rows = []
    for eps_n in EMITTANCES:
        beam = TransportBeam(emittance_n_edge_m_rad=eps_n)
        found = []
        for eta_down in ETA_DOWN:
            K = perveance_profile(beam.proton.perveance_K0, line, eta_cell, eta_down, zb, bf, compensation="average")
            optics, t = match_optics(beam, line, K, maxiter=maxiter, starts=tuple(found))
            found.append(optics)
            rows.append({"position": name, "buncher_z_m": z_b, "drift_to_inflector_m": L - z_b,
                         "waveform": waveform, "buncher_voltage_V": volt, "bf_inflector": float(bf[-1]),
                         "bf_cell_exit": float(np.interp(line.plasma_cell_length, zb, bf)),
                         "emittance_n_edge_pi_mm_mrad": eps_n * 1e6, "eta_cell": eta_cell, "eta_downstream": eta_down,
                         "solenoid_B_T": optics.solenoid_B_T, "q1_gradient_Tm": optics.q1_gradient_Tm,
                         "q2_gradient_Tm": optics.q2_gradient_Tm, **t})
            print(f"  {name:22s} V {volt:7.0f}  B_f {bf[-1]:.2f}  eps {eps_n * 1e6:.2f}  eta_down {eta_down:.1f}  "
                  f"T_peak = {t['T_total']:.3f}", flush=True)
    return rows


def main() -> int:
    args = parse_args()
    line = InjectionLine()
    pos = buncher_positions(line)
    print(f"B3 (alternative-placement study): {len(pos)} buncher positions x {len(EMITTANCES)} emittances "
          f"x eta_down {ETA_DOWN}; eta_cell = {args.eta_cell}")
    for k, v in pos.items():
        print(f"  {k}: z_b = {v:.3f} m, drift to inflector {line.total_length - v:.3f} m")
    if args.dry_run:
        print("[DRY RUN SUCCESS] nothing written.")
        return 0
    if not CW2_CSV.exists():
        raise SystemExit(f"needs the DC reference of task CW2: {CW2_CSV}")
    tasks = [(k, v, args.waveform, args.v_max, args.eta_cell, args.maxiter) for k, v in pos.items()]
    with ProcessPoolExecutor(max_workers=args.processes) as pool:
        df = pd.DataFrame([r for part in pool.map(run_position, tasks) for r in part])
    dc = pd.read_csv(CW2_CSV)
    dc = dc[np.isclose(dc.eta_cell, args.eta_cell)]
    dc_T = {(round(r.emittance_n_edge_pi_mm_mrad, 3), round(r.eta_downstream, 3)): r.T_total for r in dc.itertuples()}
    df["T_dc"] = [dc_T.get((round(e, 3), round(d, 3)), np.nan)
                  for e, d in zip(df.emittance_n_edge_pi_mm_mrad, df.eta_downstream)]
    df["accepted_gain_vs_dc"] = df.bf_inflector * df.T_total / df.T_dc
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "late_bunching_layout.csv", index=False, float_format="%.6g")
    (out / "late_bunching_layout.json").write_text(json.dumps({
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "label": "ALTERNATIVE-PLACEMENT STUDY (buncher moved downstream of the neutralizer)",
        "model": "ballistic sine buncher, B_f(z) window 36 deg; KV envelope of the peak slice, "
                 "K = K0 (B_f - eta) (RF-averaged compensation), matched solenoid + Q1/Q2",
        "figure_of_merit": "B_f(inflector) * T_peak / T_DC (T_DC from task CW2)",
        "rows": df.to_dict(orient="records"),
    }, indent=2, default=float))
    with pd.option_context("display.width", 200):
        print(df[["position", "buncher_voltage_V", "bf_inflector", "emittance_n_edge_pi_mm_mrad", "eta_downstream",
                  "T_total", "T_dc", "accepted_gain_vs_dc"]].round(3).to_string(index=False))

    setup_publication_style()
    fig, axes = plt.subplots(1, len(EMITTANCES), figsize=(11, 4), sharey=True)
    for ax, e in zip(axes, EMITTANCES):
        g = df[np.isclose(df.emittance_n_edge_pi_mm_mrad, e * 1e6)]
        for d, gg in g.groupby("eta_downstream"):
            ax.plot(gg.drift_to_inflector_m, gg.accepted_gain_vs_dc, marker="o", label=rf"$\eta_{{\rm down}}$ = {d:.1f}")
        ax.axhline(1.0, color="0.5", lw=0.8, ls=":")
        ax.set_xlabel("buncher-to-inflector drift [m]")
        ax.set_title(rf"$\varepsilon_n$ = {e * 1e6:.2f} $\pi$ mm mrad", fontsize=10)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel(r"accepted-current gain $B_f\,T_{\rm peak}/T_{\rm DC}$")
    axes[0].legend(fontsize=8)
    fig.suptitle("Late bunching: ALTERNATIVE-PLACEMENT STUDY (baseline buncher at 1.12 m drift); "
                 rf"$\eta_{{\rm cell}}$ = {args.eta_cell:.2f}", fontsize=9)
    save_figure(fig, out / "late_bunching_layout")
    plt.close(fig)
    print(f"Wrote {out}/late_bunching_layout.csv and figure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
