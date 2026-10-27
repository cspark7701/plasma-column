#!/usr/bin/env python3
"""
scripts/analyze_confinement_scan.py

Analysis of the electron-confinement scan (scripts/run_confinement_scan.py, task 107).

For each case (results/confinement_scan/<case>/):
    - electrons and ions inside the plasma cell (0 <= z <= 0.20 m, whole cross-section),
      N_e,cell(t) and N_i,cell(t), integrated from the 3D snapshots;
    - beam-core eta_net(t) and n_e/n_b (r <= 2 mm, beam-filled cells), as in production;
    - electron confinement time tau_c from an exponential fit of N_e,cell(t) over the second half of
      the run (after the beam has filled the cell and the ions have largely left). If N_e,cell does
      not decrease, only a lower bound is given: tau_c > window / (1 - N_end / N_start), using the
      fit's 2-sigma upper bound on the loss rate;
    - tau_c_late from the last quarter of the run only (flags an accelerating loss);
    - the steady-state estimate eta_ss ~ min(1, tau_c / tau_ion), tau_ion = 80 us (H2, 1e-5 Torr),
      evaluated with the 2-sigma lower bound of tau_c (so it is a lower bound on eta_ss).

Outputs (default results/confinement_scan/analysis/, git-ignored):
    confinement_summary.csv / .json
    cell_electrons_vs_t.{png,pdf}
    core_eta_vs_t.{png,pdf}

Usage:
    python scripts/analyze_confinement_scan.py --dry_run
    python scripts/analyze_confinement_scan.py
"""

from __future__ import annotations

import argparse
import json
import math
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

from plasma_column.design_estimates import compute_design_numbers
from plasma_column.diagnostics import compute_local_core_neutralization
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.warpx_io import find_plotfiles, load_plotfile_densities

CELL_Z = (0.0, 0.20)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze the electron-confinement scan.")
    p.add_argument("--scan_dir", type=Path, default=PROJECT_ROOT / "results" / "confinement_scan")
    p.add_argument("--output_dir", type=Path, default=None, help="Default: <scan_dir>/analysis")
    p.add_argument("--fit_from_fraction", type=float, default=0.5,
                   help="Fit tau_c over t >= this fraction of the run.")
    p.add_argument("--dry_run", action="store_true", help="List cases and snapshot counts; write nothing.")
    return p.parse_args()


def snapshot_series(case_dir: Path) -> pd.DataFrame:
    rows = []
    for plt_path in find_plotfiles(case_dir):
        d = load_plotfile_densities(plt_path)
        if d is None or "ne_3d" not in d:
            continue
        x, y, z = d["x"], d["y"], d["z"]
        dv = (x[1] - x[0]) * (y[1] - y[0]) * (z[1] - z[0])
        zmask = (z >= CELL_Z[0]) & (z <= CELL_Z[1])
        core = compute_local_core_neutralization(d["ne_3d"], d["ni_3d"], d["np_3d"], x, y, z)
        rows.append({
            "time": d.get("time", np.nan),
            "Ne_cell": float(d["ne_3d"][:, :, zmask].sum() * dv),
            "Ni_cell": float(d["ni_3d"][:, :, zmask].sum() * dv),
            "Np_cell": float(d["np_3d"][:, :, zmask].sum() * dv),
            "eta_net_local": core["eta_net_local"],
            "eta_electron_only_local": core["eta_electron_only_local"],
            "core_beam_fill_fraction": core["core_beam_fill_fraction"],
        })
    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)


def fit_tau(t: np.ndarray, n: np.ndarray) -> dict[str, float]:
    """Exponential fit ln N = a - t / tau. Returns tau (inf if not decaying) and a 2-sigma lower bound."""
    ok = n > 0
    t, n = t[ok], n[ok]
    if len(t) < 3:
        return {"tau_c_s": math.nan, "tau_c_lower_bound_s": math.nan, "loss_fraction": math.nan}
    coef, cov = np.polyfit(t, np.log(n), 1, cov=True)
    slope, err = coef[0], math.sqrt(cov[0, 0])
    loss_rate_hi = -(slope - 2.0 * err)  # 2-sigma upper bound on the loss rate 1/tau
    return {
        "tau_c_s": (-1.0 / slope) if slope < 0 else math.inf,
        "tau_c_lower_bound_s": (1.0 / loss_rate_hi) if loss_rate_hi > 0 else math.inf,
        "loss_fraction": float(1.0 - n[-1] / n[0]),
    }


