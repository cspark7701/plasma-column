#!/usr/bin/env python3
"""
scripts/run_cw_best_config.py

Task CW1 of docs/physics_notes/simulation_strategy_tasks.md: the best cell configuration from the
confinement and plug scans (tasks C1, C4) on the production grid resolution, DC 10 mA beam,
seeded H2 at 1e-5 Torr, 650 ns (3x the 218 ns production runs).

Numerics match production (cases/baseline_h2.yaml): ES FFT solver, dt = 9.476 ps, nppc_beam 4,
nppc_plasma 16, electron-impact MCC on the H2 background, dz = 0.51 mm. The z domain is extended
to [-0.07, 0.27] m (nz = 672) so the beam is injected 4 widths outside the upstream plug centre
for plugs up to 10 mm wide (centre 3 widths outside the cell end); wider plugs need a longer
domain (checked below). Checkpoints every quarter of the run; extend later with
    --duration_ns <longer> --restart_from <checkpoint>.

The seeded plasma is an analytic source estimate (prescribed n_e = n_i at t = 0), not
self-consistent proton-impact ionization. The plugs are an analytic applied potential, not
electrode surfaces.

Output: results/cw_best_config/<case>/ (git-ignored). Analysis:
    python scripts/analyze_confinement_scan.py --scan_dir results/cw_best_config
    python scripts/analyze_beam_quality.py --scan_dir results/cw_best_config

Usage:
    python scripts/run_cw_best_config.py --dry_run --solenoid_Bz 0.15 --electron_temperature_eV 1 \\
        --end_plug_voltage 300 --end_plug_width 0.010
    python scripts/run_cw_best_config.py --solenoid_Bz 0.15 --electron_temperature_eV 1 \\
        --end_plug_voltage 300 --end_plug_width 0.010 --cores 24
The configuration (0.15 T, 1 eV seed, 300 V / 10 mm plugs) is the choice of task 109.
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

import run_confinement_scan as rcs

ZMIN_M, ZMAX_M, NX, NZ = -0.07, 0.27, 64, 672
COMMON = {
    "--gas": "H2", "--pressure_torr": "1e-5", "--neutralization": "-1",
    "--solver": "es", "--dt": repr(rcs.DT_S),
    "--nx": str(NX), "--ny": str(NX), "--nz": str(NZ), "--zmin": repr(ZMIN_M), "--zmax": repr(ZMAX_M),
    "--nppc_beam": "4", "--nppc_plasma": "16",
    "--reduced_diag_period": "50", "--mcc": "electron_impact",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Best confinement configuration on the production grid (CW1).")
    p.add_argument("--solenoid_Bz", type=float, required=True)
    p.add_argument("--electron_temperature_eV", type=float, required=True)
    p.add_argument("--end_plug_voltage", type=float, required=True)
    p.add_argument("--end_plug_width", type=float, default=0.005)
    p.add_argument("--case_name", default=None, help="Default: built from the settings.")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "cw_best_config")
    p.add_argument("--duration_ns", type=float, default=650.0)
    p.add_argument("--snapshots", type=int, default=20)
    p.add_argument("--cores", type=int, default=24, help="OpenMP threads (all logical CPUs by default).")
    p.add_argument("--restart_from", default=None, help="Checkpoint to continue from.")
    p.add_argument("--dry_run", action="store_true", help="Print the command and write nothing.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    steps = int(round(args.duration_ns * 1e-9 / rcs.DT_S))
    name = args.case_name or (f"B{rcs.tag(args.solenoid_Bz)}_Te{rcs.tag(args.electron_temperature_eV)}"
                              f"_V{rcs.tag(args.end_plug_voltage)}_w{rcs.tag(args.end_plug_width * 1e3)}mm")
    case = {"case_name": name, "solenoid_Bz_T": args.solenoid_Bz,
            "electron_temperature_eV": args.electron_temperature_eV,
            "end_plug_voltage_V": args.end_plug_voltage, "end_plug_width_m": args.end_plug_width,
            "end_plug_offset_m": 3.0 * args.end_plug_width}
    if ZMIN_M > -7.0 * args.end_plug_width:
        raise SystemExit(f"--end_plug_width {args.end_plug_width} m needs zmin <= {-7 * args.end_plug_width} m")
    out = args.output_dir / name
    cmd = rcs.command(case, out, steps, args.snapshots, args.cores, COMMON)
    cmd[cmd.index("--checkpoint_period") + 1] = str(steps // 4)
    if args.restart_from:
        # Absolute: the driver changes into the output directory before reading the checkpoint.
        cmd += ["--restart_from", str(Path(args.restart_from).resolve())]
    print(f"CW1: {name}, {steps} steps ({args.duration_ns:.0f} ns), {args.cores} threads")
    if args.dry_run:
        print("  " + " ".join(cmd[1:]))
        print("[DRY RUN SUCCESS] nothing written.")
        return 0
    fixed = {**rcs.FIXED, "grid": f"{NX}x{NX}x{NZ}, x,y in +-10 mm, z in [{ZMIN_M}, {ZMAX_M}] m",
             "numerics": "production: nppc_beam 4, nppc_plasma 16, electron-impact MCC",
             "end_plug": "analytic Gaussian potential, centres 3 widths outside the cell ends"}
    _, rc = rcs.run_case(case, cmd, out, fixed=fixed)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
