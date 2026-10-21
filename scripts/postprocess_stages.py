#!/usr/bin/env python3
"""
scripts/postprocess_stages.py

Stage-level analysis of a production matrix with a ``stages:`` section (cases/production.yaml).
Each case is run and postprocessed once in ``<results_dir>/<case_name>/`` (postprocess_case.py); this
script collects those outputs per stage. Missing or unfinished cases are reported, not fatal, so a stage
can be analyzed while later production runs are still going.

Generates, under ``<results_dir>/stage_<stage>/``:
- stage_summary.csv / stage_summary.json : one row per case (status, global and local-core values)
- local_eta_by_case.png / .pdf           : local core eta_net and eta_electron_only per case
- eta_vs_pressure.png / .pdf             : local eta_net and K_eff/K0 vs pressure (stages with >= 2
                                            pressures for a gas)

Global values are domain-wide ParticleNumber ratios at the last step (sanity check only); local values
come from the beam core inside the plasma column (diagnostics_summary.json).

Usage:
    python scripts/postprocess_stages.py --matrix cases/production.yaml --results_dir results/production --dry_run
    python scripts/postprocess_stages.py --matrix cases/production.yaml --results_dir results/production
    python scripts/postprocess_stages.py --matrix cases/production.yaml --results_dir results/production \
        --stage A_method_scan
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from _path_setup import PROJECT_ROOT  # noqa: F401
except ImportError:
    from scripts._path_setup import PROJECT_ROOT  # noqa: F401

from plasma_column.diagnostics import load_particle_number_diagnostic
from plasma_column.schema import ScanMatrixConfig, SimulationCaseConfig

LOCAL_KEYS = (
    "np_core_avg", "ne_core_avg", "ni_core_avg", "eta_electron_only_local", "eta_net_local",
    "keff_over_k0_local", "keff_over_k0_electron_only_local", "overcompensated", "beam_in_core",
    "core_beam_fill_fraction", "beam_z_max_m",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect per-case production results into stage summaries.")
    parser.add_argument("--matrix", type=Path, default=Path("cases/production.yaml"))
    parser.add_argument("--results_dir", type=Path, default=Path("results/production"))
    parser.add_argument("--stage", action="append", help="Stage to process (repeatable); default: all stages.")
    parser.add_argument("--no_plots", action="store_true", help="Write tables only.")
    parser.add_argument("--dry_run", action="store_true", help="Report case status only; write nothing.")
    return parser.parse_args()


def _finite_or_none(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def collect_case(case: SimulationCaseConfig, results_dir: Path) -> dict[str, Any]:
    """One summary row for a case: status, final global counts and local-core values."""
    case_dir = results_dir / case.case_name
    row: dict[str, Any] = {
        "case_name": case.case_name,
        "method": case.method,
        "gas": case.plasma.gas,
        "pressure_torr": case.plasma.pressure_torr,
        "max_steps": case.numerics.max_steps,
    }
    pn_path = case_dir / "reducedfiles" / "particle_number.txt"
    if not case_dir.is_dir() or not pn_path.exists():
        row["status"] = "missing"
        return row

    df = load_particle_number_diagnostic(pn_path)
    last = df.iloc[-1]
    final_step = int(last["step"])
    row["final_step"] = final_step
    row["status"] = "complete" if final_step >= case.numerics.max_steps else "incomplete"
    np_, ne, ni = (float(last[k]) for k in ("Np", "Ne", "Ni"))
    row.update({"Np_global": np_, "Ne_global": ne, "Ni_global": ni})
    row["eta_net_global"] = (ne - ni) / np_ if np_ > 0 else None

    summary_path = case_dir / "diagnostics_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text())
        core = summary.get("core_averages") or {}
        row.update({k: _finite_or_none(core.get(k)) for k in LOCAL_KEYS})
        row["local_warning"] = summary.get("warning")
        row["rescaling"] = summary.get("rescaling")
    else:
        row["local_warning"] = "diagnostics_summary.json missing: run postprocess_case.py"
    return row


def plot_stage(df: pd.DataFrame, stage: str, out_dir: Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    written: list[Path] = []
    done = df[df.get("eta_net_local").notna()] if "eta_net_local" in df else df.iloc[0:0]
    if done.empty:
        return written

    fig, ax = plt.subplots(figsize=(max(6.0, 0.9 * len(done) + 2), 4))
    x = range(len(done))
    ax.bar([i - 0.2 for i in x], done["eta_net_local"], width=0.4, label="local eta_net")
    ax.bar([i + 0.2 for i in x], done["eta_electron_only_local"], width=0.4, label="local eta_electron_only")
    ax.axhline(1.0, color="k", lw=0.8, ls=":")
    ax.set_xticks(list(x))
    ax.set_xticklabels(done["case_name"], rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("beam-core neutralization fraction")
    ax.set_title(f"{stage}: local core neutralization at the last snapshot")
    ax.legend(fontsize=8)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        path = out_dir / f"local_eta_by_case.{ext}"
        fig.savefig(path, dpi=150)
        written.append(path)
    plt.close(fig)

    by_gas = {g: d.sort_values("pressure_torr") for g, d in done.groupby("gas") if d["pressure_torr"].nunique() >= 2}
    if by_gas:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
        for gas, d in by_gas.items():
            for method, dm in d.groupby("method"):
                label = f"{gas} ({method})"
                ax1.plot(dm["pressure_torr"], dm["eta_net_local"], "o-", label=label)
                ax2.plot(dm["pressure_torr"], dm["keff_over_k0_local"], "o-", label=label)
        for ax, ylabel in ((ax1, "local eta_net"), (ax2, "local K_eff / K0 (net)")):
            ax.set_xscale("log")
            ax.set_xlabel("gas pressure [Torr]")
            ax.set_ylabel(ylabel)
            ax.legend(fontsize=8)
        ax2.axhline(0.0, color="k", lw=0.8, ls=":")
        fig.suptitle(f"{stage}: beam-core values at the last snapshot")
        fig.tight_layout()
        for ext in ("png", "pdf"):
            path = out_dir / f"eta_vs_pressure.{ext}"
            fig.savefig(path, dpi=150)
            written.append(path)
        plt.close(fig)
    return written


def main() -> int:
    args = parse_args()
    matrix = ScanMatrixConfig.from_yaml(args.matrix)
    if not matrix.stages:
        print(f"Error: {args.matrix} has no 'stages:' section.")
        return 1
    stages = args.stage or list(matrix.stages)

    for stage in stages:
        rows = [collect_case(c, args.results_dir) for c in matrix.stage_cases(stage)]
        df = pd.DataFrame(rows)
        counts = df["status"].value_counts().to_dict()
        print(f"== {stage}: {len(df)} cases {counts}")
        for r in rows:
            eta = r.get("eta_net_local")
            eta_s = f"{eta:.3f}" if isinstance(eta, float) else "-"
            print(f"   {r['case_name']:<24} {r['status']:<10} step {r.get('final_step', '-')!s:>6}  local eta_net {eta_s}")
        if args.dry_run:
            continue

        out_dir = args.results_dir / f"stage_{stage}"
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "stage_summary.csv", index=False)
        payload = {"matrix": str(args.matrix), "stage": stage, "status_counts": counts,
                   "cases": [{k: _finite_or_none(v) for k, v in r.items()} for r in rows]}
        (out_dir / "stage_summary.json").write_text(json.dumps(payload, indent=2, default=str))
        plots = [] if args.no_plots else plot_stage(df, stage, out_dir)
        print(f"   -> {out_dir}/stage_summary.csv" + (f" (+{len(plots)} plot files)" if plots else ""))
    if args.dry_run:
        print("Dry run: no files written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
