#!/usr/bin/env python3
"""
scripts/compare_solver_runs.py

Compare two runs of the same case made with different field solvers (e.g. ES vs EM) over their
common physical time window. Global particle counts are compared at run A's ParticleNumber times
(run B interpolated in time); local core values come from each run's diagnostics_summary.json
(written by postprocess_case.py from the last plotfile, so both runs should end at the same time).

Generates, under --output_dir:
- solver_comparison_vs_t.csv
- solver_comparison_summary.json
- solver_comparison_counts.png / .pdf

Usage:
    python scripts/compare_solver_runs.py --run_a runs/solver_cmp/es --run_b runs/solver_cmp/em \
        --label_a ES --label_b EM --output_dir runs/solver_cmp --dry_run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from _path_setup import PROJECT_ROOT  # noqa: F401
except ImportError:
    from scripts._path_setup import PROJECT_ROOT  # noqa: F401

from plasma_column.diagnostics import load_particle_number_diagnostic

SPECIES = ("Np", "Ne", "Ni")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two field-solver runs of the same case.")
    parser.add_argument("--run_a", required=True, help="Reference run directory (e.g. ES).")
    parser.add_argument("--run_b", required=True, help="Run directory to compare (e.g. EM).")
    parser.add_argument("--label_a", default="ES")
    parser.add_argument("--label_b", default="EM")
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--dry_run", action="store_true", help="Check inputs only; write nothing.")
    return parser.parse_args()


def load_counts(run_dir: Path) -> pd.DataFrame:
    df = load_particle_number_diagnostic(run_dir / "reducedfiles" / "particle_number.txt")
    return df[["step", "time", *SPECIES]].astype(float).sort_values("time").reset_index(drop=True)


def load_core(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "diagnostics_summary.json"
    if not path.exists():
        return {}
    summary = json.loads(path.read_text())
    core = dict(summary.get("core_averages") or {})
    core["local_plotfile"] = summary.get("local_plotfile")
    return core


def compare_counts(a: pd.DataFrame, b: pd.DataFrame, label_a: str, label_b: str) -> pd.DataFrame:
    t_end_s = min(a["time"].iloc[-1], b["time"].iloc[-1])
    out = a[a["time"] <= t_end_s * (1.0 + 1e-9)][["time", *SPECIES]].rename(columns={s: f"{s}_{label_a}" for s in SPECIES})
    for s in SPECIES:
        b_on_a = np.interp(out["time"], b["time"], b[s])
        out[f"{s}_{label_b}"] = b_on_a
        ref = out[f"{s}_{label_a}"].to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            out[f"{s}_reldiff"] = np.where(ref > 0, (b_on_a - ref) / ref, np.nan)
    for label in (label_a, label_b):
        with np.errstate(divide="ignore", invalid="ignore"):
            np_ = out[f"Np_{label}"].to_numpy()
            out[f"eta_net_{label}"] = np.where(np_ > 0, (out[f"Ne_{label}"] - out[f"Ni_{label}"]) / np_, np.nan)
    return out.rename(columns={"time": "time_s"})


def plot_counts(df: pd.DataFrame, label_a: str, label_b: str, out_stem: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    t_ns = df["time_s"] * 1e9
    for s, color in zip(SPECIES, ("C0", "C1", "C2")):
        ax1.plot(t_ns, df[f"{s}_{label_a}"], color=color, label=f"{s} {label_a}")
        ax1.plot(t_ns, df[f"{s}_{label_b}"], color=color, ls="--", label=f"{s} {label_b}")
    ax1.set_xlabel("t [ns]")
    ax1.set_ylabel("physical particles in domain")
    ax1.legend(fontsize=8)
    ax2.plot(t_ns, df[f"eta_net_{label_a}"], label=label_a)
    ax2.plot(t_ns, df[f"eta_net_{label_b}"], ls="--", label=label_b)
    ax2.set_xlabel("t [ns]")
    ax2.set_ylabel("global eta_net = (Ne - Ni) / Np")
    ax2.set_ylim(-1, 5)
    ax2.legend(fontsize=8)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out_stem.with_suffix(f".{ext}"), dpi=150)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    run_a, run_b, out_dir = Path(args.run_a), Path(args.run_b), Path(args.output_dir)
    for run in (run_a, run_b):
        pn = run / "reducedfiles" / "particle_number.txt"
        print(f"{run}: particle_number {'found' if pn.exists() else 'MISSING'}, "
              f"diagnostics_summary {'found' if (run / 'diagnostics_summary.json').exists() else 'missing'}")
    if args.dry_run:
        print("Dry run: no files written.")
        return 0

    a, b = load_counts(run_a), load_counts(run_b)
    df = compare_counts(a, b, args.label_a, args.label_b)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "solver_comparison_vs_t.csv", index=False)

    final = df.iloc[-1]
    summary = {
        "run_a": str(run_a), "run_b": str(run_b), "label_a": args.label_a, "label_b": args.label_b,
        "common_end_time_s": float(final["time_s"]),
        "final_reldiff": {s: float(final[f"{s}_reldiff"]) for s in SPECIES},
        "max_abs_reldiff": {s: float(np.nanmax(np.abs(df[f"{s}_reldiff"]))) if df[f"{s}_reldiff"].notna().any() else None
                            for s in SPECIES},
        "final_eta_net_global": {args.label_a: float(final[f"eta_net_{args.label_a}"]),
                                 args.label_b: float(final[f"eta_net_{args.label_b}"])},
        "core_local": {args.label_a: load_core(run_a), args.label_b: load_core(run_b)},
    }
    (out_dir / "solver_comparison_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    plot_counts(df, args.label_a, args.label_b, out_dir / "solver_comparison_counts")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
