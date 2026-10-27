#!/usr/bin/env python3
"""
scripts/run_plug_scan.py

End-plug voltage and width scan around the confinement-scan optimum (task C4 of
docs/physics_notes/simulation_strategy_tasks.md). Seeded H2 at 1e-5 Torr, DC 10 mA beam, 650 ns,
small grid, same time step as production and the confinement scan.

Cases (cell B_z and seed T_e fixed at the values chosen from task C1):
    plug0           no plugs (reference in this domain)
    V300_w5         300 V, width 5 mm (the confinement-scan setting, without the injection artifact)
    V100_w10        100 V, width 10 mm
    V300_w10        300 V, width 10 mm
    V100_w20        100 V, width 20 mm
    V300_w20        300 V, width 20 mm
Each plug centre sits 3 widths outside the cell end, so the plug potential at the cell ends is
exp(-4.5) = 1.1% of V for every width.

Why wider plugs: in the confinement scan the 5 mm plugs shortened tau_c about 4x. Their radial
field comes from the paraxial expansion E_r = (r/2) phi''(z), about V r / (2 w^2) (6 MV/m at
r = 1 mm for 300 V, 5 mm), which is only valid for r << w; a real electrode with a ~10 mm
aperture gives a potential at least ~10 mm wide.

Domain: z in [-0.12, 0.32] m with nz = 432 (dz = 1.02 mm, as in the confinement scan), so the beam
is injected 3 widths outside the upstream plug for every width. In the confinement scan (z from
-0.02 m) the upstream plug centre was 5 mm from the injection plane (artifact, see
scripts/analyze_beam_quality.py).

All 6 cases run at once, 4 OpenMP threads each on separate physical cores (2 + hyperthreads).

The seeded plasma is an analytic source estimate (prescribed n_e = n_i at t = 0), not
self-consistent proton-impact ionization. The plugs are an analytic applied potential, not
electrode surfaces.

Output: results/plug_scan/<case>/ (git-ignored). Analysis:
    python scripts/analyze_confinement_scan.py --scan_dir results/plug_scan
    python scripts/analyze_beam_quality.py --scan_dir results/plug_scan

Usage:
    python scripts/run_plug_scan.py --dry_run --solenoid_Bz 0.15 --electron_temperature_eV 1
    python scripts/run_plug_scan.py --solenoid_Bz 0.15 --electron_temperature_eV 1
"""

from __future__ import annotations

import argparse
import queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

import run_confinement_scan as rcs

ZMIN_M, ZMAX_M, NZ = -0.12, 0.32, 432
PLUGS = (  # (name, voltage V, width m)
    ("plug0", 0.0, 0.005),
    ("V300_w5", 300.0, 0.005),
    ("V100_w10", 100.0, 0.010),
    ("V300_w10", 300.0, 0.010),
    ("V100_w20", 100.0, 0.020),
    ("V300_w20", 300.0, 0.020),
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="End-plug voltage/width scan of the seeded plasma column.")
    p.add_argument("--solenoid_Bz", type=float, required=True, help="Cell B_z [T] chosen from task C1.")
    p.add_argument("--electron_temperature_eV", type=float, required=True, help="Seed T_e chosen from task C1.")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "plug_scan")
    p.add_argument("--duration_ns", type=float, default=650.0)
    p.add_argument("--snapshots", type=int, default=20)
    p.add_argument("--parallel", type=int, default=6)
    p.add_argument("--cores", type=int, default=4)
    p.add_argument("--only", action="append", help="Run only these case names (repeatable).")
    p.add_argument("--dry_run", action="store_true", help="Print the commands and write nothing.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    steps = int(round(args.duration_ns * 1e-9 / rcs.DT_S))
    common = {**rcs.COMMON, "--nz": str(NZ), "--zmin": repr(ZMIN_M), "--zmax": repr(ZMAX_M)}
    fixed = {**rcs.FIXED,
             "grid": f"32x32x{NZ}, x,y in +-10 mm, z in [{ZMIN_M}, {ZMAX_M}] m",
             "end_plug": "analytic Gaussian potential, centres 3 widths outside the cell ends"}
    todo = []
    for name, volts, width in PLUGS:
        if args.only and name not in args.only:
            continue
        case = {"case_name": name, "solenoid_Bz_T": args.solenoid_Bz,
                "electron_temperature_eV": args.electron_temperature_eV,
                "end_plug_voltage_V": volts, "end_plug_width_m": width, "end_plug_offset_m": 3.0 * width}
        out = args.output_dir / name
        if rcs.finished(out, steps):
            print(f"  skip {name} (finished)")
            continue
        todo.append((case, rcs.command(case, out, steps, args.snapshots, args.cores, common), out))

    print(f"Plug scan: B_z = {args.solenoid_Bz} T, T_e = {args.electron_temperature_eV} eV, "
          f"{len(todo)} to run, {steps} steps ({args.duration_ns:.0f} ns), {args.parallel} in parallel")
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
