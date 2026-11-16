#!/usr/bin/env python3
"""
scripts/run_line_section.py

Task CW3 of docs/physics_notes/simulation_strategy_tasks.md: electron retention downstream of the
neutralizer cell, in the main solenoid and quadrupole section of the baseline line
(buncher -> neutralizer -> solenoid -> Q1 -> Q2 -> inflector). Residual-gas compensation plasma is
seeded along the whole section, and the run shows where the electrons stay (eta_downstream for
task CW2).

Section geometry (z from the cell exit, plasma_column.injection_line.InjectionLine defaults, hard
edges, except the solenoid, which has 2 cm tanh edges with the paraxial radial fringe field so that
the beam gets the Busch kick and is focused): drift1 0-0.10 m, solenoid 0.10-0.35 m (0.23 T, matched
uncompensated tune), drift2
0.35-0.45 m, Q1 0.45-0.57 m (-0.28 T/m), drift3 0.57-0.65 m, Q2 0.65-0.77 m (+0.85 T/m).
Domain z in [-0.02, 0.80] m, 32x32x816 (dz 1.0 mm), x,y +-10 mm (pipe), DC 10 mA beam injected
2 mm parallel at z = -0.02 m (the cell-exit beam of CW1 is larger; this is a retention study,
not a transport model).

Cases:
    fields      solenoid + Q1 + Q2
    solenoid    solenoid only (isolates the quadrupoles)
    nofields    no applied fields (field-free pipe reference)

Seeded plasma n_e = n_i = f n_b, r <= 3 mm, 0 <= z <= 0.77 m, T_e = 1 eV (analytic source estimate,
not self-consistent proton-impact ionization; f from the 200 us source model as in production).
H2 at 1e-5 Torr, no MCC (as in the confinement scans), 650 ns. Three cases at once, 4 OpenMP
threads each on physical cores 0-5 (+ hyperthreads); B4 on cores 6-9 (--core_offset 6), within the
22-CPU job budget.

Output: results/line_section/<case>/ (git-ignored). Analysis:
    python scripts/analyze_line_section.py --scan_dir results/line_section

Task B4 (--group b4): the "fields" section with an RF-bunched beam, B_f = 3 and 5.7 (density
bunching at constant velocity at the section entrance; output results/line_section_bunched/).

Usage:
    python scripts/run_line_section.py --dry_run
    python scripts/run_line_section.py --parallel 3 --cores 4
    python scripts/run_line_section.py --group b4 --parallel 2 --cores 4 --core_offset 6
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

ZMIN_M, ZMAX_M, NZ = -0.02, 0.80, 816
SECTION_M = 0.77
SOLENOID = (0.10, 0.35, 0.23)
QUADS = "0.45:0.57:-0.28;0.65:0.77:0.85"
FRINGE_M = 0.02  # tanh solenoid edges with the radial fringe field (Busch kick); quadrupoles hard edge
GROUPS = {  # name: (cases (name, solenoid B [T], quadrupole spec, bunching factor), output subdirectory)
    "cw3": ((("fields", SOLENOID[2], QUADS, 1.0), ("solenoid", SOLENOID[2], "", 1.0), ("nofields", 0.0, "", 1.0)),
            "line_section"),
    # Task B4: the same section with an RF-bunched beam (density bunching at constant velocity, fixed B_f at
    # the section entrance as a stand-in for the bunching that grows along the line; B_f = 5.7 is the
    # inflector value of the sine buncher, task 105).
    "b4": ((("fields_Bf3", SOLENOID[2], QUADS, 3.0), ("fields_Bf5p7", SOLENOID[2], QUADS, 5.7)), "line_section_bunched"),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Electron retention in the solenoid/quadrupole section (task CW3).")
    p.add_argument("--group", choices=sorted(GROUPS), default="cw3", help="cw3: DC beam; b4: bunched beam (task B4).")
    p.add_argument("--output_dir", type=Path, default=None, help="Default: results/<group subdirectory>")
    p.add_argument("--duration_ns", type=float, default=650.0)
    p.add_argument("--snapshots", type=int, default=20)
    p.add_argument("--parallel", type=int, default=3)
    p.add_argument("--cores", type=int, default=6)
    p.add_argument("--core_offset", type=int, default=0, help="First physical core of this runner's CPU slots.")
    p.add_argument("--only", action="append", help="Run only these case names (repeatable).")
    p.add_argument("--dry_run", action="store_true", help="Print the commands and write nothing.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    steps = int(round(args.duration_ns * 1e-9 / rcs.DT_S))
    common = {**rcs.COMMON, "--nz": str(NZ), "--zmin": repr(ZMIN_M), "--zmax": repr(ZMAX_M),
              "--column_zmin": "0.0", "--column_length": repr(SECTION_M),
              "--solenoid_zmin": repr(SOLENOID[0]), "--solenoid_zmax": repr(SOLENOID[1]),
              "--solenoid_fringe": repr(FRINGE_M)}
    fixed = {**rcs.FIXED,
             "plasma": f"seeded n_e = n_i = f n_b, r <= 3 mm, 0 <= z <= {SECTION_M} m (analytic source estimate)",
             "grid": f"32x32x{NZ}, x,y in +-10 mm, z in [{ZMIN_M}, {ZMAX_M}] m",
             "section": "drift1 0-0.10, solenoid 0.10-0.35 (0.23 T, 2 cm tanh edges with radial fringe), drift2, "
                        "Q1 0.45-0.57 (-0.28 T/m), drift3, Q2 0.65-0.77 (+0.85 T/m); hard-edge quadrupoles",
             "end_plug": "none"}
    todo = []
    cases, subdir = GROUPS[args.group]
    out_root = args.output_dir or PROJECT_ROOT / "results" / subdir
    for name, bz, quads, bf in cases:
        if args.only and name not in args.only:
            continue
        case = {"case_name": name, "solenoid_Bz_T": bz, "electron_temperature_eV": 1.0, "end_plug_voltage_V": 0.0,
                "quadrupoles": quads, "beam_bunching_factor": bf}
        out = out_root / name
        if rcs.finished(out, steps):
            print(f"  skip {name} (finished)")
            continue
        cmd = rcs.command(case, out, steps, args.snapshots, args.cores, common)
        if quads:
            cmd += ["--quadrupoles", quads]
        if bf > 1.0:
            cmd += ["--beam_bunching_factor", repr(bf)]
        todo.append((case, cmd, out))

    print(f"Line section ({args.group}): {len(todo)} to run, {steps} steps ({args.duration_ns:.0f} ns), "
          f"{args.parallel} in parallel x {args.cores} threads")
    if args.dry_run:
        for c, cmd, _ in todo:
            print(f"  {c['case_name']}: {' '.join(cmd[1:])}")
        print("[DRY RUN SUCCESS] nothing written.")
        return 0

    rcs.SLOTS = rcs.core_slots(args.parallel, args.cores, args.core_offset)
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        results = list(pool.map(lambda t: rcs.run_case(*t, fixed=fixed), todo))
    failed = [n for n, rc in results if rc != 0]
    print(f"Done: {len(results) - len(failed)} succeeded, {len(failed)} failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
