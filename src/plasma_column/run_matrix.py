"""
src/plasma_column/run_matrix.py

Parameter-scan matrix builder and result aggregator for the plasma-column project.

Provides:
  - ScanParameter / ScanMatrix dataclasses for defining a scan
  - build_scan_dataframe()  — enumerate all (gas, pressure, method) combinations
  - run_scan_matrix()       — launch subprocess for each case (or dry-run)
  - collect_scan_results()  — load completed runs and build summary DataFrame
  - save_scan_summary()     — write CSV

Designed to work with existing scripts/run_scan.py (YAML-driven) and the
new notebooks/runs/nb_parameter_scan.ipynb.
"""

from __future__ import annotations

import itertools
import json
import subprocess
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from plasma_column.diagnostics import (
    load_particle_number_diagnostic,
    compute_particle_number_metrics,
    warn_global_count_limitation,
)


# ── Scan definition dataclasses ───────────────────────────────────────────────

@dataclass
class ScanParameter:
    """Single axis of a parameter scan."""
    name: str            # parameter key, e.g. 'pressure_torr'
    values: list[Any]    # list of values to sweep


@dataclass
class ScanMatrix:
    """
    Full definition of a parameter scan matrix.

    Attributes:
        scan_name:   Human-readable name used in filenames and titles.
        script:      Path to the WarpX PICMI script to run.
        parameters:  List of ScanParameter objects (Cartesian product is taken).
        fixed:       Fixed arguments passed to every case (dict of argname→value).
        gases:       Gas species to sweep over (separate from 'parameters').
        methods:     Simulation methods to compare (e.g. ['seeded', 'callback']).
        dry_run:     If True, write metadata but do not launch subprocesses.
        runs_root:   Root directory for case output directories.
    """
    scan_name:  str
    script:     Path
    parameters: list[ScanParameter] = field(default_factory=list)
    fixed:      dict[str, Any]      = field(default_factory=dict)
    gases:      list[str]           = field(default_factory=lambda: ["H2", "Kr"])
    methods:    list[str]           = field(default_factory=lambda: ["seeded"])
    dry_run:    bool                = True
    runs_root:  Path                = Path("runs")


# ── Matrix builder ─────────────────────────────────────────────────────────────

def build_scan_dataframe(matrix: ScanMatrix) -> pd.DataFrame:
    """
    Enumerate all combinations in the scan matrix and return a DataFrame.

    Columns: case_name, gas, method, <param.name for each ScanParameter>, ...fixed...

    The case_name is constructed as:
      {scan_name}_{gas}_{method}_{param1_val}_{param2_val}_...
    """
    param_names  = [p.name for p in matrix.parameters]
    param_values = [p.values for p in matrix.parameters]

    rows = []
    for gas, method, *pvals in itertools.product(
        matrix.gases, matrix.methods, *param_values
    ):
        # Build case name
        parts = [matrix.scan_name, gas, method] + [_fmt_val(v) for v in pvals]
        case_name = "_".join(parts)

        row: dict[str, Any] = {
            "case_name": case_name,
            "gas":       gas,
            "method":    method,
        }
        for pname, pval in zip(param_names, pvals):
            row[pname] = pval
        row.update(matrix.fixed)
        rows.append(row)

    return pd.DataFrame(rows)


def _fmt_val(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.2g}".replace("-", "m").replace("+", "p").replace(".", "d")
    return str(v).replace(".", "d").replace("-", "m")


# ── Subprocess launcher ────────────────────────────────────────────────────────

