#!/usr/bin/env python3
"""
scripts/transmission_vs_downstream.py

Task CW2 of docs/physics_notes/simulation_strategy_tasks.md: transmission into the inflector of a
DC beam versus the compensation downstream of the plasma cell, with eta_cell from CW1.

For each downstream compensation eta_down (drift, main solenoid, Q1, Q2, last drift) and each beam
emittance, the solenoid and Q1/Q2 are matched (plasma_column.transport.match_optics) and the
geometric KV transmission estimate is reported (pipe 10 mm, inflector aperture 5 mm, divergence
50 mrad). The cell compensation is the CW1 beam-core eta_net (0.91, mean from 490 to 975 ns,
task 111). Output: T(eta_down) and the eta_down needed for T >= 0.5 and 0.9 (linear interpolation).

Matches at one emittance run in order of eta_down, each warm-started from the previous optimum.
Emittances run in parallel processes (--processes, default 2).

The line starts at the cell entrance (buncher exit); a drift between buncher and cell is not
modeled (task 111 shows such a drift, uncompensated, already enlarges the beam before the cell).

Outputs (default results/transmission_vs_downstream/, git-ignored):
    transmission_vs_downstream.csv / .json, transmission_vs_downstream.{png,pdf}

Usage:
    python scripts/transmission_vs_downstream.py --dry_run
    python scripts/transmission_vs_downstream.py
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

from plasma_column.injection_line import InjectionLine
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.transport import TransportBeam, match_optics, perveance_profile
from plasma_column.warpx_io import get_git_info

ETA_CELL_CW1 = 0.91  # task 111: beam-core eta_net, mean over 490-975 ns
EMITTANCES = (0.25e-6, 0.5e-6, 1.0e-6)
ETA_DOWN = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95)
TARGETS = (0.5, 0.9)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Transmission vs downstream compensation (task CW2).")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "transmission_vs_downstream")
    p.add_argument("--eta_cell", type=float, default=ETA_CELL_CW1)
    p.add_argument("--maxiter", type=int, default=40, help="Differential-evolution generations per match.")
    p.add_argument("--processes", type=int, default=2)
    p.add_argument("--dry_run", action="store_true", help="List the scan; write nothing.")
    return p.parse_args()


def scan_emittance(eps_n: float, eta_cell: float, maxiter: int) -> list[dict]:
    line = InjectionLine()
    beam = TransportBeam(emittance_n_edge_m_rad=eps_n)
    K0 = beam.proton.perveance_K0
    rows, found = [], []
    for eta_down in ETA_DOWN:
        K = perveance_profile(K0, line, eta_cell, eta_down)
        optics, t = match_optics(beam, line, K, maxiter=maxiter, starts=tuple(reversed(found[-3:])))
        found.append(optics)
        rows.append({"emittance_n_edge_pi_mm_mrad": eps_n * 1e6, "eta_cell": eta_cell, "eta_downstream": eta_down,
                     "solenoid_B_T": optics.solenoid_B_T, "q1_gradient_Tm": optics.q1_gradient_Tm,
                     "q2_gradient_Tm": optics.q2_gradient_Tm, **t})
        print(f"  eps_n {eps_n * 1e6:.2f}  eta_down {eta_down:.2f}  T = {t['T_total']:.3f}  "
              f"max R {t['max_R_mm']:.1f} mm", flush=True)
    return rows


def eta_needed(df: pd.DataFrame, target: float) -> float:
    """Smallest eta_down with T >= target (linear interpolation; NaN if never reached)."""
    d = df.sort_values("eta_downstream")
    T, e = d.T_total.to_numpy(), d.eta_downstream.to_numpy()
    if T[0] >= target:
        return float(e[0])
    for k in range(1, len(T)):
        if T[k] >= target:
            return float(e[k - 1] + (target - T[k - 1]) * (e[k] - e[k - 1]) / (T[k] - T[k - 1]))
    return float("nan")


def main() -> int:
    args = parse_args()
    print(f"CW2: eta_cell = {args.eta_cell}, eta_down = {ETA_DOWN}, "
          f"emittances {[e * 1e6 for e in EMITTANCES]} pi mm mrad, {len(ETA_DOWN) * len(EMITTANCES)} matches")
    if args.dry_run:
        print("[DRY RUN SUCCESS] nothing written.")
        return 0
    with ProcessPoolExecutor(max_workers=args.processes) as pool:
        parts = list(pool.map(scan_emittance, EMITTANCES, [args.eta_cell] * len(EMITTANCES),
                              [args.maxiter] * len(EMITTANCES)))
    df = pd.DataFrame([r for part in parts for r in part])
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "transmission_vs_downstream.csv", index=False, float_format="%.6g")
    needed = {f"{e:.2f}": {f"T>={t}": eta_needed(g, t) for t in TARGETS}
              for e, g in df.groupby("emittance_n_edge_pi_mm_mrad")}
    print("eta_down needed:", json.dumps(needed))
    (out / "transmission_vs_downstream.json").write_text(json.dumps({
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "model": "KV envelope, matched solenoid + Q1/Q2 per point, geometric transmission estimate, DC beam",
        "eta_cell_source": "CW1 (task 111) beam-core eta_net, 0.15 T / 300 V plugs, mean 490-975 ns",
        "apertures": "pipe 10 mm, inflector 5 mm, divergence 50 mrad",
        "eta_downstream_needed": needed,
        "rows": df.to_dict(orient="records"),
    }, indent=2, default=float))

    setup_publication_style()
    fig, ax = plt.subplots(figsize=(6, 4))
    for e, g in df.groupby("emittance_n_edge_pi_mm_mrad"):
        ax.plot(g.eta_downstream, g.T_total, marker="o", label=rf"$\varepsilon_n$ = {e:.2f} $\pi$ mm mrad")
    for t in TARGETS:
        ax.axhline(t, color="0.6", lw=0.8, ls=":")
    ax.set_xlabel(r"downstream compensation $\eta_{\rm down}$")
    ax.set_ylabel("transmission estimate T")
    ax.set_ylim(0, 1.05)
    ax.set_title(rf"DC beam, $\eta_{{\rm cell}}$ = {args.eta_cell:.2f} (CW1), matched optics", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    save_figure(fig, out / "transmission_vs_downstream")
    plt.close(fig)
    print(f"Wrote {out}/transmission_vs_downstream.csv and figure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
