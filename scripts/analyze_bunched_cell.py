#!/usr/bin/env python3
"""
scripts/analyze_bunched_cell.py

RF-averaged vs peak-bunch neutralization in the plasma cell for the bunched-beam runs (task B2,
scripts/run_bunched_cell.py). Per snapshot, from the beam-core (r <= 2 mm) density profiles along
z over three whole RF wavelengths inside the cell (z = 0.02 to 0.164 m):

    eta_avg, eta_peak (top 10% of the proton line density: the 36 deg window), K_eff,peak / K0,peak = 1 - eta_peak,
    B_cell = max / mean line density, the n_e modulation along z, and the net charge in the gaps,

see plasma_column.bunched_cell. Summary values are averages over t >= --from_fraction of the run.
For a DC case eta_avg and eta_peak coincide.

Outputs in <scan_dir>/analysis/ (git-ignored):
    bunched_cell_time_series.csv, bunched_cell_summary.csv/.json,
    bunched_cell_eta_vs_t.{png,pdf}, bunched_cell_profiles.{png,pdf}

The seeded plasma is an analytic source estimate, not self-consistent proton-impact ionization.

Usage:
    python scripts/analyze_bunched_cell.py --dry_run
    python scripts/analyze_bunched_cell.py --scan_dir results/bunched_cell
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

from plasma_column.bunched_cell import bunch_metrics, core_z_profiles, rf_wavelength_m
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.warpx_io import find_plotfiles, load_plotfile_densities

N_WAVELENGTHS = 3


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RF-averaged vs peak-bunch neutralization in the cell (B2).")
    p.add_argument("--scan_dir", type=Path, default=PROJECT_ROOT / "results" / "bunched_cell")
    p.add_argument("--output_dir", type=Path, default=None, help="Default: <scan_dir>/analysis")
    p.add_argument("--from_fraction", type=float, default=0.5, help="Average over t >= this fraction of the run.")
    p.add_argument("--z_start", type=float, default=0.02,
                   help="Start of the 3-wavelength window [m] (0.02: cell; 0.12: main solenoid of the B4 section).")
    p.add_argument("--rf_frequency_hz", type=float, default=50e6)
    p.add_argument("--beam_energy_eV", type=float, default=30e3)
    p.add_argument("--dry_run", action="store_true", help="List cases and snapshot counts; write nothing.")
    return p.parse_args()


def case_info(case_dir: Path) -> dict:
    meta = json.loads((case_dir / "metadata.json").read_text())
    return meta.get("case", {"case_name": case_dir.name})


def main() -> int:
    args = parse_args()
    cases = sorted(d for d in args.scan_dir.iterdir() if (d / "metadata.json").exists()) if args.scan_dir.is_dir() else []
    lam = rf_wavelength_m(args.beam_energy_eV, args.rf_frequency_hz)
    print(f"lambda_RF = {lam * 100:.2f} cm; window z = {args.z_start} to {args.z_start + N_WAVELENGTHS * lam:.3f} m")
    if args.dry_run:
        for d in cases:
            print(f"  {d.name}: {len(find_plotfiles(d))} snapshots")
        print("[DRY RUN SUCCESS] nothing written.")
        return 0
    out_dir = args.output_dir or args.scan_dir / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows, last_profiles = [], {}
    for d in cases:
        info = case_info(d)
        for plt_path in find_plotfiles(d):
            s = load_plotfile_densities(plt_path)
            if s is None or "ne_3d" not in s:
                continue
            prof = core_z_profiles(s["ne_3d"], s["ni_3d"], s["np_3d"], s["x"], s["y"], s["z"])
            m = bunch_metrics(prof, args.z_start, lam, N_WAVELENGTHS)
            rows.append({"case_name": d.name, "time_ns": s["time"] * 1e9,
                         "beam_bunching_factor": info.get("beam_bunching_factor", 1.0),
                         "solenoid_Bz_T": info.get("solenoid_Bz_T"), "end_plug_voltage_V": info.get("end_plug_voltage_V"),
                         **m})
            last_profiles[d.name] = prof
    ts = pd.DataFrame(rows).sort_values(["case_name", "time_ns"])
    ts.to_csv(out_dir / "bunched_cell_time_series.csv", index=False)

    summ = []
    for name, g in ts.groupby("case_name"):
        late = g[g.time_ns >= args.from_fraction * g.time_ns.max()]
        summ.append({"case_name": name, "beam_bunching_factor": g.beam_bunching_factor.iloc[0],
                     "solenoid_Bz_T": g.solenoid_Bz_T.iloc[0], "end_plug_voltage_V": g.end_plug_voltage_V.iloc[0],
                     "window_ns": f"{late.time_ns.min():.0f}-{late.time_ns.max():.0f}",
                     **{f"{k}_mean": late[k].mean() for k in ("eta_avg", "eta_peak", "keff_over_k0_peak",
                                                             "bunching_factor_cell", "ne_modulation", "eta_gap_excess")},
                     "eta_avg_std": late.eta_avg.std(), "eta_peak_std": late.eta_peak.std()})
    summary = pd.DataFrame(summ)
    summary["static_cloud_eta_peak"] = summary.eta_avg_mean / summary.bunching_factor_cell_mean
    summary.to_csv(out_dir / "bunched_cell_summary.csv", index=False)
    (out_dir / "bunched_cell_summary.json").write_text(json.dumps({
        "provenance": {"scan_dir": str(args.scan_dir), "lambda_rf_m": lam, "z_window_m": [args.z_start, args.z_start + N_WAVELENGTHS * lam],
                       "r_core_m": 0.002, "peak_fraction": 0.1, "from_fraction": args.from_fraction,
                       "note": "seeded plasma (analytic source estimate); B_f = 5 cases are a bunch-focus study"},
        "cases": summ}, indent=2, default=float))
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(summary.round(3).to_string(index=False))

    import matplotlib.pyplot as plt
    setup_publication_style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for name, g in ts.groupby("case_name"):
        for ax, key in zip(axes, ("eta_avg", "eta_peak")):
            ax.plot(g.time_ns, g[key], marker=".", label=name)
    for ax, title in zip(axes, (r"RF-averaged $\eta_{\rm net}$ (core)", r"peak-bunch $\eta_{\rm net}$ (core)")):
        ax.set_xlabel("t [ns]"); ax.set_title(title); ax.grid(alpha=0.3)
    axes[0].set_ylabel(r"$\eta_{\rm net}$"); axes[1].legend(fontsize=7)
    fig.suptitle("Bunched beam in the cell, seeded H$_2$ (analytic source estimate); B$_f$ = 5: bunch-focus study", fontsize=9)
    save_figure(fig, out_dir / "bunched_cell_eta_vs_t")
    plt.close(fig)

    fig, axes = plt.subplots(len(last_profiles), 1, figsize=(8, 2.0 * len(last_profiles)), sharex=True, squeeze=False)
    for ax, (name, prof) in zip(axes[:, 0], last_profiles.items()):
        npm = prof["np"][(prof["z"] >= 0) & (prof["z"] <= 0.2)].mean() or 1.0
        ax.plot(prof["z"], prof["np"] / npm, label=r"$n_p$")
        ax.plot(prof["z"], (prof["ne"] - prof["ni"]) / npm, label=r"$n_e - n_i$")
        ax.plot(prof["z"], prof["ne"] / npm, lw=0.8, alpha=0.6, label=r"$n_e$")
        ax.set_ylabel("/ mean $n_p$"); ax.set_title(name, fontsize=8); ax.grid(alpha=0.3)
        ax.axvspan(args.z_start, args.z_start + N_WAVELENGTHS * lam, color="0.9", zorder=0)
    axes[0, 0].legend(fontsize=7, ncol=3); axes[-1, 0].set_xlabel("z [m]")
    fig.suptitle("Beam-core (r <= 2 mm) densities at the last snapshot; shaded: analysis window", fontsize=9)
    save_figure(fig, out_dir / "bunched_cell_profiles")
    plt.close(fig)
    print(f"Wrote {out_dir}/bunched_cell_summary.csv and figures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