def main() -> None:
    args = parse_args()
    out = args.output_dir or args.scan_dir / "analysis"
    tau_ion = compute_design_numbers()["tau_h2_s"]
    case_dirs = sorted(p for p in args.scan_dir.iterdir() if (p / "metadata.json").exists())

    if args.dry_run:
        for c in case_dirs:
            print(f"  {c.name:22s} snapshots: {len(find_plotfiles(c))}")
        print("[DRY RUN SUCCESS] nothing written.")
        return

    series, rows = {}, []
    for c in case_dirs:
        meta = json.loads((c / "metadata.json").read_text())["case"]
        s = snapshot_series(c)
        if s.empty:
            continue
        series[c.name] = s
        t_end = s.time.max()
        w = s[s.time >= args.fit_from_fraction * t_end]
        fit = fit_tau(w.time.to_numpy(), w.Ne_cell.to_numpy())
        wl = s[s.time >= 0.75 * t_end]
        fit_late = fit_tau(wl.time.to_numpy(), wl.Ne_cell.to_numpy())
        tau_c = fit["tau_c_s"]
        bound = fit["tau_c_lower_bound_s"]
        rows.append({
            "case_name": c.name, **meta,
            "t_end_ns": t_end * 1e9,
            "fit_window_ns": f"{w.time.min() * 1e9:.0f}-{t_end * 1e9:.0f}",
            "Ne_cell_end_over_start": float(s.Ne_cell.iloc[-1] / s.Ne_cell.iloc[0]),
            "Ni_cell_end_over_start": float(s.Ni_cell.iloc[-1] / s.Ni_cell.iloc[0]),
            "window_electron_loss_fraction": fit["loss_fraction"],
            "tau_c_fit_us": tau_c * 1e6,
            "tau_c_2sigma_lower_bound_us": bound * 1e6,
            # Fit over the last quarter only: shorter than tau_c_fit when the loss accelerates.
            "tau_c_late_fit_us": fit_late["tau_c_s"] * 1e6,
            # Lower bound on eta_ss from the tau_c lower bound (1 if no loss is resolved; NaN if no fit).
            "eta_ss_lower_bound": (math.nan if math.isnan(bound) else min(1.0, bound / tau_ion)),
            "eta_net_local_end": float(s.eta_net_local.iloc[-1]),
            "eta_electron_only_local_end": float(s.eta_electron_only_local.iloc[-1]),
        })
    summary = pd.DataFrame(rows)
    print(summary[["case_name", "Ne_cell_end_over_start", "tau_c_fit_us", "tau_c_2sigma_lower_bound_us",
                   "tau_c_late_fit_us", "eta_ss_lower_bound", "eta_net_local_end"]].to_string(index=False, float_format="%.3g"))

    out.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out / "confinement_summary.csv", index=False, float_format="%.6g")
    (out / "confinement_summary.json").write_text(json.dumps(
        {"tau_ion_s": tau_ion, "cell_z_m": CELL_Z, "fit_from_fraction": args.fit_from_fraction,
         "cases": summary.to_dict(orient="records")}, indent=2, default=str))
    series_df = pd.concat([s.assign(case_name=k) for k, s in series.items()], ignore_index=True)
    series_df.to_csv(out / "confinement_time_series.csv", index=False, float_format="%.6g")

    setup_publication_style()
    colors = {0.0: "tab:red", 0.05: "tab:orange", 0.15: "tab:blue"}
    for col, fname, ylabel in (("Ne_cell", "cell_electrons_vs_t", r"$N_{e,\rm cell}(t)/N_{e,\rm cell}(0)$"),
                               ("eta_net_local", "core_eta_vs_t", r"beam-core $\eta_{\rm net}$")):
        tes = sorted({r["electron_temperature_eV"] for r in rows})
        fig, axes = plt.subplots(1, len(tes), figsize=(5 * len(tes), 4), sharey=True, squeeze=False)
        axes = axes[0]
        for ax, te in zip(axes, tes):
            for r in rows:
                if r["electron_temperature_eV"] != te:
                    continue
                s = series[r["case_name"]]
                y = s[col] / s[col].iloc[0] if col == "Ne_cell" else s[col]
                ls = "-" if r["end_plug_voltage_V"] > 0 else "--"
                label = f"B = {r['solenoid_Bz_T']:g} T, plug {r['end_plug_voltage_V']:g} V"
                if r["end_plug_voltage_V"] > 0 and not pd.isna(r.get("end_plug_width_m", float("nan"))):
                    label += f", w {r['end_plug_width_m'] * 1e3:g} mm"
                one_field = len({q["solenoid_Bz_T"] for q in rows}) == 1
                color = f"C{rows.index(r)}" if one_field else colors.get(r["solenoid_Bz_T"], "k")
                ax.plot(s.time * 1e9, y, ls, marker="o", ms=3, color=color, label=label)
            ax.set_title(f"seed T_e = {te:g} eV", fontsize=10)
            ax.set_xlabel("t [ns]")
        axes[0].set_ylabel(ylabel)
        axes[0].legend(fontsize=7)
        fig.suptitle(f"{args.scan_dir.name}, seeded H$_2$ $10^{{-5}}$ Torr (analytic source estimate)", fontsize=10)
        fig.tight_layout()
        save_figure(fig, out / fname)
        plt.close(fig)
    print(f"Wrote {out}/confinement_summary.csv and figures.")


if __name__ == "__main__":
    main()
