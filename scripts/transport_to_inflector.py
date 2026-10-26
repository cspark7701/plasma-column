#!/usr/bin/env python3
"""
scripts/transport_to_inflector.py

Matched envelope transport through the axial injection line
(buncher exit -> plasma neutralizer -> solenoid -> Q1 -> Q2 -> spiral inflector), task 106.

For each compensation scenario and beam emittance, the solenoid field and the Q1/Q2 gradients are
matched (plasma_column.transport.match_optics) and the geometric KV transmission estimate is
reported: pipe clipping (10 mm), inflector aperture (5 mm) and divergence (50 mrad).

Scenarios (peak-slice perveance; bunched cases use B_f(z) of a sine buncher set for the inflector,
task 105). The electrons cancel only the RF-averaged charge (tau_ion ~ 80 us >> T_RF = 20 ns), so the
physical bunched cases use K = K0 (B_f - eta) ("average"). The "_slice" cases use K = K0 B_f (1 - eta),
an upper bound reached only if every slice were compensated by the same fraction:
    dc_uncompensated             DC beam, eta = 0
    dc_cell                      DC beam, eta = eta_cell in the cell
    dc_full                      DC beam, eta_cell over the whole line (residual-gas compensation)
    bunched_uncompensated        peak slice, eta = 0
    bunched_cell                 eta_cell in the cell (average)
    bunched_cell_down0p5         eta_cell in the cell + 0.5 downstream (average, illustrative)
    bunched_full                 eta_cell over the whole line (average)
    bunched_cell_slice           as bunched_cell, per-slice upper bound
    bunched_cell_down0p5_slice   as bunched_cell_down0p5, per-slice upper bound
    bunched_full_slice           as bunched_full, per-slice upper bound
eta_cell = PIC beam-core eta_net of seeded H2 at 1e-5 Torr (paper/manuscript/pic_data, DC beam).

Beam at the buncher exit: a = 2 mm, parallel (as in the PIC runs); normalized edge emittance
0.25, 0.5 and 1.0 pi mm mrad.

Outputs (default results/transport_to_inflector/, git-ignored):
    transport_summary.csv / .json, envelopes.csv, envelopes_matched.{png,pdf}

Usage:
    python scripts/transport_to_inflector.py --dry_run
    python scripts/transport_to_inflector.py
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
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

from plasma_column.bunching import BuncherModel, bunching_along_line
from plasma_column.injection_line import InjectionLine
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.transport import TransportBeam, envelope, match_optics, perveance_profile
from plasma_column.warpx_io import get_git_info

PIC_CASES = PROJECT_ROOT / "paper" / "manuscript" / "pic_data" / "production_cases.csv"
EMITTANCES = (0.25e-6, 0.5e-6, 1.0e-6)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Matched envelope transport to the spiral inflector.")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "results" / "transport_to_inflector")
    p.add_argument("--buncher_voltage_V", type=float, default=620.0, help="Sine buncher (task 105 optimum).")
    p.add_argument("--maxiter", type=int, default=40, help="Differential-evolution generations per match.")
    p.add_argument("--dry_run", action="store_true", help="List scenarios; write nothing.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    line = InjectionLine()
    eta_cell = float(pd.read_csv(PIC_CASES).set_index("case_name").loc["seeded_H2_1e-5Torr", "eta_net_local"])
    zb = np.linspace(0.0, line.total_length, 225)
    bf = bunching_along_line(zb, BuncherModel(voltage_V=args.buncher_voltage_V), n_particles=100_000)["bunching_factor"]
    bf = np.maximum(bf, 1.0)

    scenarios = {
        "dc_uncompensated": dict(eta_cell=0.0, eta_downstream=0.0, bunched=False),
        "dc_cell": dict(eta_cell=eta_cell, eta_downstream=0.0, bunched=False),
        "dc_full": dict(eta_cell=eta_cell, eta_downstream=eta_cell, bunched=False),
        "bunched_uncompensated": dict(eta_cell=0.0, eta_downstream=0.0, bunched=True),
    }
    for mode, suffix in (("average", ""), ("per_slice", "_slice")):
        scenarios[f"bunched_cell{suffix}"] = dict(eta_cell=eta_cell, eta_downstream=0.0, bunched=True, mode=mode)
        scenarios[f"bunched_cell_down0p5{suffix}"] = dict(eta_cell=eta_cell, eta_downstream=0.5, bunched=True,
                                                          mode=mode)
        scenarios[f"bunched_full{suffix}"] = dict(eta_cell=eta_cell, eta_downstream=eta_cell, bunched=True,
                                                  mode=mode)
    print(f"Transport scan: {len(scenarios)} scenarios x {len(EMITTANCES)} emittances, eta_cell = {eta_cell:.3f}")
    if args.dry_run:
        for k, v in scenarios.items():
            print(f"  {k}: {v}")
        print("[DRY RUN SUCCESS] nothing written.")
        return 0

    rows, envs = [], {}
    for eps_n in EMITTANCES:
        beam = TransportBeam(emittance_n_edge_m_rad=eps_n)
        K0 = beam.proton.perveance_K0
        found = []  # optima of the scenarios already matched at this emittance, used as extra starts
        for name, sc in scenarios.items():
            K = perveance_profile(K0, line, sc["eta_cell"], sc["eta_downstream"],
                                  zb if sc["bunched"] else None, bf if sc["bunched"] else None,
                                  compensation=sc.get("mode", "average"))
            optics, t = match_optics(beam, line, K, maxiter=args.maxiter, starts=tuple(reversed(found)))
            found.append(optics)
            envs[(eps_n, name)] = envelope(beam, line, optics, K)
            rows.append({"emittance_n_edge_pi_mm_mrad": eps_n * 1e6, "scenario": name,
                         "eta_cell": sc["eta_cell"], "eta_downstream": sc["eta_downstream"],
                         "bunched_peak_slice": sc["bunched"],
                         "compensation": sc.get("mode", "average") if sc["bunched"] else "dc",
                         "solenoid_B_T": optics.solenoid_B_T, "q1_gradient_Tm": optics.q1_gradient_Tm,
                         "q2_gradient_Tm": optics.q2_gradient_Tm, **t})
            print(f"  eps_n {eps_n * 1e6:.2f}  {name:24s} T = {t['T_total']:.3f} "
                  f"(pipe {t['T_pipe']:.2f}, ap {t['T_inflector_aperture']:.2f}, div {t['T_inflector_divergence']:.2f}), "
                  f"max R {t['max_R_mm']:.1f} mm", flush=True)

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "transport_summary.csv", index=False, float_format="%.6g")
    env_rows = []
    for (eps_n, name), e in envs.items():
        env_rows.append(pd.DataFrame({"emittance_n_edge_pi_mm_mrad": eps_n * 1e6, "scenario": name,
                                      "z_m": e["z_m"], "Rx_mm": e["Rx_m"] * 1e3, "Ry_mm": e["Ry_m"] * 1e3}))
    pd.concat(env_rows).iloc[::5].to_csv(out / "envelopes.csv", index=False, float_format="%.5g")
    meta = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "model": "KV envelope, matched solenoid + Q1/Q2 per scenario, geometric transmission estimate",
        "beam": "30 keV, 10 mA, a = 2 mm parallel at the buncher exit",
        "eta_cell_source": "PIC core eta_net, seeded_H2_1e-5Torr (DC beam)",
        "bunching": f"sine buncher {args.buncher_voltage_V} V, ballistic B_f(z) (task 105)",
        "compensation": "average: K = K0 (B_f - eta) (physical, tau_ion >> T_RF); "
                        "per_slice: K = K0 B_f (1 - eta) (upper bound)",
        "apertures": "pipe 10 mm, inflector 5 mm, divergence 50 mrad",
        "rows": rows,
    }
    (out / "transport_summary.json").write_text(json.dumps(meta, indent=2, default=str))

    setup_publication_style()
    fig, axes = plt.subplots(1, len(EMITTANCES), figsize=(14, 4), sharey=True)
    colors = {"dc_uncompensated": "0.5", "dc_cell": "k", "bunched_uncompensated": "tab:red",
              "bunched_full": "tab:blue", "bunched_full_slice": "tab:cyan"}
    for ax, eps_n in zip(axes, EMITTANCES):
        for name, color in colors.items():
            e = envs[(eps_n, name)]
            ax.plot(e["z_m"] * 100, e["Rx_m"] * 1e3, color=color, lw=1.6, label=f"{name} (x)")
            ax.plot(e["z_m"] * 100, e["Ry_m"] * 1e3, color=color, lw=1.0, ls="--")
        ax.axhline(10.0, color="k", lw=0.8, ls=":")
        ax.axhline(5.0, color="k", lw=0.8, ls="-.")
        ax.set_ylim(0, 40)
        ax.set_xlabel("z from buncher exit [cm]")
        ax.set_title(rf"$\varepsilon_n$ = {eps_n * 1e6:.2f} $\pi$ mm mrad (edge)", fontsize=10)
    axes[0].set_ylabel("edge radius [mm] (solid x, dashed y)")
    axes[0].legend(fontsize=7, loc="upper left")
    fig.suptitle("Matched envelopes to the inflector (pipe 10 mm dotted, inflector 5 mm dash-dot)", fontsize=10)
    fig.tight_layout()
    save_figure(fig, out / "envelopes_matched")
    plt.close(fig)
    print(f"Wrote {out}/transport_summary.csv and figure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
