#!/usr/bin/env python3
"""
scripts/sliced_bunch_transport.py

Tasks B5 and B6 of docs/physics_notes/simulation_strategy_tasks.md: RF-averaged transmission of
the accepted bunch into the inflector, resolved in longitudinal slices.

The best 36-deg phase window at the inflector (the cyclotron acceptance) is split into 9 slices of
4 deg (plasma_column.bunching.slice_bunching_along_line). Each slice is followed back along the
line; its local current factor B_s(z) sets its own perveance, and its KV envelope is transported
through one common set of optics (solenoid, Q1, Q2) matched for the largest accepted current
    T_acc = sum_s f_s T_s       (f_s: beam fraction in slice s),
compared with an unbunched beam of the same compensation, whose window holds 36/360 of the beam:
    G = T_acc / (0.1 T_DC),     T_DC from task CW2.
Compensation: K_s = K0 (B_s - eta) (electrons follow only the RF-averaged charge; default, task 106)
and K_s = K0 B_s (1 - eta) (per-slice upper bound). eta_cell = 0.91 (CW1).

Buncher positions: baseline (upstream of the neutralizer, at the cell entrance of the model line),
and, as an ALTERNATIVE-PLACEMENT STUDY, between Q1 and Q2 and 7.5 cm before the inflector (task B3;
the last one is outside the ballistic model). Buncher voltage: best window B_f at the inflector.
Waveform: sine (B5) or ideal sawtooth (B6, --waveform sawtooth).

Limitations: ballistic bunching (no longitudinal space charge), slices transported independently
(the bunch length at the focus, ~5 mm for 36 deg, is comparable to the pipe radius, so the
transverse field of a slice is overestimated there: conservative), KV slice envelopes, geometric
transmission estimate.

Outputs (default results/sliced_bunch_transport/, git-ignored):
    sliced_bunch_<waveform>.csv / .json, sliced_bunch_<waveform>.{png,pdf}

Usage:
    python scripts/sliced_bunch_transport.py --dry_run
    python scripts/sliced_bunch_transport.py --waveform sine
    python scripts/sliced_bunch_transport.py --waveform sawtooth
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
from scipy.optimize import differential_evolution

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.bunching import BuncherModel, optimal_voltage_V, slice_bunching_along_line
from plasma_column.injection_line import InjectionLine
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.transport import Optics, TransportBeam, envelope, transmission
from plasma_column.warpx_io import get_git_info

ETA_CELL_CW1 = 0.91
ETA_DOWN = (0.0, 0.5, 0.9)
EMITTANCES = (0.25e-6, 0.5e-6)
MODES = ("average", "per_slice")
POSITIONS = {"baseline_cell_entrance": 0.0, "drift3_Q1_Q2": 0.81, "drift4_Q2_inflector": 1.045}
ACCEPTANCE_DEG = 36.0
N_SLICES = 9
BOUNDS = ((0.0, 0.6), (-1.5, 1.5), (-1.5, 1.5))
CW2_CSV = PROJECT_ROOT / "results" / "transmission_vs_downstream" / "transmission_vs_downstream.csv"
B3_CSV = PROJECT_ROOT / "results" / "late_bunching_layout" / "late_bunching_layout.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sliced-bunch transport into the inflector acceptance (B5/B6).")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "sliced_bunch_transport")
    p.add_argument("--waveform", default="sine", choices=("sine", "sawtooth"))
    p.add_argument("--eta_cell", type=float, default=ETA_CELL_CW1)
    p.add_argument("--v_max", type=float, default=20000.0)
    p.add_argument("--maxiter", type=int, default=30)
    p.add_argument("--popsize", type=int, default=15)
    p.add_argument("--processes", type=int, default=2)
    p.add_argument("--dry_run", action="store_true", help="List the cases; write nothing.")
    return p.parse_args()


def slice_perveance(K0: float, line: InjectionLine, z_grid: np.ndarray, factor: np.ndarray,
                    eta_cell: float, eta_down: float, mode: str):
    L = line.plasma_cell_length

    def K(z: np.ndarray) -> np.ndarray:
        z = np.asarray(z, float)
        eta = np.where(z <= L, eta_cell, eta_down)
        b = np.interp(z, z_grid, factor)
        if mode == "average":
            return K0 * np.clip(b - eta, 0.0, None)
        return K0 * b * np.clip(1.0 - eta, 0.0, None)

    return K


def accepted(beam: TransportBeam, line: InjectionLine, optics: Optics, Ks: list, frac: np.ndarray,
             dz_m: float = 1.0e-3) -> tuple[float, list[dict]]:
    ts = [transmission(envelope(beam, line, optics, K, dz_m=dz_m), beam) for K in Ks]
    return float(sum(f * t["T_total"] for f, t in zip(frac, ts))), ts


def match(beam: TransportBeam, line: InjectionLine, Ks: list, frac: np.ndarray, starts: list[Optics],
          maxiter: int, popsize: int) -> Optics:
    norm = frac.sum()

    def cost(x: np.ndarray) -> float:
        return -accepted(beam, line, Optics(*x), Ks, frac, dz_m=2.0e-3)[0] / norm

    x0 = None
    if starts:
        lo, hi = [b[0] for b in BOUNDS], [b[1] for b in BOUNDS]
        x0 = np.clip([starts[0].solenoid_B_T, starts[0].q1_gradient_Tm, starts[0].q2_gradient_Tm], lo, hi)
    res = differential_evolution(cost, BOUNDS, seed=1, maxiter=maxiter, popsize=popsize, tol=1e-6, polish=True, x0=x0)
    cands = [(res.fun, Optics(*res.x))] + [(cost(np.array([o.solenoid_B_T, o.q1_gradient_Tm, o.q2_gradient_Tm])), o)
                                           for o in starts]
    return min(cands, key=lambda c: c[0])[1]


def run_position(task: tuple) -> list[dict]:
    name, z_b, waveform, v_max, eta_cell, maxiter, popsize, b3_optics = task
    line = InjectionLine()
    L = line.total_length
    volt = optimal_voltage_V(L - z_b, BuncherModel(waveform=waveform), ACCEPTANCE_DEG, v_max=v_max)
    b = BuncherModel(voltage_V=volt, waveform=waveform)
    z_grid = np.linspace(0.0, L, 225)
    sl = slice_bunching_along_line(z_grid, z_b, b, L, ACCEPTANCE_DEG, N_SLICES)
    frac = sl["slice_fraction"]
    rows = []
    for eps_n in EMITTANCES:
        beam = TransportBeam(emittance_n_edge_m_rad=eps_n)
        K0 = beam.proton.perveance_K0
        for mode in MODES:
            found: list[Optics] = []
            for eta_down in ETA_DOWN:
                Ks = [slice_perveance(K0, line, z_grid, f, eta_cell, eta_down, mode) for f in sl["slice_factor"]]
                starts = list(found) + [o for o in [b3_optics.get((round(eps_n * 1e6, 3), eta_down))] if o]
                optics = match(beam, line, Ks, frac, starts, maxiter, popsize)
                found.insert(0, optics)
                t_acc, ts = accepted(beam, line, optics, Ks, frac)
                rows.append({"position": name, "buncher_z_m": z_b, "waveform": waveform, "buncher_voltage_V": volt,
                             "bf_window_inflector": sl["bf_window"], "max_slice_factor": float(sl["slice_factor"].max()),
                             "z_max_slice_factor_m": float(z_grid[np.argmax(sl["slice_factor"].max(axis=0))]),
                             "emittance_n_edge_pi_mm_mrad": eps_n * 1e6, "compensation": mode, "eta_cell": eta_cell,
                             "eta_downstream": eta_down, "solenoid_B_T": optics.solenoid_B_T,
                             "q1_gradient_Tm": optics.q1_gradient_Tm, "q2_gradient_Tm": optics.q2_gradient_Tm,
                             "window_fraction": float(frac.sum()), "T_accepted": t_acc,
                             "T_window_mean": t_acc / frac.sum(),
                             "T_slice_min": min(t["T_total"] for t in ts), "T_slice_max": max(t["T_total"] for t in ts),
                             "slice_T": [t["T_total"] for t in ts], "slice_fraction": frac.tolist(),
                             "slice_centre_deg": sl["slice_centre_deg"].tolist()})
                print(f"  {waveform} {name:22s} V {volt:7.0f}  eps {eps_n * 1e6:.2f}  {mode:9s} eta_down {eta_down:.1f}  "
                      f"T_acc = {t_acc:.4f} (window {frac.sum():.3f})", flush=True)
    return rows


def b3_starts() -> dict:
    if not B3_CSV.exists():
        return {}
    d = pd.read_csv(B3_CSV)
    return {(r.position, round(r.emittance_n_edge_pi_mm_mrad, 3), round(r.eta_downstream, 3)):
            Optics(r.solenoid_B_T, r.q1_gradient_Tm, r.q2_gradient_Tm) for r in d.itertuples()}


def main() -> int:
    args = parse_args()
    label = "" if args.waveform == "sine" else " (B6)"
    print(f"B5{label}: {args.waveform} buncher at {list(POSITIONS)}; {N_SLICES} slices of {ACCEPTANCE_DEG / N_SLICES:g} deg; "
          f"eps {[e * 1e6 for e in EMITTANCES]}; modes {MODES}; eta_down {ETA_DOWN}; eta_cell {args.eta_cell}")
    print("  positions other than the baseline are an ALTERNATIVE-PLACEMENT STUDY")
    if args.dry_run:
        print("[DRY RUN SUCCESS] nothing written.")
        return 0
    if not CW2_CSV.exists():
        raise SystemExit(f"needs the DC reference of task CW2: {CW2_CSV}")
    b3 = b3_starts()
    tasks = [(k, v, args.waveform, args.v_max, args.eta_cell, args.maxiter, args.popsize,
              {(e, d): o for (p, e, d), o in b3.items() if p == k}) for k, v in POSITIONS.items()]
    with ProcessPoolExecutor(max_workers=args.processes) as pool:
        df = pd.DataFrame([r for part in pool.map(run_position, tasks) for r in part])
    dc = pd.read_csv(CW2_CSV)
    dc = dc[np.isclose(dc.eta_cell, args.eta_cell)]
    dc_T = {(round(r.emittance_n_edge_pi_mm_mrad, 3), round(r.eta_downstream, 3)): r.T_total for r in dc.itertuples()}
    df["T_dc"] = [dc_T.get((round(e, 3), round(d, 3)), np.nan)
                  for e, d in zip(df.emittance_n_edge_pi_mm_mrad, df.eta_downstream)]
    df["accepted_gain_vs_dc"] = df.T_accepted / (ACCEPTANCE_DEG / 360.0 * df.T_dc)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    stem = f"sliced_bunch_{args.waveform}"
    df.drop(columns=["slice_T", "slice_fraction", "slice_centre_deg"]).to_csv(out / f"{stem}.csv", index=False,
                                                                                float_format="%.6g")
    (out / f"{stem}.json").write_text(json.dumps({
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "label": "buncher positions other than baseline_cell_entrance: ALTERNATIVE-PLACEMENT STUDY",
        "model": f"ballistic {args.waveform} buncher; {N_SLICES} slices of the best {ACCEPTANCE_DEG:g}-deg window at the "
                 "inflector, KV slice envelopes with local perveance, common matched solenoid + Q1/Q2",
        "figure_of_merit": "G = sum_s f_s T_s / (0.1 T_DC), T_DC from task CW2",
        "rows": df.to_dict(orient="records"),
    }, indent=2, default=float))
    with pd.option_context("display.width", 220):
        print(df[["position", "buncher_voltage_V", "bf_window_inflector", "max_slice_factor",
                  "emittance_n_edge_pi_mm_mrad", "compensation", "eta_downstream", "T_window_mean",
                  "T_accepted", "T_dc", "accepted_gain_vs_dc"]].round(3).to_string(index=False))

    setup_publication_style()
    fig, axes = plt.subplots(1, len(EMITTANCES), figsize=(11, 4), sharey=True)
    for ax, e in zip(axes, EMITTANCES):
        g = df[np.isclose(df.emittance_n_edge_pi_mm_mrad, e * 1e6)]
        for (pos, mode), gg in g.groupby(["position", "compensation"]):
            ax.plot(gg.eta_downstream, gg.accepted_gain_vs_dc, marker="o", ls="-" if mode == "average" else "--",
                    label=f"{pos} ({mode})")
        ax.axhline(1.0, color="0.5", lw=0.8, ls=":")
        ax.set_yscale("log"); ax.set_xlabel(r"$\eta_{\rm down}$")
        ax.set_title(rf"$\varepsilon_n$ = {e * 1e6:.2f} $\pi$ mm mrad", fontsize=10); ax.grid(alpha=0.3)
    axes[0].set_ylabel(r"accepted-current gain $\sum f_s T_s / (0.1\,T_{\rm DC})$")
    axes[0].legend(fontsize=6)
    fig.suptitle(f"Sliced-bunch transport, {args.waveform} buncher; non-baseline positions: ALTERNATIVE-PLACEMENT "
                 rf"STUDY; $\eta_{{\rm cell}}$ = {args.eta_cell:.2f}; dashed: per-slice upper bound", fontsize=8)
    save_figure(fig, out / stem)
    plt.close(fig)
    print(f"Wrote {out}/{stem}.csv and figure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
