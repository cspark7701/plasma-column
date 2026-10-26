#!/usr/bin/env python3
"""
scripts/make_manuscript_pic_results.py

Freezes the production PIC results (cases/production.yaml, results/production/) into a small
tracked dataset and generates the PIC figures and number macros of the journal manuscript
paper/manuscript/plasma_column_prab.tex. Every PIC number in the manuscript text comes from the
frozen dataset, so the text can be rebuilt without the 126 GB of simulation output.

Outputs (default --output_dir paper/manuscript):
    pic_data/production_cases.csv     one row per case: seed fraction, local core and global values
    pic_data/local_eta_vs_t.csv       beam-core eta per snapshot, every case + the rescaled run
    pic_data/radial_profiles.csv      n_b(r), n_e(r), n_i(r) at the last snapshot (baseline cases)
    pic_data/provenance.json          repository commit, results directory, per-case run metadata
    figures/fig6_pic_eta_vs_time.{pdf,png}
    figures/fig7_pic_pressure_scan.{pdf,png}
    figures/fig8_pic_radial_profiles.{pdf,png}
    numbers_pic.tex                   LaTeX \\newcommand macros (\\numpic...)
    pic_table.tex                     rows of the production-case table

Local values are beam-core averages (r <= 2 mm, 0 <= z <= 0.20 m, beam-filled cells). Seeded
cases start from a prescribed plasma (analytic source estimate, not self-consistent proton-impact
ionization). The callback run uses an ionization rate multiplied by 1000 and is labeled RESCALED.

Usage:
    python scripts/make_manuscript_pic_results.py --dry_run
    python scripts/make_manuscript_pic_results.py                 # freeze from results/production
    python scripts/make_manuscript_pic_results.py --from_frozen   # rebuild from pic_data/ only
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
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

from plasma_column.design_estimates import uniform_beam_density_m3
from plasma_column.beam import ProtonBeam
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.schema import ScanMatrixConfig
from plasma_column.warpx_io import get_git_info

H2_COLOR = "#2a7ab9"
KR_COLOR = "#c4512b"
ACCEL_CASE = "callback_H2_accel_x1000_rescaled"
PROFILE_CASES = ("seeded_H2_1e-5Torr", "seeded_Kr_1e-6Torr")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze production PIC results and make manuscript PIC figures.")
    parser.add_argument("--matrix", type=Path, default=PROJECT_ROOT / "cases" / "production.yaml")
    parser.add_argument("--results_dir", type=Path, default=PROJECT_ROOT / "results" / "production")
    parser.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "paper" / "manuscript")
    parser.add_argument("--from_frozen", action="store_true",
                        help="Do not read results_dir; rebuild figures and macros from output_dir/pic_data/.")
    parser.add_argument("--dry_run", action="store_true", help="Collect and check data; write nothing.")
    return parser.parse_args()


# --------------------------------------------------------------------------- #
# Freezing
# --------------------------------------------------------------------------- #
def _seed_fraction(case_dir: Path) -> float:
    model = case_dir / "neutralization_model.csv"
    if not model.exists():
        return float("nan")
    return float(pd.read_csv(model, nrows=1)["seeded_fraction_at_step0"].iloc[0])


def collect_cases(matrix: ScanMatrixConfig, results_dir: Path) -> pd.DataFrame:
    rows = []
    for case in matrix.cases:
        # Nominal uniform beam density n_b = I / (e v pi a^2); the seed density is seed_fraction * n_b.
        beam = ProtonBeam(energy_keV=case.beam.energy_keV, current_mA=case.beam.current_mA,
                          radius_m=case.beam.radius_m)
        nb_nominal = uniform_beam_density_m3(case.beam.current_mA * 1e-3, beam.velocity, case.beam.radius_m)
        case_dir = results_dir / case.case_name
        summary = json.loads((case_dir / "diagnostics_summary.json").read_text())
        core = summary["core_averages"]
        g = pd.read_csv(case_dir / "global_particle_number.csv").iloc[-1]
        stages = [s for s, members in matrix.stages.items() if case.case_name in members]
        np_core = core["np_core_avg"]
        seed = _seed_fraction(case_dir)
        rows.append({
            "case_name": case.case_name,
            "method": case.method,
            "gas": case.plasma.gas,
            "pressure_torr": case.plasma.pressure_torr,
            "stages": " ".join(s.split("_")[0] for s in stages),
            "final_step": int(g["step"]),
            "seed_fraction": seed,
            "eta_electron_only_local": core["eta_electron_only_local"],
            "eta_net_local": core["eta_net_local"],
            "ni_over_np_local": core["ni_core_avg"] / np_core if np_core else float("nan"),
            "np_core_over_nominal": np_core / nb_nominal,
            "ni_core_over_seed": (core["ni_core_avg"] / (seed * nb_nominal)) if seed > 0 else float("nan"),
            "keff_over_k0_local": core["keff_over_k0_local"],
            "core_beam_fill_fraction": core["core_beam_fill_fraction"],
            "eta_net_global": float(g["eta_net"]),
        })
    return pd.DataFrame(rows)


def collect_time_series(names: list[str], results_dir: Path) -> pd.DataFrame:
    frames = []
    for name in names:
        path = results_dir / name / "local_neutralization_vs_t.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df.insert(0, "case_name", name)
        frames.append(df[["case_name", "step", "time", "core_beam_fill_fraction",
                          "eta_electron_only_local", "eta_net_local"]])
    return pd.concat(frames, ignore_index=True)


def collect_profiles(results_dir: Path) -> pd.DataFrame:
    frames = []
    for name in PROFILE_CASES:
        df = pd.read_csv(results_dir / name / "radial_density_profiles.csv")
        df.insert(0, "case_name", name)
        frames.append(df[["case_name", "r", "np_r", "ne_r", "ni_r"]])
    return pd.concat(frames, ignore_index=True)


def collect_provenance(names: list[str], results_dir: Path, args: argparse.Namespace) -> dict:
    runs = {}
    for name in names:
        meta_path = results_dir / name / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            runs[name] = {"timestamp": meta.get("timestamp"),
                          "plasma_column_commit": (meta.get("plasma_column_repo") or {}).get("commit"),
                          "warpx_commit": ((meta.get("warpx_source") or {}).get("git") or {}).get("commit")}
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "matrix": str(args.matrix.relative_to(PROJECT_ROOT) if args.matrix.is_absolute() else args.matrix),
        "results_dir": str(args.results_dir),
        "core_definition": "r <= 2 mm, 0 <= z <= 0.20 m, beam-filled cells, last snapshot t = 218 ns",
        "runs": runs,
    }


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def fig_eta_vs_time(ts: pd.DataFrame, accel_tau_eff_s: float) -> plt.Figure:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.9))
    styles = [
        ("seeded_H2_1e-5Torr", r"H$_2$ $10^{-5}$ seeded", H2_COLOR, "-"),
        ("cxx_mcc_H2_1e-5Torr", r"H$_2$ $10^{-5}$ + e-impact MCC", H2_COLOR, ":"),
        ("seeded_Kr_1e-6Torr", r"Kr $10^{-6}$ seeded", KR_COLOR, "-"),
        ("cxx_mcc_Kr_1e-6Torr", r"Kr $10^{-6}$ + e-impact MCC", KR_COLOR, ":"),
        ("vacuum_reference", "vacuum", "0.4", "--"),
    ]
    for name, label, color, ls in styles:
        d = ts[ts.case_name == name]
        a1.plot(d.time * 1e9, d.eta_net_local, ls, color=color, marker="o", ms=3, label=label)
    a1.set_xlabel("t [ns]")
    a1.set_ylabel(r"local $\eta_{\rm net}$ (beam core)")
    a1.set_ylim(-0.1, 1.1)
    a1.legend(frameon=False, fontsize=7)
    a1.text(0.03, 0.95, "(a)", transform=a1.transAxes, va="top")

    d = ts[ts.case_name == ACCEL_CASE]
    t = np.linspace(0.0, d.time.max(), 200)
    a2.plot(d.time * 1e9, d.eta_electron_only_local, "s-", color=H2_COLOR, ms=3, mfc="none",
            label=r"$n_e/n_b$")
    a2.plot(d.time * 1e9, d.eta_net_local, "o-", color=H2_COLOR, ms=3, label=r"$\eta_{\rm net}$")
    a2.plot(t * 1e9, 1.0 - np.exp(-t / accel_tau_eff_s), "k--", lw=1,
            label=r"$1-e^{-t/\tau_{\rm eff}}$")
    a2.set_xlabel("t [ns]")
    a2.set_ylabel("local core value")
    a2.set_title(r"RESCALED source ($\times1000$), H$_2$ $10^{-5}$ Torr", fontsize=8)
    a2.legend(frameon=False, fontsize=7)
    a2.text(0.03, 0.95, "(b)", transform=a2.transAxes, va="top")
    fig.tight_layout()
    return fig


def fig_pressure_scan(cases: pd.DataFrame) -> plt.Figure:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.9))
    seeded = cases[cases.method == "seeded_compensation"]
    for gas, color in (("H2", H2_COLOR), ("Kr", KR_COLOR)):
        d = seeded[seeded.gas == gas].sort_values("pressure_torr")
        label = r"H$_2$" if gas == "H2" else "Kr"
        a1.semilogx(d.pressure_torr, d.eta_net_local, "o-", color=color, label=f"{label} local " + r"$\eta_{\rm net}$")
        a1.semilogx(d.pressure_torr, d.seed_fraction, "--", color=color, lw=1, label=f"{label} seed fraction")
        a2.semilogx(d.pressure_torr, d.eta_electron_only_local, "s-", color=color, mfc="none", label=f"{label} " + r"$n_e/n_b$")
        a2.semilogx(d.pressure_torr, d.ni_over_np_local, "^-", color=color, label=f"{label} " + r"$n_i/n_b$")
    a1.set_xlabel("pressure [Torr]")
    a1.set_ylabel(r"$\eta$")
    a1.set_ylim(0, 1.05)
    a1.legend(frameon=False, fontsize=7)
    a1.text(0.03, 0.95, "(a)", transform=a1.transAxes, va="top")
    a2.set_xlabel("pressure [Torr]")
    a2.set_ylabel(r"core density / $n_b$")
    a2.set_ylim(0, 3.3)
    a2.legend(frameon=False, fontsize=7, ncol=2, loc="upper center")
    a2.text(0.03, 0.95, "(b)", transform=a2.transAxes, va="top")
    fig.tight_layout()
    return fig


def fig_radial_profiles(prof: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8), sharey=True)
    titles = {"seeded_H2_1e-5Torr": r"H$_2$, $10^{-5}$ Torr", "seeded_Kr_1e-6Torr": r"Kr, $10^{-6}$ Torr"}
    for ax, (name, tag) in zip(axes, (("seeded_H2_1e-5Torr", "(a)"), ("seeded_Kr_1e-6Torr", "(b)"))):
        d = prof[prof.case_name == name]
        r_mm = d.r * 1e3
        ax.plot(r_mm, d.np_r, color="0.2", label=r"$n_b$")
        ax.plot(r_mm, d.ne_r, color=H2_COLOR, label=r"$n_e$")
        ax.plot(r_mm, d.ni_r, color=KR_COLOR, label=r"$n_i$")
        ax.axvline(2.0, color="0.5", ls=":", lw=0.8)
        ax.set_xlim(0, 8)
        ax.set_xlabel("r [mm]")
        ax.set_title(titles[name], fontsize=9)
        ax.text(0.03, 0.95, tag, transform=ax.transAxes, va="top")
    axes[0].set_ylabel(r"density [m$^{-3}$]")
    axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# Macros
# --------------------------------------------------------------------------- #
def _f(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}"


def build_pic_macros(cases: pd.DataFrame, ts: pd.DataFrame, accel_tau_eff_s: float) -> dict[str, str]:
    c = cases.set_index("case_name")

    def v(name: str, col: str) -> float:
        return float(c.loc[name, col])

    seeded = cases[cases.method == "seeded_compensation"]
    h2 = seeded[seeded.gas == "H2"]
    kr = seeded[seeded.gas == "Kr"]
    h2_plateau = h2[h2.pressure_torr >= 1e-5]
    acc = ts[ts.case_name == ACCEL_CASE].sort_values("time").iloc[-1]
    return {
        "picncases": str(len(cases)),
        "picHtwoeta": _f(v("seeded_H2_1e-5Torr", "eta_net_local")),
        "picHtwokeff": _f(v("seeded_H2_1e-5Torr", "keff_over_k0_local")),
        "picHtwoseed": _f(v("seeded_H2_1e-5Torr", "seed_fraction")),
        "picHtwoni": _f(v("seeded_H2_1e-5Torr", "ni_over_np_local")),
        "picHtwoniseed": _f(v("seeded_H2_1e-5Torr", "ni_core_over_seed")),
        "picKrniseed": _f(v("seeded_Kr_1e-6Torr", "ni_core_over_seed")),
        "picHtwonbcore": _f(v("seeded_H2_1e-5Torr", "np_core_over_nominal")),
        "picKrnbcore": _f(v("seeded_Kr_1e-6Torr", "np_core_over_nominal")),
        "picHtwone": _f(v("seeded_H2_1e-5Torr", "eta_electron_only_local")),
        "picHtwomcceta": _f(v("cxx_mcc_H2_1e-5Torr", "eta_net_local")),
        "picKreta": _f(v("seeded_Kr_1e-6Torr", "eta_net_local")),
        "picKrkeff": _f(v("seeded_Kr_1e-6Torr", "keff_over_k0_local")),
        "picKrseed": _f(v("seeded_Kr_1e-6Torr", "seed_fraction")),
        "picKrni": _f(v("seeded_Kr_1e-6Torr", "ni_over_np_local")),
        "picKrne": _f(v("seeded_Kr_1e-6Torr", "eta_electron_only_local")),
        "picKrmcceta": _f(v("cxx_mcc_Kr_1e-6Torr", "eta_net_local")),
        "picHtwoetalowp": _f(v("seeded_H2_1e-6Torr", "eta_net_local")),
        "picHtwoseedlowp": _f(v("seeded_H2_1e-6Torr", "seed_fraction")),
        "picHtwoetamidp": _f(v("seeded_H2_3e-6Torr", "eta_net_local")),
        "picHtwoseedmidp": _f(v("seeded_H2_3e-6Torr", "seed_fraction")),
        "picHtwoplateaumin": _f(h2_plateau.eta_net_local.min()),
        "picHtwoplateaumax": _f(h2_plateau.eta_net_local.max()),
        "picKretamin": _f(kr.eta_net_local.min()),
        "picKretamax": _f(kr.eta_net_local.max()),
        "picKrnimin": _f(kr.ni_over_np_local.min(), 1),
        "picKrnimax": _f(kr.ni_over_np_local.max(), 1),
        "picKrnemin": _f(kr.eta_electron_only_local.min(), 1),
        "picKrnemax": _f(kr.eta_electron_only_local.max(), 1),
        "picKrseedmax": _f(kr.seed_fraction.max()),
        "picHtwoglobal": _f(v("seeded_H2_1e-5Torr", "eta_net_global")),
        "picvaceta": _f(abs(v("vacuum_reference", "eta_net_local"))),
        "picacctaueffns": f"{accel_tau_eff_s * 1e9:.0f}",
        "picacceta": _f(float(acc.eta_net_local)),
        "picaccne": _f(float(acc.eta_electron_only_local), 1),
        "picaccsource": _f(1.0 - math.exp(-float(acc.time) / accel_tau_eff_s)),
    }


def write_case_table(cases: pd.DataFrame, path: Path) -> None:
    """LaTeX table body (rows only) of the production cases, included by the manuscript."""
    method = {"seeded_compensation": "seeded", "cxx_mcc_custom": "e-MCC", "vacuum": "vacuum"}
    gas = {"H2": r"$\Htwo$", "Kr": "Kr", "none": "--"}
    order = cases.assign(_m=cases.method.map({"vacuum": 0, "seeded_compensation": 1, "cxx_mcc_custom": 2}))
    order = order.sort_values(["_m", "gas", "pressure_torr"])
    lines = ["% Auto-generated by scripts/make_manuscript_pic_results.py -- do not edit by hand."]
    for r in order.itertuples():
        if r.method == "vacuum":
            p, seed, ni = "--", "--", "--"
        else:
            e = int(math.floor(math.log10(r.pressure_torr)))
            m = r.pressure_torr / 10**e
            p = f"$10^{{{e}}}$" if abs(m - 1) < 1e-9 else f"${m:g}\\times10^{{{e}}}$"
            seed, ni = f"{r.seed_fraction:.2f}", f"{r.ni_over_np_local:.2f}"
        lines.append(f"{method[r.method]} & {gas[r.gas]} & {p} & {seed} & {r.eta_electron_only_local:.2f} & "
                     f"{ni} & {abs(r.eta_net_local) if abs(r.eta_net_local) < 5e-3 else r.eta_net_local:.2f} & "
                     f"{r.keff_over_k0_local:.2f} \\\\")
    path.write_text("\n".join(lines) + "\n")


def write_macros(macros: dict[str, str], path: Path) -> None:
    lines = [
        "% Auto-generated by scripts/make_manuscript_pic_results.py -- do not edit by hand.",
        "% Values are production PIC results frozen in paper/manuscript/pic_data/.",
    ]
    lines += [f"\\newcommand{{\\num{k}}}{{\\ensuremath{{{val}}}}}" for k, val in macros.items()]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    data_dir = args.output_dir / "pic_data"

    if args.from_frozen:
        cases = pd.read_csv(data_dir / "production_cases.csv")
        ts = pd.read_csv(data_dir / "local_eta_vs_t.csv")
        prof = pd.read_csv(data_dir / "radial_profiles.csv")
        accel_tau_eff_s = json.loads((data_dir / "provenance.json").read_text())["accelerated_tau_eff_s"]
        provenance = None
    else:
        matrix = ScanMatrixConfig.from_yaml(args.matrix)
        cases = collect_cases(matrix, args.results_dir)
        incomplete = cases[cases.final_step < max(c.numerics.max_steps for c in matrix.cases)]
        if not incomplete.empty:
            raise SystemExit(f"Unfinished cases: {list(incomplete.case_name)}")
        names = [c.case_name for c in matrix.cases] + [ACCEL_CASE]
        ts = collect_time_series(names, args.results_dir)
        prof = collect_profiles(args.results_dir)
        model = pd.read_csv(args.results_dir / ACCEL_CASE / "neutralization_source_model.csv", nrows=1)
        accel_tau_eff_s = float(model["tau_eff_s"].iloc[0])
        provenance = collect_provenance(names, args.results_dir, args)
        provenance["accelerated_tau_eff_s"] = accel_tau_eff_s
        provenance["accelerated_source_rate_factor"] = float(model["source_rate_factor"].iloc[0])

    macros = build_pic_macros(cases, ts, accel_tau_eff_s)
    if args.dry_run:
        print(f"[DRY RUN SUCCESS] {len(cases)} cases, {ts.case_name.nunique()} time series, "
              f"{len(macros)} macros; nothing written.")
        for k in ("picHtwoeta", "picKreta", "picacceta"):
            print(f"  {k:16s} = {macros[k]}")
        return

    setup_publication_style()
    figs = {
        "fig6_pic_eta_vs_time": fig_eta_vs_time(ts, accel_tau_eff_s),
        "fig7_pic_pressure_scan": fig_pressure_scan(cases),
        "fig8_pic_radial_profiles": fig_radial_profiles(prof),
    }
    (args.output_dir / "figures").mkdir(parents=True, exist_ok=True)
    for name, fig in figs.items():
        save_figure(fig, args.output_dir / "figures" / name)
        plt.close(fig)
    if provenance is not None:
        data_dir.mkdir(parents=True, exist_ok=True)
        cases.to_csv(data_dir / "production_cases.csv", index=False, float_format="%.6g")
        ts.to_csv(data_dir / "local_eta_vs_t.csv", index=False, float_format="%.6g")
        prof.to_csv(data_dir / "radial_profiles.csv", index=False, float_format="%.6g")
        (data_dir / "provenance.json").write_text(json.dumps(provenance, indent=2, default=str))
    write_macros(macros, args.output_dir / "numbers_pic.tex")
    write_case_table(cases, args.output_dir / "pic_table.tex")
    print(f"Wrote {len(figs)} figures and numbers_pic.tex to {args.output_dir}"
          + ("" if provenance is None else f"; froze data in {data_dir}"))


if __name__ == "__main__":
    main()
