#!/usr/bin/env python3
"""
scripts/run_confinement_scan.py

Electron-confinement scan (task 107, step 2 of docs/physics_notes/neutralizer_efficiency_strategy.md).
Runs the seeded H2 plasma column (1e-5 Torr, DC 10 mA beam) for 650 ns on the small 32x32x256 grid,
for every combination of

    cell solenoid B_z          : 0, 0.05, 0.15 T
    seed electron temperature  : 1 eV (production value), 10 eV (secondary-electron-like)
    end plugs                  : off, 300 V analytic plugs (> the ~158 V beam potential well)

All cases use the same time step as production (9.476 ps, set by 0.15 T) so they differ only in
the physics settings. Output: results/confinement_scan/<case>/ (git-ignored), one metadata.json per
case. Analysis: scripts/analyze_confinement_scan.py.

The seeded plasma is an analytic source estimate (prescribed n_e = n_i at t = 0), not
self-consistent proton-impact ionization. The end plugs are an analytic applied potential, not
electrode surfaces.

Usage:
    python scripts/run_confinement_scan.py --dry_run
    python scripts/run_confinement_scan.py --parallel 3
    python scripts/run_confinement_scan.py --parallel 3 --only B0p15_Te1_plug0
"""

from __future__ import annotations

import argparse
import datetime
import itertools
import json
import os
import queue
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.warpx_io import get_git_info

DRIVER = PROJECT_ROOT / "scripts" / "plasma_column_mcc_picmi_v7.py"
WARPX_DIR = Path("/home/cspark/Work/simulation_codes-working/warpx")
DT_S = 9.4760501726e-12
BZ_T = (0.0, 0.05, 0.15)
TE_EV = (1.0, 10.0)
PLUG_V = (0.0, 300.0)

COMMON = {
    "--gas": "H2", "--pressure_torr": "1e-5", "--neutralization": "-1",
    "--solver": "es", "--dt": repr(DT_S),
    "--nx": "32", "--ny": "32", "--nz": "256",
    "--nppc_beam": "4", "--nppc_plasma": "4",
    "--reduced_diag_period": "50", "--mcc": "none",
}


def tag(x: float) -> str:
    return f"{x:g}".replace(".", "p")


def scan_cases() -> list[dict]:
    cases = []
    for bz, te, plug in itertools.product(BZ_T, TE_EV, PLUG_V):
        cases.append({"case_name": f"B{tag(bz)}_Te{tag(te)}_plug{tag(plug)}",
                      "solenoid_Bz_T": bz, "electron_temperature_eV": te, "end_plug_voltage_V": plug})
    return cases


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Electron-confinement scan of the seeded plasma column.")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "confinement_scan")
    p.add_argument("--duration_ns", type=float, default=650.0)
    p.add_argument("--snapshots", type=int, default=20)
    p.add_argument("--parallel", type=int, default=3, help="Cases run at the same time.")
    p.add_argument("--cores", type=int, default=8, help="OpenMP threads per case.")
    p.add_argument("--only", action="append", help="Run only these case names (repeatable).")
    p.add_argument("--dry_run", action="store_true", help="Print the commands and write nothing.")
    return p.parse_args()


