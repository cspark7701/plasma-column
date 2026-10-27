#!/usr/bin/env python3
"""
scripts/analyze_beam_quality.py

Effect of the plasma-column settings (cell solenoid B_z, end plugs, seed T_e) on the beam
(task C3 of docs/physics_notes/simulation_strategy_tasks.md).

For every case of a scan directory (results/confinement_scan/ by default, or the plug scan of
task C4), the beam_protons particles of the late snapshots (t >= --from_fraction * t_end) are
binned in z-slabs and the weighted rms size, divergence, normalized rms emittance and mean
kinetic energy are averaged over the snapshots (plasma_column.beam_quality).

Slabs [m]: injection (zmin to zmin + 3 mm), mid-cell 0.09–0.11, cell end 0.18–0.20, and exit
(from 3 plug widths past the downstream plug centre, at least 0.225 m, to zmax - 2 mm).

Caveat: in the default 32x32x256 domain (zmin = -0.02 m) the upstream plug centre (-0.015 m) is
5 mm from the injection plane, so the beam is injected inside the plug potential and sees only
half of the upstream plug lens; the beam then enters the cell about 0.18 keV low at 300 V. This
is a geometry artifact, corrected in the plug scan (task C4) with zmin = -0.05 m.

Outputs (default <scan_dir>/analysis/, git-ignored):
    beam_quality.csv / .json
    beam_quality_exit.{png,pdf}

Usage:
    python scripts/analyze_beam_quality.py --dry_run
    python scripts/analyze_beam_quality.py
    python scripts/analyze_beam_quality.py --scan_dir results/plug_scan
"""

from __future__ import annotations

import argparse
import json
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

from plasma_column.beam_quality import load_beam_particles, slab_beam_moments
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.warpx_io import find_plotfiles


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Beam rms size, divergence and emittance per case and z-slab.")
    p.add_argument("--scan_dir", type=Path, default=PROJECT_ROOT / "results" / "confinement_scan")
    p.add_argument("--output_dir", type=Path, default=None, help="Default: <scan_dir>/analysis")
    p.add_argument("--from_fraction", type=float, default=0.5, help="Average snapshots with t >= this * t_end.")
    p.add_argument("--dry_run", action="store_true", help="List cases and snapshots; write nothing.")
    return p.parse_args()


def case_domain(meta: dict) -> tuple[float, float]:
    """zmin, zmax of a case from its command line (driver defaults -0.02, 0.24 m)."""
    cmd = meta.get("command_line", [])
    vals = {"--zmin": -0.02, "--zmax": 0.24}
    for k in vals:
        if k in cmd:
            vals[k] = float(cmd[cmd.index(k) + 1])
    return vals["--zmin"], vals["--zmax"]


def slabs(zmin: float, zmax: float, case: dict) -> dict[str, tuple[float, float]]:
    """z-slabs; the exit slab starts 3 plug widths past the downstream plug centre (at least 0.225 m)."""
    w = case.get("end_plug_width_m", 0.005)
    exit_start = max(0.225, 0.20 + case.get("end_plug_offset_m", 0.015) + 3.0 * w)
    exit_start = min(exit_start, zmax - 0.006)
    return {"injection": (zmin, zmin + 0.003), "mid_cell": (0.09, 0.11), "cell_end": (0.18, 0.20),
            "exit": (exit_start, zmax - 0.002)}


def main() -> int:
    args = parse_args()
    out = args.output_dir or args.scan_dir / "analysis"
    case_dirs = sorted(p for p in args.scan_dir.iterdir() if (p / "metadata.json").exists())
    if args.dry_run:
        for c in case_dirs:
            print(f"  {c.name:28s} snapshots: {len(find_plotfiles(c))}")
        print("[DRY RUN SUCCESS] nothing written.")
        return 0

    rows = []
    for c in case_dirs:
        meta = json.loads((c / "metadata.json").read_text())
        plotfiles = find_plotfiles(c)
        if not plotfiles:
            continue
        parts = [load_beam_particles(p) for p in plotfiles]
        t_end = max(p["time"] for p in parts)
        late = [p for p in parts if p["time"] >= args.from_fraction * t_end]
        for name, (z0, z1) in slabs(*case_domain(meta), meta["case"]).items():
            m = pd.DataFrame([slab_beam_moments(p, z0, z1) for p in late]).mean()
            rows.append({"case_name": c.name, **meta["case"], "slab": name, "z_min_m": z0, "z_max_m": z1,
                         "n_snapshots": len(late), **m.to_dict()})
        print(f"  {c.name}: {len(late)} snapshots", flush=True)
    df = pd.DataFrame(rows)
    df["eps_n_rms_mm_mrad"] = 0.5 * (df.eps_n_rms_x_mm_mrad + df.eps_n_rms_y_mm_mrad)
    df["r_rms_mm"] = np.hypot(df.x_rms_mm, df.y_rms_mm)
    df["rp_rms_mrad"] = np.hypot(df.xp_rms_mrad, df.yp_rms_mrad)

    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "beam_quality.csv", index=False, float_format="%.6g")
    (out / "beam_quality.json").write_text(json.dumps(
        {"from_fraction": args.from_fraction, "rows": df.to_dict(orient="records")}, indent=2, default=str))
    ex = df[df.slab == "exit"].set_index("case_name")
    print(ex[["r_rms_mm", "rp_rms_mrad", "eps_n_rms_mm_mrad", "kinetic_energy_keV"]].to_string(float_format="%.4g"))

    setup_publication_style()
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    x = np.arange(len(ex))
    for ax, col, label in zip(axes, ("r_rms_mm", "rp_rms_mrad", "eps_n_rms_mm_mrad"),
                              (r"$r_{\rm rms}$ [mm]", r"$r'_{\rm rms}$ [mrad]",
                               r"$\varepsilon_{n,\rm rms}$ [$\pi$ mm mrad]")):
        ax.bar(x, ex[col], color=["tab:blue" if v > 0 else "0.6" for v in ex.get("end_plug_voltage_V", 0 * x)])
        ax.set_xticks(x, ex.index, rotation=70, fontsize=7)
        ax.set_ylabel(label)
    axes[0].set_title("beam at the cell exit (blue: plugs on)", fontsize=10)
    fig.tight_layout()
    save_figure(fig, out / "beam_quality_exit")
    plt.close(fig)
    print(f"Wrote {out}/beam_quality.csv and figure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
