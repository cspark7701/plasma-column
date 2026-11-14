#!/usr/bin/env python3
"""
scripts/trap_orbit_tracking.py

Task C2 of docs/physics_notes/simulation_strategy_tasks.md: guiding-centre test electrons in the
static cell fields for 100 us (plasma_column.electron_trap), to see whether the solenoid + end-plug
trap holds electrons for tau_ion ~ 80 us, beyond the ~1 us of the PIC runs (tasks 107, 109, 111).

Scan: cell B_z = 0.05, 0.15 T; plugs off, -100 V, -300 V (w = 10 mm, centres 30 mm outside the
cell ends, as in CW1); net beam-well compensation eta = 0.5, 0.9; electrons born in the beam with
T = 1 eV (seed of the PIC runs) or 10 eV (closer to proton-impact secondaries). Elastic e-H2
collisions at 1e-5 Torr and Coulomb heating by the 10 mA beam. One case is repeated at dt / 2.5 as
a time-step check.

This is a classical, quiescent-trap upper bound: no collective fields, fluctuations, ion dynamics
or e-e collisions (see the module docstring). tau_c from PIC includes those.

Outputs (default results/trap_orbit_tracking/, git-ignored):
    trap_summary.csv / .json, trap_time_series.csv, trap_survival.{png,pdf}

Usage:
    python scripts/trap_orbit_tracking.py --dry_run
    python scripts/trap_orbit_tracking.py --processes 2
"""

from __future__ import annotations

import argparse
import datetime
import itertools
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
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

from plasma_column.electron_trap import TrapConfig, confinement_time_s, track
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.warpx_io import get_git_info

TAU_ION_S = 80e-6
B_FIELDS = (0.05, 0.15)
PLUGS_V = (0.0, 100.0, 300.0)
ETAS = (0.5, 0.9)
TEMPS_EV = (1.0, 10.0)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Test-electron confinement in the static trap (task C2).")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "trap_orbit_tracking")
    p.add_argument("--t_end_us", type=float, default=100.0)
    p.add_argument("--dt_s", type=float, default=5e-10)
    p.add_argument("--n_electrons", type=int, default=2000)
    p.add_argument("--processes", type=int, default=2)
    p.add_argument("--dry_run", action="store_true", help="List the cases; write nothing.")
    return p.parse_args()


def cases(dt_s: float) -> list[dict]:
    out = [{"name": f"B{b:g}_V{v:g}_eta{e:g}_T{t:g}", "B": b, "V": v, "eta": e, "T": t, "dt": dt_s}
           for b, v, e, t in itertools.product(B_FIELDS, PLUGS_V, ETAS, TEMPS_EV)]
    out.append({"name": "B0.15_V300_eta0.9_T10_dtcheck", "B": 0.15, "V": 300.0, "eta": 0.9, "T": 10.0, "dt": dt_s / 2.5})
    return out


def run(task: tuple) -> tuple[dict, pd.DataFrame]:
    c, t_end_s, n_e = task
    cfg = TrapConfig(solenoid_Bz_T=c["B"], plug_voltage_V=c["V"], eta=c["eta"])
    r = track(cfg, n_electrons=n_e, t_end_s=t_end_s, dt_s=c["dt"], temperature_eV=c["T"])
    tau = confinement_time_s(r["t_s"], r["surviving"])
    row = {"case": c["name"], "solenoid_Bz_T": c["B"], "plug_voltage_V": c["V"], "eta": c["eta"],
           "birth_temperature_eV": c["T"], "dt_s": c["dt"], "t_end_us": r["t_s"][-1] * 1e6,
           "surviving_end": r["surviving"][-1], "lost_axial_end": r["lost_axial"][-1],
           "lost_radial_end": r["lost_radial"][-1], "mean_energy_end_eV": r["mean_energy_eV"][-1],
           "tau_c_us": tau * 1e6, "eta_ss_estimate": min(1.0, tau / TAU_ION_S) if np.isfinite(tau) else 1.0,
           "well_depth_V": float(cfg.beam_potential_V(np.array([0.0]))[0] - cfg.beam_potential_V(np.array([cfg.pipe_radius_m]))[0])}
    print(f"  {c['name']:32s} surviving {row['surviving_end']:.3f}  tau_c {row['tau_c_us']:.3g} us  "
          f"E_end {row['mean_energy_end_eV']:.2f} eV", flush=True)
    ts = pd.DataFrame({"case": c["name"], "t_us": r["t_s"] * 1e6, "surviving": r["surviving"],
                       "mean_energy_eV": r["mean_energy_eV"], "lost_axial": r["lost_axial"], "lost_radial": r["lost_radial"]})
    return row, ts


def main() -> int:
    args = parse_args()
    cs = cases(args.dt_s)
    cfg0 = TrapConfig()
    print(f"C2: {len(cs)} cases, {args.n_electrons} electrons, {args.t_end_us} us, dt {args.dt_s:g} s; "
          f"gas {cfg0.gas_density_m3:.3g} m^-3, beam heating {cfg0.heating_W / 1.602e-19 * 1e-6:.3f} eV/us")
    if args.dry_run:
        for c in cs:
            print(f"  {c['name']}")
        print("[DRY RUN SUCCESS] nothing written.")
        return 0
    with ProcessPoolExecutor(max_workers=args.processes) as pool:
        res = list(pool.map(run, [(c, args.t_end_us * 1e-6, args.n_electrons) for c in cs]))
    summary = pd.DataFrame([r for r, _ in res])
    ts = pd.concat([t for _, t in res])
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out / "trap_summary.csv", index=False, float_format="%.5g")
    ts.to_csv(out / "trap_time_series.csv", index=False, float_format="%.5g")
    (out / "trap_summary.json").write_text(json.dumps({
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "model": "guiding-centre test electrons, static analytic plugs + (1 - eta) beam well, uniform B_z, "
                 "MC elastic e-H2 (approximate cross section), Coulomb heating by the beam; classical upper bound",
        "base_config": asdict(cfg0), "tau_ion_s": TAU_ION_S,
        "rows": summary.to_dict(orient="records"),
    }, indent=2, default=str))
    with pd.option_context("display.width", 200):
        print(summary.drop(columns=["case"]).round(3).to_string(index=False))

    setup_publication_style()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, b in zip(axes, B_FIELDS):
        for c in cs:
            if c["B"] != b or c["eta"] != 0.9 or c["name"].endswith("dtcheck"):
                continue
            g = ts[ts.case == c["name"]]
            ls = "-" if c["T"] == 1.0 else "--"
            ax.plot(g.t_us, g.surviving, ls=ls, label=f"plug {c['V']:g} V, T {c['T']:g} eV")
        ax.axvline(TAU_ION_S * 1e6, color="0.5", ls=":", lw=0.8)
        ax.set_xlabel("t [us]"); ax.set_title(f"B = {b} T, eta = 0.9", fontsize=10); ax.grid(alpha=0.3)
    axes[0].set_ylabel("surviving fraction"); axes[0].legend(fontsize=7)
    fig.suptitle("Test electrons in the static trap (classical upper bound; dotted: tau_ion = 80 us)", fontsize=9)
    save_figure(fig, out / "trap_survival")
    plt.close(fig)
    print(f"Wrote {out}/trap_summary.csv and figure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
