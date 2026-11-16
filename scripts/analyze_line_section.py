#!/usr/bin/env python3
"""
scripts/analyze_line_section.py

Electron retention per element of the solenoid/quadrupole section (task CW3,
scripts/run_line_section.py). For each case and snapshot, per region (drift1, solenoid, drift2,
Q1, drift3, Q2): electron, ion and beam counts in the region and the beam-core eta_net
(r <= 2 mm, beam-filled cells, plasma_column.diagnostics.compute_local_core_neutralization).
Per region: N_e(t_end)/N_e(0), tau_c fit over t >= --fit_from_fraction of the run, and the
late-time mean core eta_net (input eta_downstream for task CW2).

Outputs in <scan_dir>/analysis/ (git-ignored):
    line_section_time_series.csv, line_section_summary.csv/.json,
    line_section_electrons.{png,pdf}, line_section_eta.{png,pdf}

The seeded plasma is an analytic source estimate (residual-gas compensation seeded at t = 0), not
self-consistent proton-impact ionization.

Usage:
    python scripts/analyze_line_section.py --dry_run
    python scripts/analyze_line_section.py --scan_dir results/line_section
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from analyze_confinement_scan import fit_tau
from plasma_column.diagnostics import compute_local_core_neutralization
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.warpx_io import find_plotfiles, load_plotfile_densities

REGIONS = {"drift1": (0.0, 0.10), "solenoid": (0.10, 0.35), "drift2": (0.35, 0.45),
           "Q1": (0.45, 0.57), "drift3": (0.57, 0.65), "Q2": (0.65, 0.77)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Electron retention per element of the line section (CW3).")
    p.add_argument("--scan_dir", type=Path, default=PROJECT_ROOT / "results" / "line_section")
    p.add_argument("--output_dir", type=Path, default=None, help="Default: <scan_dir>/analysis")
    p.add_argument("--fit_from_fraction", type=float, default=0.5)
    p.add_argument("--dry_run", action="store_true", help="List cases and snapshot counts; write nothing.")
    return p.parse_args()


def region_rows(case: str, d: dict) -> list[dict]:
    x, y, z = d["x"], d["y"], d["z"]
    dv = (x[1] - x[0]) * (y[1] - y[0]) * (z[1] - z[0])
    rows = []
    for name, (z0, z1) in REGIONS.items():
        m = (z >= z0) & (z < z1)
        core = compute_local_core_neutralization(d["ne_3d"], d["ni_3d"], d["np_3d"], x, y, z,
                                                 z_min_col=z0, z_max_col=z1)
        rows.append({"case_name": case, "region": name, "time_ns": d["time"] * 1e9,
                     "Ne": float(d["ne_3d"][:, :, m].sum() * dv), "Ni": float(d["ni_3d"][:, :, m].sum() * dv),
                     "Np": float(d["np_3d"][:, :, m].sum() * dv),
                     "eta_net_core": core["eta_net_local"], "beam_in_core": core["beam_in_core"]})
    return rows


def main() -> int:
    args = parse_args()
    cases = sorted(d for d in args.scan_dir.iterdir() if (d / "metadata.json").exists()) if args.scan_dir.is_dir() else []
    if args.dry_run:
        for d in cases:
            print(f"  {d.name}: {len(find_plotfiles(d))} snapshots")
        print("[DRY RUN SUCCESS] nothing written.")
        return 0
    out_dir = args.output_dir or args.scan_dir / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for d in cases:
        for plt_path in find_plotfiles(d):
            s = load_plotfile_densities(plt_path)
            if s is not None and "ne_3d" in s:
                rows.extend(region_rows(d.name, s))
    ts = pd.DataFrame(rows).sort_values(["case_name", "region", "time_ns"])
    ts.to_csv(out_dir / "line_section_time_series.csv", index=False)

    summ = []
    for (case, region), g in ts.groupby(["case_name", "region"], sort=False):
        g = g.sort_values("time_ns")
        late = g[g.time_ns >= args.fit_from_fraction * g.time_ns.max()]
        fit = fit_tau(late.time_ns.to_numpy() * 1e-9, late.Ne.to_numpy())
        summ.append({"case_name": case, "region": region, "Ne_end_over_start": g.Ne.iloc[-1] / g.Ne.iloc[0],
                     "Ni_end_over_start": g.Ni.iloc[-1] / g.Ni.iloc[0],
                     "tau_c_us": fit["tau_c_s"] * 1e6, "tau_c_lower_bound_us": fit["tau_c_lower_bound_s"] * 1e6,
                     "eta_net_core_late_mean": late.eta_net_core.mean(), "eta_net_core_end": g.eta_net_core.iloc[-1]})
    summary = pd.DataFrame(summ)
    summary.to_csv(out_dir / "line_section_summary.csv", index=False)
    (out_dir / "line_section_summary.json").write_text(json.dumps({
        "regions_m": REGIONS, "fit_from_fraction": args.fit_from_fraction,
        "note": "seeded residual-gas plasma (analytic source estimate), DC 10 mA beam, hard-edge elements",
        "rows": summ}, indent=2, default=float))
    with pd.option_context("display.width", 200):
        print(summary.round(3).to_string(index=False))

    import matplotlib.pyplot as plt
    setup_publication_style()
    names = list(ts.case_name.unique())
    fig, axes = plt.subplots(1, len(names), figsize=(4.5 * len(names), 3.8), sharey=True, squeeze=False)
    for ax, case in zip(axes[0], names):
        for region in REGIONS:
            g = ts[(ts.case_name == case) & (ts.region == region)]
            ax.plot(g.time_ns, g.Ne / g.Ne.iloc[0], marker=".", label=region)
        ax.set_title(case, fontsize=10); ax.set_xlabel("t [ns]"); ax.grid(alpha=0.3)
    axes[0, 0].set_ylabel(r"$N_e(t)/N_e(0)$ in the region"); axes[0, 0].legend(fontsize=7)
    fig.suptitle("Electron retention per element (seeded residual-gas plasma, analytic source estimate)", fontsize=9)
    save_figure(fig, out_dir / "line_section_electrons")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.8))
    w = 0.8 / max(1, len(names))
    for k, case in enumerate(names):
        s = summary[summary.case_name == case].set_index("region").reindex(list(REGIONS))
        ax.bar(np.arange(len(REGIONS)) + k * w, s.eta_net_core_late_mean, width=w, label=case)
    ax.set_xticks(np.arange(len(REGIONS)) + 0.4 - w / 2, list(REGIONS))
    ax.set_ylabel(r"late-time core $\eta_{\rm net}$"); ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=8)
    fig.suptitle("Beam-core compensation per element, second half of the run", fontsize=9)
    save_figure(fig, out_dir / "line_section_eta")
    plt.close(fig)
    print(f"Wrote {out_dir}/line_section_summary.csv and figures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
