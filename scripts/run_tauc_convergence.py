#!/usr/bin/env python3
"""
scripts/run_tauc_convergence.py

Task 123: numerical convergence of the PIC electron confinement time tau_c. The test-electron model
(task 114) keeps electrons in the plugged trap for 100 us, while PIC gives tau_c = 4.2 us on the
production grid (task 111) and 7.2 us on the coarser plug-scan grid (task 109). The cause is
collective or numerical. The Debye length of a 1 eV seed at the beam density (~0.17 mm) is
smaller than the cell size (0.31 mm at 64x64, 0.63 mm at 32x32), so grid heating is a candidate.

Physics as CW1 (scripts/run_cw_best_config.py): seeded H2 at 1e-5 Torr, 0.15 T cell solenoid,
1 eV seed, 300 V / 10 mm end plugs (centres 30 mm outside the cell ends), DC 10 mA beam, ES FFT
solver, z in [-0.07, 0.27] m, x, y in +-10 mm, 650 ns. Each case changes one numerical parameter:

    g32_p4        32x32x336, nppc_plasma 4             (coarse reference)
    g32_p16       32x32x336, nppc_plasma 16
    g32_p64       32x32x336, nppc_plasma 64
    g32_p16_dt2   32x32x336, nppc_plasma 16, dt / 2
    g32_p4_nomcc  32x32x336, nppc_plasma 4, no e-impact MCC  (plug-scan numerics, task 109)
    g48_p16       48x48x504, nppc_plasma 16
    g64_p32       64x64x672, nppc_plasma 32            (production grid; nppc 16 = CW1, task 111)

nppc_beam is 4 everywhere, as in production. The CW1 run is the 64x64x672 / nppc 16 point
(refit over the same 325-650 ns window in the analysis).

Groups (run both at once; CPUs 11 and 23 stay free for analysis):
    --group small  6 cases, 4 at a time, 2 physical cores + hyperthreads each (CPUs 0-7, 12-19)
    --group large  g64_p32 on 3 physical cores + hyperthreads (CPUs 8-10, 20-22)

The seeded plasma is an analytic source estimate, not self-consistent proton-impact ionization.

Output: results/tauc_convergence/<case>/ (git-ignored). Analysis:
    python scripts/analyze_confinement_scan.py --scan_dir results/tauc_convergence

Usage:
    python scripts/run_tauc_convergence.py --dry_run
    python scripts/run_tauc_convergence.py --group small &
    python scripts/run_tauc_convergence.py --group large &
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

ZMIN_M, ZMAX_M = -0.07, 0.27
PHYSICS = {"solenoid_Bz_T": 0.15, "electron_temperature_eV": 1.0, "end_plug_voltage_V": 300.0,
           "end_plug_width_m": 0.010, "end_plug_offset_m": 0.030}
# name: (nx = ny, nz, nppc_plasma, dt factor, mcc)
CASES = {
    "g32_p4": (32, 336, 4, 1.0, "electron_impact"),
    "g32_p16": (32, 336, 16, 1.0, "electron_impact"),
    "g32_p64": (32, 336, 64, 1.0, "electron_impact"),
    "g32_p16_dt2": (32, 336, 16, 0.5, "electron_impact"),
    "g32_p4_nomcc": (32, 336, 4, 1.0, "none"),
    "g48_p16": (48, 504, 16, 1.0, "electron_impact"),
    "g64_p32": (64, 672, 32, 1.0, "electron_impact"),
}
GROUPS = {  # cases, parallel, OpenMP threads per case, first physical core
    "small": (("g32_p64", "g48_p16", "g32_p16_dt2", "g32_p16", "g32_p4", "g32_p4_nomcc"), 4, 4, 0),
    "large": (("g64_p32",), 1, 6, 8),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convergence of the PIC electron confinement time (task 123).")
    p.add_argument("--group", choices=sorted(GROUPS), action="append",
                   help="Case group to run (repeatable; default: all groups in dry-run, required otherwise).")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "tauc_convergence")
    p.add_argument("--duration_ns", type=float, default=650.0)
    p.add_argument("--snapshots", type=int, default=20)
    p.add_argument("--dry_run", action="store_true", help="Print the commands and write nothing.")
    return p.parse_args()


def case_command(name: str, out: Path, duration_ns: float, snapshots: int, cores: int) -> tuple[dict, list[str], int]:
    n, nz, nppc, dt_factor, mcc = CASES[name]
    dt = rcs.DT_S * dt_factor
    steps = int(round(duration_ns * 1e-9 / dt))
    common = {**rcs.COMMON, "--dt": repr(dt), "--nx": str(n), "--ny": str(n), "--nz": str(nz),
              "--zmin": repr(ZMIN_M), "--zmax": repr(ZMAX_M), "--nppc_beam": "4",
              "--nppc_plasma": str(nppc), "--mcc": mcc,
              "--reduced_diag_period": str(int(50 / dt_factor))}
    case = {"case_name": name, **PHYSICS, "nx": n, "nz": nz, "nppc_plasma": nppc, "dt_s": dt, "mcc": mcc}
    return case, rcs.command(case, out, steps, snapshots, cores, common), steps


def main() -> int:
    args = parse_args()
    groups = args.group or (sorted(GROUPS) if args.dry_run else None)
    if not groups:
        raise SystemExit("--group small and/or --group large is required (use --dry_run to list).")
    rc_all = 0
    for g in groups:
        names, parallel, cores, offset = GROUPS[g]
        todo = []
        for name in names:
            out = args.output_dir / name
            case, cmd, steps = case_command(name, out, args.duration_ns, args.snapshots, cores)
            if rcs.finished(out, steps):
                print(f"  skip {name} (finished)")
                continue
            todo.append((case, cmd, out, steps))
        slots = rcs.core_slots(parallel, cores, offset)
        print(f"tau_c convergence, group {g}: {len(todo)} cases, {parallel} at a time, {cores} threads each, "
              f"CPU sets {list(slots.queue)}")
        if args.dry_run:
            for case, cmd, _, steps in todo:
                print(f"  {case['case_name']}: {steps} steps; {' '.join(cmd[1:])}")
            continue
        rcs.SLOTS = slots
        fixed = {**rcs.FIXED, "grid": f"see case; x,y in +-10 mm, z in [{ZMIN_M}, {ZMAX_M}] m",
                 "numerics": "convergence study: nppc_beam 4; nx, nz, nppc_plasma, dt, mcc per case",
                 "end_plug": "analytic Gaussian potential, 300 V, width 10 mm, centres 30 mm outside the cell ends"}
        with ThreadPoolExecutor(max_workers=parallel) as pool:
            results = list(pool.map(lambda t: rcs.run_case(t[0], t[1], t[2], fixed=fixed), todo))
        failed = [n for n, rc in results if rc != 0]
        print(f"Group {g} done: {len(results) - len(failed)} succeeded, {len(failed)} failed {failed}")
        rc_all |= bool(failed)
    if args.dry_run:
        print("[DRY RUN SUCCESS] nothing written.")
    return int(rc_all)


if __name__ == "__main__":
    raise SystemExit(main())