def command(case: dict, out: Path, steps: int, snapshots: int, cores: int,
            common: dict[str, str] | None = None) -> list[str]:
    """Driver command line; case keys end_plug_width_m / end_plug_offset_m are optional."""
    cmd = [sys.executable, str(DRIVER), "--run", "--output_dir", str(out),
           "--max_steps", str(steps), "--diag_period", str(max(1, steps // snapshots)),
           "--checkpoint_period", str(steps // 2), "--cores", str(cores), "--gpu", "auto",
           "--solenoid_Bz", repr(case["solenoid_Bz_T"]),
           "--electron_temperature_eV", repr(case["electron_temperature_eV"]),
           "--end_plug_voltage", repr(case["end_plug_voltage_V"])]
    if "end_plug_width_m" in case:
        cmd += ["--end_plug_width", repr(case["end_plug_width_m"])]
    if "end_plug_offset_m" in case:
        cmd += ["--end_plug_offset", repr(case["end_plug_offset_m"])]
    for k, v in (common or COMMON).items():
        cmd += [k, v]
    return cmd


def finished(out: Path, steps: int) -> bool:
    pn = out / "reducedfiles" / "particle_number.txt"
    if not pn.exists():
        return False
    last = pn.read_text().strip().splitlines()[-1]
    try:
        # particle_number.txt is written every --reduced_diag_period steps, so the last line can be
        # up to one period short of the final step.
        return int(float(last.split(",")[0].split()[0])) >= steps - int(COMMON["--reduced_diag_period"])
    except ValueError:
        return False


def core_slots(parallel: int, cores: int, offset: int = 0) -> "queue.Queue[str]":
    """
    Disjoint CPU sets, one per parallel case. The driver sets OMP_PROC_BIND=close, which pins every
    process's threads from core 0 upward; without separate affinity masks, parallel cases share the
    same cores (task 107: 0.87 s/step instead of ~0.1 s/step). Each slot gets cores/2 physical cores
    and their hyperthread siblings (logical CPU n pairs with n + n_physical), starting at physical
    core `offset` (so that two runners can share the machine).
    """
    n_logical = os.cpu_count() or 1
    n_phys = n_logical // 2
    per = max(1, cores // 2)
    slots: "queue.Queue[str]" = queue.Queue()
    for k in range(parallel):
        phys = list(range(offset + k * per, min(offset + (k + 1) * per, n_phys)))
        if not phys:
            raise SystemExit(f"--parallel {parallel} x --cores {cores} exceeds {n_logical} logical CPUs")
        slots.put(",".join(str(c) for c in phys + [c + n_phys for c in phys]))
    return slots


SLOTS: "queue.Queue[str] | None" = None


FIXED = {"gas": "H2", "pressure_torr": 1e-5, "beam": "30 keV, 10 mA DC, a = 2 mm",
         "plasma": "seeded n_e = n_i = f n_b, r <= 3 mm, 0 <= z <= 0.20 m (analytic source estimate)",
         "grid": "32x32x256, x,y in +-10 mm, z in [-0.02, 0.24] m", "solver": "es FFT",
         "dt_s": DT_S, "end_plug": "analytic, width 5 mm, centres 15 mm outside the cell ends"}


def run_case(case: dict, cmd: list[str], out: Path, fixed: dict | None = None) -> tuple[str, int]:
    slot = SLOTS.get() if SLOTS is not None else None
    if slot is not None:
        cmd = ["taskset", "-c", slot] + cmd
    out.mkdir(parents=True, exist_ok=True)
    meta = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": cmd,
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "warpx_source": {"path": str(WARPX_DIR), "git": get_git_info(WARPX_DIR)},
        "case": case,
        "fixed": fixed or FIXED,
    }
    # A restart keeps the original metadata and appends to the log.
    restart = "--restart_from" in cmd
    (out / ("metadata_restart.json" if restart else "metadata.json")).write_text(
        json.dumps(meta, indent=2, default=str))
    with open(out / "run.log", "a" if restart else "w") as log:
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=PROJECT_ROOT).returncode
    print(f"  [{datetime.datetime.now():%H:%M}] {case['case_name']}: exit {rc} (cpus {slot})", flush=True)
    if slot is not None:
        SLOTS.put(slot)
    return case["case_name"], rc


def main() -> int:
    args = parse_args()
    steps = int(round(args.duration_ns * 1e-9 / DT_S))
    cases = [c for c in scan_cases() if not args.only or c["case_name"] in args.only]
    todo = []
    for c in cases:
        out = args.output_dir / c["case_name"]
        if finished(out, steps):
            print(f"  skip {c['case_name']} (finished)")
            continue
        todo.append((c, command(c, out, steps, args.snapshots, args.cores), out))

    print(f"Confinement scan: {len(cases)} cases, {len(todo)} to run, {steps} steps "
          f"({args.duration_ns:.0f} ns), {args.parallel} in parallel")
    if args.dry_run:
        for c, cmd, _ in todo:
            print(f"  {c['case_name']}: {' '.join(cmd[1:])}")
        print("[DRY RUN SUCCESS] nothing written.")
        return 0

    global SLOTS
    SLOTS = core_slots(args.parallel, args.cores)
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        results = list(pool.map(lambda t: run_case(*t), todo))
    failed = [name for name, rc in results if rc != 0]
    print(f"Done: {len(results) - len(failed)} succeeded, {len(failed)} failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
