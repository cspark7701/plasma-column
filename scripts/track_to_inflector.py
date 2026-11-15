#!/usr/bin/env python3
"""
scripts/track_to_inflector.py

Task CW5 of docs/physics_notes/simulation_strategy_tasks.md: particle tracking of the DC beam from
the plasma cell through drift / solenoid / Q1 / Q2 to the inflector (plasma_column.particle_tracking),
replacing the KV transmission estimate by counted particles.

Part A, model beams (launch 2 mm, parallel, at the cell entrance; eta_cell = 0.91 from CW1):
    KV and Gaussian beams of the same rms, 0.25 and 0.5 pi mm mrad (edge, normalized),
    eta_down = 0, 0.5, 0.7, 0.9 with the optics matched in task CW2 (envelope model).
    KV vs envelope checks the tracker; Gaussian vs KV shows the effect of tails.
Part B, PIC beams at the cell exit (z = 0.20 m), eta_down = 0.5, 0.7, 0.9, optics rematched by
tracking (differential evolution on the counted transmission, warm start from CW2):
    cw1      CW1 production-grid run (0.15 T, 300 V / 10 mm plugs; beam injected 7 cm before the
             cell, task 111), cell-end slab
    c1_short confinement scan B0p15_Te1_plug0 (injection 2 cm before the cell, no plugs, task 107)
The PIC particles of the last snapshots in z = 0.18-0.20 m are projected to z = 0.20 m. The PIC cell
solenoid is a hard-edge B_z without radial fringe field (tasks <= 111), so the beam got no Busch
rotation and the cell solenoid did not focus it; its residual mean rotation (from space-charge
expansion turned by B_z) is removed as a rigid rotation, giving zero mean angular momentum as
after a real solenoid exit. Sampled to N particles with probability proportional to weight.

Outputs (default results/track_to_inflector/, git-ignored):
    track_summary.csv / .json, track_rms.csv, track_to_inflector.{png,pdf}

Usage:
    python scripts/track_to_inflector.py --dry_run
    python scripts/track_to_inflector.py --processes 2
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.beam_quality import load_beam_particles
from plasma_column.injection_line import InjectionLine
from plasma_column.particle_tracking import gaussian_beam, kv_beam, rms_emittance_m_rad, track
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.transport import Optics, TransportBeam
from plasma_column.warpx_io import find_plotfiles, get_git_info

ETA_CELL = 0.91
CW2_CSV = PROJECT_ROOT / "results" / "transmission_vs_downstream" / "transmission_vs_downstream.csv"
PIC_INPUTS = {"cw1": PROJECT_ROOT / "results" / "cw_best_config" / "B0p15_Te1_V300_w10mm",
              "c1_short": PROJECT_ROOT / "results" / "confinement_scan" / "B0p15_Te1_plug0"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Particle tracking to the inflector (task CW5).")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "track_to_inflector")
    p.add_argument("--n_particles", type=int, default=20_000)
    p.add_argument("--n_match", type=int, default=3000, help="Particles per tracking during the rematch.")
    p.add_argument("--match_maxiter", type=int, default=15)
    p.add_argument("--snapshots", type=int, default=3, help="Last PIC snapshots pooled for the input beam.")
    p.add_argument("--processes", type=int, default=2)
    p.add_argument("--dry_run", action="store_true", help="List the cases; write nothing.")
    return p.parse_args()


def cw2_optics(eps_pi: float, eta_down: float) -> Optics:
    d = pd.read_csv(CW2_CSV)
    r = d.iloc[((d.emittance_n_edge_pi_mm_mrad - eps_pi).abs() + (d.eta_downstream - eta_down).abs()).argmin()]
    return Optics(r.solenoid_B_T, r.q1_gradient_Tm, r.q2_gradient_Tm)


def pic_beam(case_dir: Path, n: int, snapshots: int, rigidity_Tm: float) -> tuple[tuple[np.ndarray, ...], dict]:
    parts = []
    for plt_path in find_plotfiles(case_dir)[-snapshots:]:
        p = load_beam_particles(plt_path)
        m = (p["z"] >= 0.18) & (p["z"] < 0.20)
        parts.append({k: p[k][m] for k in ("x", "y", "z", "px", "py", "pz", "w")})
    q = {k: np.concatenate([d[k] for d in parts]) for k in parts[0]}
    rng = np.random.default_rng(5)
    idx = rng.choice(q["w"].size, size=n, replace=True, p=q["w"] / q["w"].sum())
    xp, yp = q["px"][idx] / q["pz"][idx], q["py"][idx] / q["pz"][idx]
    dz = 0.20 - q["z"][idx]
    x, y = q["x"][idx] + xp * dz, q["y"][idx] + yp * dz
    # Remove the mean mechanical angular momentum as a rigid rotation (see the module docstring).
    L0 = np.mean(x * yp - y * xp)
    omega = L0 / np.mean(x**2 + y**2)
    xp, yp = xp + omega * y, yp - omega * x
    info = {"n_pic_macro": int(q["w"].size), "L_before_mm_mrad": L0 * 1e6, "L_after_mm_mrad": float(np.mean(x * yp - y * xp)) * 1e6,
            "x_rms_mm": float(np.std(x) * 1e3), "xp_rms_mrad": float(np.std(xp) * 1e3),
            "eps_rms_x_mm_mrad": rms_emittance_m_rad(x, xp) * 1e6, "eps_rms_y_mm_mrad": rms_emittance_m_rad(y, yp) * 1e6}
    return (x, xp, y, yp), info


def part_a(task: tuple) -> dict:
    dist, eps_pi, eta_down, n = task
    line, tb = InjectionLine(), TransportBeam(emittance_n_edge_m_rad=eps_pi * 1e-6)
    gen = kv_beam if dist == "kv" else gaussian_beam
    beam = gen(n, tb.r0_m, tb.emittance_geom_m_rad)
    optics = cw2_optics(eps_pi, eta_down)
    r = track(*beam, line, optics, tb.rigidity_Tm, tb.proton.perveance_K0, ETA_CELL, eta_down)
    d = pd.read_csv(CW2_CSV)
    t_env = d[np.isclose(d.emittance_n_edge_pi_mm_mrad, eps_pi) & np.isclose(d.eta_downstream, eta_down)].T_total.iloc[0]
    print(f"  A {dist:8s} eps {eps_pi:.2f} eta_down {eta_down:.1f}: T = {r['T_total']:.3f} (envelope {t_env:.3f})", flush=True)
    return {"part": "A", "beam": dist, "emittance_n_edge_pi_mm_mrad": eps_pi, "eta_downstream": eta_down,
            "solenoid_B_T": optics.solenoid_B_T, "q1_gradient_Tm": optics.q1_gradient_Tm, "q2_gradient_Tm": optics.q2_gradient_Tm,
            "T_pipe": r["T_pipe"], "T_aperture": r["T_aperture"], "T_total": r["T_total"], "T_envelope": t_env,
            "z_m": r["z_m"].tolist(), "x_rms_mm": r["x_rms_mm"].tolist(), "y_rms_mm": r["y_rms_mm"].tolist()}


def part_b(task: tuple) -> dict:
    name, eta_down, n, n_match, maxiter, snapshots = task
    line, tb = InjectionLine(), TransportBeam()
    beam, info = pic_beam(PIC_INPUTS[name], n, snapshots, tb.rigidity_Tm)
    K0 = tb.proton.perveance_K0
    sub = tuple(a[:n_match] for a in beam)
    start = cw2_optics(0.5, eta_down)

    def cost(v: np.ndarray) -> float:
        return -track(*sub, line, Optics(*v), tb.rigidity_Tm, K0, ETA_CELL, eta_down, z_start_m=0.20,
                      record_every=10_000)["T_total"]

    x0 = np.clip([start.solenoid_B_T, start.q1_gradient_Tm, start.q2_gradient_Tm], [0, -1.5, -1.5], [0.6, 1.5, 1.5])
    res = differential_evolution(cost, ((0.0, 0.6), (-1.5, 1.5), (-1.5, 1.5)), maxiter=maxiter, popsize=12,
                                 seed=1, x0=x0, polish=False, tol=1e-3)
    optics = Optics(*res.x)
    r = track(*beam, line, optics, tb.rigidity_Tm, K0, ETA_CELL, eta_down, z_start_m=0.20)
    print(f"  B {name:8s} eta_down {eta_down:.1f}: T = {r['T_total']:.3f} (pipe {r['T_pipe']:.2f}, aperture "
          f"{r['T_aperture']:.2f}); optics {optics}", flush=True)
    return {"part": "B", "beam": name, "emittance_n_edge_pi_mm_mrad": np.nan, "eta_downstream": eta_down,
            "solenoid_B_T": optics.solenoid_B_T, "q1_gradient_Tm": optics.q1_gradient_Tm, "q2_gradient_Tm": optics.q2_gradient_Tm,
            "T_pipe": r["T_pipe"], "T_aperture": r["T_aperture"], "T_total": r["T_total"], "T_envelope": np.nan,
            **{f"input_{k}": v for k, v in info.items()},
            "z_m": r["z_m"].tolist(), "x_rms_mm": r["x_rms_mm"].tolist(), "y_rms_mm": r["y_rms_mm"].tolist()}


def main() -> int:
    args = parse_args()
    ta = [(d, e, h, args.n_particles) for d in ("kv", "gaussian") for e in (0.25, 0.5) for h in (0.0, 0.5, 0.7, 0.9)]
    tbs = [(k, h, args.n_particles, args.n_match, args.match_maxiter, args.snapshots) for k in PIC_INPUTS for h in (0.5, 0.7, 0.9)]
    print(f"CW5: part A {len(ta)} tracks (CW2 optics), part B {len(tbs)} rematches + tracks; eta_cell {ETA_CELL}")
    if args.dry_run:
        for k, pth in PIC_INPUTS.items():
            print(f"  PIC input {k}: {pth} ({'found' if pth.exists() else 'MISSING'})")
        print("[DRY RUN SUCCESS] nothing written.")
        return 0
    with ProcessPoolExecutor(max_workers=args.processes) as pool:
        rows = list(pool.map(part_a, ta)) + list(pool.map(part_b, tbs))
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    hist_cols = ("z_m", "x_rms_mm", "y_rms_mm")
    summary = pd.DataFrame([{k: v for k, v in r.items() if k not in hist_cols} for r in rows])
    summary.to_csv(out / "track_summary.csv", index=False, float_format="%.5g")
    pd.concat([pd.DataFrame({"part": r["part"], "beam": r["beam"], "emittance_n_edge_pi_mm_mrad": r["emittance_n_edge_pi_mm_mrad"],
                             "eta_downstream": r["eta_downstream"], **{c: r[c] for c in hist_cols}}) for r in rows]
              ).to_csv(out / "track_rms.csv", index=False, float_format="%.5g")
    (out / "track_summary.json").write_text(json.dumps({
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "model": "transverse particle tracking, hard-edge lattice of InjectionLine (solenoid in the Larmor frame), "
                 "2D open-boundary space charge with K0 (1 - eta), pipe 10 mm, accepted r < 5 mm and |x'|,|y'| < 50 mrad",
        "eta_cell": ETA_CELL, "pic_inputs": {k: str(v) for k, v in PIC_INPUTS.items()},
        "rows": summary.to_dict(orient="records"),
    }, indent=2, default=float))
    with pd.option_context("display.width", 220):
        print(summary[["part", "beam", "emittance_n_edge_pi_mm_mrad", "eta_downstream", "T_pipe", "T_aperture",
                       "T_total", "T_envelope"]].round(3).to_string(index=False))

    setup_publication_style()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for r in rows:
        ax = axes[0] if r["part"] == "A" else axes[1]
        if r["part"] == "A" and r["emittance_n_edge_pi_mm_mrad"] != 0.25:
            continue
        lab = f"{r['beam']} eta_down {r['eta_downstream']:.1f}"
        ax.plot(np.array(r["z_m"]) * 100, 2 * np.array(r["x_rms_mm"]), label=lab, lw=1.2)
    for ax, t in zip(axes, ("model beams, 0.25 pi mm mrad (2 x rms x)", "PIC cell-exit beams (2 x rms x)")):
        ax.axhline(10, color="k", ls=":", lw=0.8); ax.axhline(5, color="k", ls="-.", lw=0.8)
        ax.set_title(t, fontsize=10); ax.set_xlabel("z from cell entrance [cm]"); ax.grid(alpha=0.3); ax.legend(fontsize=6)
    axes[0].set_ylabel("2 x rms x of surviving particles [mm]")
    fig.suptitle(f"Particle tracking to the inflector, eta_cell = {ETA_CELL}", fontsize=10)
    save_figure(fig, out / "track_to_inflector")
    plt.close(fig)
    print(f"Wrote {out}/track_summary.csv and figure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
