#!/usr/bin/env python3
"""
scripts/run_bunched_cell.py

RF-bunched beam in the plasma cell (task B2 of docs/physics_notes/simulation_strategy_tasks.md).
Seeded H2 at 1e-5 Torr, 10 mA average current, 50 MHz, periodic von Mises current profile at
injection (density bunching at constant velocity), 650 ns (32 RF periods), small grid.

Cases:
    trap_Bf1        0.15 T, 1 eV seed, -300 V / 10 mm plugs, DC beam (reference in this domain)
    trap_Bf1p3      same trap, B_f = 1.3 (baseline bunching in the cell, task 105)
    trap_Bf5        same trap, B_f = 5 (bunch-focus study: the bunch focus moved into the cell;
                    labeled, not the baseline layout)
    open_Bf1p3      0 T, no plugs, B_f = 1.3
    open_Bf5        0 T, no plugs, B_f = 5 (bunch-focus study)
The trap is the CW1 configuration (tasks 109, 111); the domain z in [-0.07, 0.27] m is that of
CW1, with dz = 1.01 mm as in the confinement and plug scans.

The seeded plasma is an analytic source estimate (prescribed n_e = n_i at t = 0, scaled to the
average beam density), not self-consistent proton-impact ionization. The plugs are an analytic
applied potential, not electrode surfaces.

Five cases at once, 4 OpenMP threads each on separate physical cores 0-9 (+ hyperthreads), within
the 22-CPU budget for jobs (CPUs 11 and 23 stay free).

Output: results/bunched_cell/<case>/ (git-ignored). Analysis:
    python scripts/analyze_bunched_cell.py --scan_dir results/bunched_cell
    python scripts/analyze_confinement_scan.py --scan_dir results/bunched_cell

Usage:
    python scripts/run_bunched_cell.py --dry_run
    python scripts/run_bunched_cell.py
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

import run_confinement_scan as rcs

ZMIN_M, ZMAX_M, NZ = -0.07, 0.27, 336
TRAP = {"solenoid_Bz_T": 0.15, "electron_temperature_eV": 1.0, "end_plug_voltage_V": 300.0,
        "end_plug_width_m": 0.010, "end_plug_offset_m": 0.030}
OPEN = {"solenoid_Bz_T": 0.0, "electron_temperature_eV": 1.0, "end_plug_voltage_V": 0.0}
CASES = (  # (name, cell settings, bunching factor)
    ("trap_Bf1", TRAP, 1.0),
    ("trap_Bf1p3", TRAP, 1.3),
    ("trap_Bf5", TRAP, 5.0),
    ("open_Bf1p3", OPEN, 1.3),
    ("open_Bf5", OPEN, 5.0),
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RF-bunched beam in the plasma cell (task B2).")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "bunched_cell")
    p.add_argument("--duration_ns", type=float, default=650.0)
    p.add_argument("--snapshots", type=int, default=40)
    p.add_argument("--parallel", type=int, default=5)
    p.add_argument("--cores", type=int, default=4)
    p.add_argument("--only", action="append", help="Run only these case names (repeatable).")
    p.add_argument("--dry_run", action="store_true", help="Print the commands and write nothing.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    steps = int(round(args.duration_ns * 1e-9 / rcs.DT_S))
    common = {**rcs.COMMON, "--nz": str(NZ), "--zmin": repr(ZMIN_M), "--zmax": repr(ZMAX_M)}
    fixed = {**rcs.FIXED,
             "beam": "30 keV, 10 mA average, a = 2 mm, 50 MHz von Mises current profile (36 deg acceptance)",
             "grid": f"32x32x{NZ}, x,y in +-10 mm, z in [{ZMIN_M}, {ZMAX_M}] m",
             "end_plug": "trap cases: analytic Gaussian, -300 V, w = 10 mm, centres 30 mm outside the cell ends"}
    todo = []
    for name, cell, bf in CASES:
        if args.only and name not in args.only:
            continue
        case = {"case_name": name, **cell, "beam_bunching_factor": bf,
                "bunch_focus_study": bf > 2.0}
        out = args.output_dir / name
        if rcs.finished(out, steps):
            print(f"  skip {name} (finished)")
            continue
        cmd = rcs.command(case, out, steps, args.snapshots, args.cores, common)
        cmd += ["--beam_bunching_factor", repr(bf)]
        todo.append((case, cmd, out))

    print(f"Bunched cell: {len(todo)} to run, {steps} steps ({args.duration_ns:.0f} ns), "
          f"{args.parallel} in parallel x {args.cores} threads")
    if args.dry_run:
        for c, cmd, _ in todo:
            print(f"  {c['case_name']}: {' '.join(cmd[1:])}")
        print("[DRY RUN SUCCESS] nothing written.")
        return 0

    rcs.SLOTS = rcs.core_slots(args.parallel, args.cores)
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        results = list(pool.map(lambda t: rcs.run_case(*t, fixed=fixed), todo))
    failed = [n for n, rc in results if rc != 0]
    print(f"Done: {len(results) - len(failed)} succeeded, {len(failed)} failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
