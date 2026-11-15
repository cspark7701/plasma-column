#!/usr/bin/env python3
"""
scripts/suppressor_scan.py

Task CW4 of docs/physics_notes/simulation_strategy_tasks.md: suppressor voltage needed to keep the
compensating electrons of the line from draining into the inflector field
(plasma_column.suppressor, axisymmetric (r, z) Poisson model with the 10 mA beam).

Scan: suppressor -V_s = 0 ... 2 kV; aperture radius 5 and 7.5 mm (5 mm thick electrode, 10 mm pipe);
eta_down = 0.5, 0.7, 0.9 upstream (compensation ends at the suppressor); inflector leakage
potential V_inf = 0, +1, +3 kV on the pipe wall from 30 mm downstream (an illustrative stand-in for
the electron-attracting part of the inflector field; the real inflector field is a dipole, not
axisymmetric).

Criterion: the on-axis barrier (upstream compensated-beam potential minus the lowest on-axis
potential at and after the suppressor) must exceed the electron energy with margin, 20 V (C2: the
trapped electrons heat to ~5 eV in 100 us). Also reported: focal length of the suppressor lens for
the 30 keV beam (paraxial ray, relative to V_s = 0).

Outputs (default results/suppressor_scan/, git-ignored):
    suppressor_scan.csv / .json, suppressor_barrier.{png,pdf}, suppressor_axis_potential.{png,pdf}

Usage:
    python scripts/suppressor_scan.py --dry_run
    python scripts/suppressor_scan.py
"""

from __future__ import annotations

import argparse
import datetime
import itertools
import json
import os
import sys
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

from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.suppressor import SuppressorConfig, barrier_V, lens_focal_length_m, solve
from plasma_column.warpx_io import get_git_info

VOLTAGES = (0.0, 50.0, 100.0, 200.0, 300.0, 500.0, 1000.0, 2000.0)
APERTURES = (0.005, 0.0075)
ETAS = (0.5, 0.7, 0.9)
V_INF = (0.0, 1000.0, 3000.0)
MARGIN_V = 20.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Electron suppressor before the inflector (task CW4).")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "suppressor_scan")
    p.add_argument("--dry_run", action="store_true", help="List the scan; write nothing.")
    return p.parse_args()


def needed_voltage(g: pd.DataFrame) -> float:
    ok = g[g.barrier_V >= MARGIN_V].sort_values("suppressor_voltage_V")
    if ok.empty:
        return float("nan")
    v = ok.suppressor_voltage_V.iloc[0]
    lower = g[g.suppressor_voltage_V < v].sort_values("suppressor_voltage_V")
    if lower.empty:
        return float(v)
    a, b = lower.iloc[-1], ok.iloc[0]  # linear interpolation of the barrier between scan points
    return float(a.suppressor_voltage_V + (MARGIN_V - a.barrier_V) * (b.suppressor_voltage_V - a.suppressor_voltage_V)
                 / (b.barrier_V - a.barrier_V))


def main() -> int:
    args = parse_args()
    grid = list(itertools.product(APERTURES, ETAS, V_INF, VOLTAGES))
    print(f"CW4: {len(grid)} field solutions; margin {MARGIN_V} V")
    if args.dry_run:
        print(f"  V_s {VOLTAGES}, apertures {APERTURES}, eta_down {ETAS}, V_inf {V_INF}")
        print("[DRY RUN SUCCESS] nothing written.")
        return 0
    rows, refs, axis = [], {}, {}
    for ap, eta, vinf, vs in grid:
        cfg = SuppressorConfig(suppressor_voltage_V=vs, aperture_m=ap, eta_down=eta, inflector_voltage_V=vinf)
        sol = solve(cfg)
        key = (ap, eta, vinf)
        if vs == 0.0:
            refs[key] = sol
        b = barrier_V(sol, cfg)
        f = lens_focal_length_m(sol, refs[key], 30e3) if vs > 0 else np.inf
        rows.append({"aperture_mm": ap * 1e3, "eta_down": eta, "inflector_voltage_V": vinf,
                     "suppressor_voltage_V": vs, **b, "lens_focal_length_m": f})
        if eta == 0.7 and vinf == 1000.0 and ap == 0.005:
            axis[vs] = (sol["z_m"], sol["phi_axis_V"])
    df = pd.DataFrame(rows)
    need = []
    for (ap, eta, vinf), g in df.groupby(["aperture_mm", "eta_down", "inflector_voltage_V"]):
        v = needed_voltage(g)
        f = np.interp(v, g.suppressor_voltage_V, g.lens_focal_length_m.replace(np.inf, 1e9)) if np.isfinite(v) and v > 0 else np.inf
        need.append({"aperture_mm": ap, "eta_down": eta, "inflector_voltage_V": vinf, "V_s_needed_V": v,
                     "lens_focal_length_at_needed_m": f})
    need = pd.DataFrame(need)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "suppressor_scan.csv", index=False, float_format="%.5g")
    (out / "suppressor_scan.json").write_text(json.dumps({
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "model": "axisymmetric (r, z) Poisson, grounded 10 mm pipe, ring suppressor, inflector leakage as wall potential, "
                 "uniform 10 mA beam with eta_down upstream of the suppressor",
        "base_config": asdict(SuppressorConfig()), "margin_V": MARGIN_V,
        "needed": need.to_dict(orient="records"), "rows": df.to_dict(orient="records"),
    }, indent=2, default=float))
    with pd.option_context("display.width", 200):
        print(need.round(3).to_string(index=False))

    setup_publication_style()
    fig, axes = plt.subplots(1, len(V_INF), figsize=(13, 4), sharey=True)
    for ax, vinf in zip(axes, V_INF):
        for (ap, eta), g in df[df.inflector_voltage_V == vinf].groupby(["aperture_mm", "eta_down"]):
            ax.plot(g.suppressor_voltage_V, g.barrier_V, marker="o", ls="-" if ap == 5.0 else "--",
                    label=f"aperture {ap:g} mm, eta_down {eta}")
        ax.axhline(MARGIN_V, color="k", ls=":", lw=0.8)
        ax.set_xscale("symlog", linthresh=50); ax.set_xlabel("suppressor voltage magnitude V_s [V]")
        ax.set_title(f"inflector leakage V_inf = {vinf:g} V (illustrative)", fontsize=9); ax.grid(alpha=0.3)
    axes[0].set_ylabel("on-axis electron barrier [V]"); axes[0].legend(fontsize=6)
    save_figure(fig, out / "suppressor_barrier")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for vs, (z, pa) in axis.items():
        ax.plot(z * 100, pa, label=f"V_s = {vs:g} V")
    ax.set_xlabel("z from suppressor centre [cm]"); ax.set_ylabel("on-axis potential [V]")
    ax.set_title("aperture 5 mm, eta_down 0.7, V_inf = 1 kV", fontsize=9); ax.grid(alpha=0.3); ax.legend(fontsize=7)
    save_figure(fig, out / "suppressor_axis_potential")
    plt.close(fig)
    print(f"Wrote {out}/suppressor_scan.csv and figures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