def run_scan_matrix(
    scan_df: pd.DataFrame,
    matrix: ScanMatrix,
    *,
    extra_args: Optional[dict[str, str]] = None,
    warpx_data_dir: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """
    Launch a subprocess for each row of scan_df.

    If matrix.dry_run is True, only prints commands and writes metadata — does
    not execute any simulation steps.

    Returns a list of result dicts:
        {case_name, out_dir, returncode (or 'dry_run'), stdout, stderr}
    """
    results = []
    extra_args = extra_args or {}

    for _, row in scan_df.iterrows():
        case_name = row["case_name"]
        out_dir   = matrix.runs_root / case_name
        out_dir.mkdir(parents=True, exist_ok=True)

        cmd = [sys.executable, str(matrix.script), "--run"]
        cmd += ["--output_dir", str(out_dir)]
        cmd += ["--gas",        row.get("gas",    "H2")]
        cmd += ["--method",     row.get("method", "seeded")]

        if "pressure_torr" in row:
            cmd += ["--pressure_torr", str(row["pressure_torr"])]
        if "neutralization" in row:
            cmd += ["--neutralization", str(row["neutralization"])]
        if "max_steps" in row:
            cmd += ["--max_steps", str(row["max_steps"])]

        # Fixed args from matrix
        for k, v in matrix.fixed.items():
            if k not in ("gas", "method", "pressure_torr", "neutralization", "max_steps"):
                cmd += [f"--{k}", str(v)]

        # Extra per-call overrides
        for k, v in extra_args.items():
            cmd += [f"--{k}", str(v)]

        if warpx_data_dir is not None:
            cmd += ["--warpx_data_dir", str(warpx_data_dir)]

        # Write metadata
        meta = {
            "case_name":  case_name,
            "command":    " ".join(cmd),
            "scan_name":  matrix.scan_name,
            **{k: v for k, v in row.items()},
        }
        meta_path = out_dir / "scan_metadata.json"
        meta_path.write_text(json.dumps(meta, indent=2, default=str))

        if matrix.dry_run:
            print(f"  [DRY RUN] {case_name}")
            print(f"            {' '.join(cmd[:6])} ...")
            results.append({
                "case_name":  case_name,
                "out_dir":    out_dir,
                "returncode": "dry_run",
                "stdout":     "",
                "stderr":     "",
            })
            continue

        print(f"  [RUN] {case_name} → {out_dir}")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        results.append({
            "case_name":  case_name,
            "out_dir":    out_dir,
            "returncode": proc.returncode,
            "stdout":     proc.stdout[-2000:],
            "stderr":     proc.stderr[-1000:],
        })
        if proc.returncode != 0:
            print(f"    *** FAILED (rc={proc.returncode}) ***")
            print(proc.stderr[-500:])
        else:
            print(f"    OK (rc=0)")

    return results


# ── Result aggregator ─────────────────────────────────────────────────────────

def collect_scan_results(
    scan_df: pd.DataFrame,
    runs_root: Path,
    *,
    t_avg_window_frac: float = 0.25,
) -> pd.DataFrame:
    """
    Load completed runs for all cases in scan_df and compute summary metrics.

    For each case:
        - Searches for ParticleNumber_red.txt or neutralization_from_particle_number.csv
        - Computes final and time-averaged η_e, η_net, K_eff/K0
        - Time-average is over the last t_avg_window_frac fraction of the run

    Returns a copy of scan_df with extra columns:
        n_steps, final_eta_electron_only, final_eta_net, final_keff_over_k0,
        avg_eta_net (last window), status (ok / not_found / error)
    """
    warn_global_count_limitation()

    rows = []
    for _, row in scan_df.iterrows():
        case_name = row["case_name"]
        out_dir   = runs_root / case_name
        result    = dict(row)

        diag = _find_diag(out_dir)
        if diag is None:
            result.update({"status": "not_found", "n_steps": 0,
                           "final_eta_electron_only": float("nan"),
                           "final_eta_net": float("nan"),
                           "final_keff_over_k0": float("nan"),
                           "avg_eta_net": float("nan")})
            rows.append(result)
            continue

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                hist = load_particle_number_diagnostic(diag)
                hist = compute_particle_number_metrics(hist)

            n      = len(hist)
            window = max(1, int(n * t_avg_window_frac))
            tail   = hist.tail(window)

            result.update({
                "status":                  "ok",
                "n_steps":                 n,
                "final_eta_electron_only": float(hist["eta_electron_only"].iloc[-1])
                                           if "eta_electron_only" in hist.columns else float("nan"),
                "final_eta_net":           float(hist["eta_net"].iloc[-1])
                                           if "eta_net" in hist.columns else float("nan"),
                "final_keff_over_k0":      float(hist["keff_over_k0"].iloc[-1])
                                           if "keff_over_k0" in hist.columns else float("nan"),
                "avg_eta_net":             float(tail["eta_net"].mean())
                                           if "eta_net" in tail.columns else float("nan"),
            })
        except Exception as exc:
            result.update({"status": f"error:{exc}", "n_steps": 0,
                           "final_eta_electron_only": float("nan"),
                           "final_eta_net": float("nan"),
                           "final_keff_over_k0": float("nan"),
                           "avg_eta_net": float("nan")})

        rows.append(result)

    return pd.DataFrame(rows)


def _find_diag(out_dir: Path) -> Optional[Path]:
    for rel in [
        "reducedfiles/ParticleNumber_red.txt",
        "neutralization_from_particle_number.csv",
    ]:
        p = out_dir / rel
        if p.exists():
            return p
    return None


# ── Summary I/O ───────────────────────────────────────────────────────────────

def save_scan_summary(summary_df: pd.DataFrame, out_path: Path) -> Path:
    """Write scan summary DataFrame to CSV. Returns the written path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(out_path, index=False)
    return out_path


def load_scan_summary(csv_path: Path) -> pd.DataFrame:
    """Load a previously saved scan summary CSV."""
    return pd.read_csv(csv_path)
