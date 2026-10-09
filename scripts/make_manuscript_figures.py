#!/usr/bin/env python3
"""
scripts/make_manuscript_figures.py

Generates the figures and the number macros used by the journal manuscript
paper/manuscript/plasma_column_prab.tex. Every number in the manuscript text
comes from plasma_column.design_estimates.compute_design_numbers(), so the
text, figures and code stay consistent.

Outputs (default --output_dir paper/manuscript):
    figures/fig1_beamline_layout.{pdf,png}
    figures/fig2_cross_sections_tau.{pdf,png}
    figures/fig3_timescales.{pdf,png}
    figures/fig4_envelope_drift.{pdf,png}
    figures/fig5_peak_perveance.{pdf,png}
    numbers.tex               LaTeX \\newcommand macros
    manuscript_numbers.json   raw numbers + provenance metadata

All content is analytical (closed-form estimates and the tabulated Rudd-model
cross sections). No PIC output is plotted.

Usage:
    python scripts/make_manuscript_figures.py --dry_run
    python scripts/make_manuscript_figures.py
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

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.design_estimates import (
    DesignPoint,
    compute_design_numbers,
    design_point_dict,
    laminar_envelope_drift,
)
from plasma_column.gas import CrossSectionDatabase, gas_density_m3
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.warpx_io import get_git_info

WARPX_DIR = Path("/home/cspark/Work/simulation_codes-working/warpx")
H2_COLOR = "#2a7ab9"
KR_COLOR = "#c4512b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate manuscript figures and number macros.")
    parser.add_argument("--output_dir", "--output-dir", type=Path,
                        default=PROJECT_ROOT / "paper" / "manuscript")
    parser.add_argument("--dry_run", action="store_true",
                        help="Compute all numbers and figures in memory without writing files.")
    return parser.parse_args()


# --------------------------------------------------------------------------- #
# Number formatting for LaTeX
# --------------------------------------------------------------------------- #
def sci(x: float, digits: int = 2) -> str:
    """Formats x as LaTeX scientific notation, e.g. 1.25\\times10^{-3}."""
    if x == 0:
        return "0"
    exp = int(math.floor(math.log10(abs(x))))
    mant = x / 10**exp
    if round(mant, digits - 1) >= 10:
        mant, exp = mant / 10, exp + 1
    if exp == 0:
        return f"{mant:.{digits - 1}f}"
    return f"{mant:.{digits - 1}f}\\times10^{{{exp}}}"


def fixed(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}"


def build_macros(d: dict[str, float], dp: DesignPoint, env: dict[str, float]) -> dict[str, str]:
    """Maps LaTeX macro names (letters only) to formatted values (math mode content)."""
    return {
        "beta": f"{d['beta']:.5f}",
        "vbeam": sci(d["v_m_s"], 3),
        "Kzero": sci(d["K0"], 3),
        "Kzeropeak": sci(d["K0_peak"], 3),
        "lambdaavg": sci(d["lambda_avg_C_m"], 3),
        "nbavg": sci(d["n_beam_avg_m3"], 2),
        "nbpeak": sci(d["n_beam_peak_m3"], 2),
        "sigmaHtwo": sci(d["sigma_h2_m2"], 3),
        "sigmaKr": sci(d["sigma_kr_m2"], 3),
        "sigmaratio": fixed(d["sigma_ratio_kr_h2"], 2),
        "nHtwo": sci(d["n_h2_m3"], 3),
        "nKr": sci(d["n_kr_m3"], 3),
        "tauHtwous": fixed(d["tau_h2_s"] * 1e6, 0),
        "tauKrus": fixed(d["tau_kr_s"] * 1e6, 0),
        "pKrequal": sci(d["p_kr_equal_tau_torr"], 2),
        "PionHtwo": sci(d["ionization_prob_per_pass_h2"], 2),
        "PionKr": sci(d["ionization_prob_per_pass_kr"], 2),
        "transitns": fixed(d["cell_transit_s"] * 1e9, 0),
        "TRFns": fixed(d["T_rf_s"] * 1e9, 0),
        "bunchns": fixed(d["bunch_duration_s"] * 1e9, 1),
        "bunchmm": fixed(d["bunch_length_m"] * 1e3, 1),
        "gapns": fixed(d["bunch_gap_s"] * 1e9, 0),
        "Bfuniform": fixed(d["uniform_fill_bunching_factor"], 0),
        "omegapeavg": sci(d["omega_pe_avg_rad_s"], 2),
        "omegapepeak": sci(d["omega_pe_peak_rad_s"], 2),
        "omegapebunch": fixed(d["omega_pe_peak_times_bunch"], 0),
        "wellavg": fixed(d["well_depth_avg_V"], 0),
        "wellpeak": fixed(d["well_depth_peak_V"], 0),
        "texpelHtwons": fixed(d["t_expel_h2p_avg_s"] * 1e9, 0),
        "texpelKrns": fixed(d["t_expel_krp_avg_s"] * 1e9, 0),
        "tcrossns": fixed(d["t_electron_cross_s"] * 1e9, 1),
        "tescapens": fixed(d["t_electron_escape_cell_s"] * 1e9, 0),
        "etafreeHtwo": sci(d["eta_free_escape_h2"], 1),
        "etafreeKr": sci(d["eta_free_escape_kr"], 1),
        "ionfracHtwo": sci(d["ion_fraction_h2"], 1),
        "ionfracKr": sci(d["ion_fraction_kr"], 1),
        "Bconfine": fixed(d["B_confine_T"] * 1e3, 0),
        "picdtfs": fixed(d["pic_dt_s"] * 1e15, 0),
        "picns": fixed(d["pic_duration_s"] * 1e9, 1),
        "picdynns": fixed(d["pic_duration_dynamic_s"] * 1e9, 0),
        "picovertau": sci(d["pic_duration_over_tau_h2"], 1),
        "zdoublecm": fixed(d["z_double_K0_m"] * 100, 1),
        "zdoublepeakcm": fixed(d["z_double_K0_peak_m"] * 100, 1),
        "growthKzero": fixed(env["growth_avg_1.0"], 1),
        "growthKhalf": fixed(env["growth_avg_0.5"], 1),
        "growthKtenth": fixed(env["growth_avg_0.1"], 2),
        "growthpeak": fixed(env["growth_peak_static_bunch"], 1),
        "Keffpeakstatic": fixed(env["keff_peak_static_bunch"], 2),
        # inputs
        "Ekev": fixed(dp.energy_keV, 0),
        "Iavgma": fixed(dp.current_avg_mA, 0),
        "Ipeakma": fixed(dp.current_avg_mA * dp.bunching_factor, 0),
        "abeammm": fixed(dp.beam_radius_m * 1e3, 0),
        "bpipemm": fixed(dp.pipe_radius_m * 1e3, 0),
        "Lcellcm": fixed(dp.cell_length_m * 100, 0),
        "fRFmhz": fixed(dp.rf_frequency_hz / 1e6, 0),
        "dphideg": fixed(dp.bunch_phase_width_deg, 0),
        "Bf": fixed(dp.bunching_factor, 0),
        "pHtwo": sci(dp.pressure_h2_torr, 1),
        "pKr": sci(dp.pressure_kr_torr, 1),
        "Eeev": fixed(dp.secondary_electron_energy_eV, 0),
    }


def write_macros(macros: dict[str, str], path: Path) -> None:
    lines = [
        "% Auto-generated by scripts/make_manuscript_figures.py -- do not edit by hand.",
        "% Values are analytical design estimates from plasma_column.design_estimates.",
    ]
    for name, val in macros.items():
        lines.append(f"\\newcommand{{\\num{name}}}{{\\ensuremath{{{val}}}}}")
    path.write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def fig_layout() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(3.4, 1.05))
    elements = [
        ("Buncher", 1.0, "#8fb3d9"),
        ("Plasma\nneutral-\nizer", 1.3, "#9ccf9c"),
        ("Sole-\nnoid", 1.3, "#f2c38f"),
        ("Q1", 0.8, "#e3a3a3"),
        ("Q2", 0.8, "#e3a3a3"),
        ("Spiral\ninflector", 1.0, "#c9c9c9"),
    ]
    x = 0.0
    gap = 0.3
    for label, w, c in elements:
        ax.add_patch(plt.Rectangle((x, 0.15), w, 0.7, facecolor=c, edgecolor="k", lw=0.8))
        ax.text(x + w / 2, 0.5, label, ha="center", va="center", fontsize=6)
        x += w + gap
    ax.annotate("", xy=(x - gap + 0.1, 0.5), xytext=(-0.5, 0.5),
                arrowprops=dict(arrowstyle="-|>", lw=1.0, color="0.3"), zorder=0)
    ax.text(-0.45, 0.92, r"$p^+$, 30 keV", fontsize=6.5, ha="left", va="bottom")
    ax.set_xlim(-0.6, x)
    ax.set_ylim(0, 1.15)
    ax.axis("off")
    ax.text(x - gap, 0.0, "schematic, not to scale", fontsize=5, ha="right", va="bottom", color="0.4")
    fig.tight_layout()
    return fig


def fig_cross_sections_tau(d: dict[str, float], dp: DesignPoint) -> plt.Figure:
    db = CrossSectionDatabase()
    e_keV = np.logspace(0, 3, 300)
    s_h2 = np.array([db.get_proton_impact_cross_section("H2", e * 1e3) for e in e_keV])
    s_kr = np.array([db.get_proton_impact_cross_section("Kr", e * 1e3) for e in e_keV])

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.9))
    a1.loglog(e_keV, s_h2 * 1e20, color=H2_COLOR, label=r"H$_2$")
    a1.loglog(e_keV, s_kr * 1e20, color=KR_COLOR, label="Kr")
    a1.axvline(dp.energy_keV, color="0.5", ls=":", lw=1)
    a1.plot([dp.energy_keV] * 2, [d["sigma_h2_m2"] * 1e20, d["sigma_kr_m2"] * 1e20], "ko", ms=3)
    a1.set_xlabel("Proton lab energy [keV]")
    a1.set_ylabel(r"$\sigma_i$ [$10^{-20}$ m$^2$]")
    a1.legend(frameon=False)
    a1.text(0.03, 0.95, "(a)", transform=a1.transAxes, va="top")

    p = np.logspace(-7, -4, 200)
    v = d["v_m_s"]
    tau_h2 = 1.0 / (np.array([gas_density_m3(pp) for pp in p]) * d["sigma_h2_m2"] * v)
    tau_kr = 1.0 / (np.array([gas_density_m3(pp) for pp in p]) * d["sigma_kr_m2"] * v)
    a2.loglog(p, tau_h2 * 1e6, color=H2_COLOR, label=r"H$_2$")
    a2.loglog(p, tau_kr * 1e6, color=KR_COLOR, label="Kr")
    a2.plot(dp.pressure_h2_torr, d["tau_h2_s"] * 1e6, "o", color=H2_COLOR, ms=5)
    a2.plot(dp.pressure_kr_torr, d["tau_kr_s"] * 1e6, "s", color=KR_COLOR, ms=5)
    a2.axhline(d["tau_h2_s"] * 1e6, color="0.6", ls=":", lw=1)
    a2.plot(d["p_kr_equal_tau_torr"], d["tau_h2_s"] * 1e6, "x", color=KR_COLOR, ms=6)
    a2.set_xlabel("Gas pressure [Torr] (300 K)")
    a2.set_ylabel(r"$\tau_{\rm ion}$ [$\mu$s]")
    a2.legend(frameon=False)
    a2.text(0.03, 0.05, "(b)", transform=a2.transAxes, va="bottom")
    fig.tight_layout()
    return fig


def fig_timescales(d: dict[str, float]) -> plt.Figure:
    items = [
        (r"$1/\omega_{pe}$ (peak $n_b$)", 1.0 / d["omega_pe_peak_rad_s"], "plasma"),
        (r"$e^-$ crossing of beam radius", d["t_electron_cross_s"], "electron"),
        ("Bunch duration", d["bunch_duration_s"], "beam"),
        (r"Bunch gap", d["bunch_gap_s"], "beam"),
        (r"RF period", d["T_rf_s"], "beam"),
        (r"H$_2^+$ expulsion (avg. $\lambda$)", d["t_expel_h2p_avg_s"], "ion"),
        ("Proton transit of cell", d["cell_transit_s"], "beam"),
        (r"$e^-$ free escape from cell", d["t_electron_escape_cell_s"], "electron"),
        ("PIC run, seeded (20k steps)", d["pic_duration_s"], "pic"),
        ("PIC run, dynamic (120k steps)", d["pic_duration_dynamic_s"], "pic"),
        (r"Kr$^+$ expulsion (avg. $\lambda$)", d["t_expel_krp_avg_s"], "ion"),
        (r"$\tau_{\rm ion}$, H$_2$ $10^{-5}$ Torr", d["tau_h2_s"], "ionization"),
        (r"$\tau_{\rm ion}$, Kr $10^{-6}$ Torr", d["tau_kr_s"], "ionization"),
    ]
    items.sort(key=lambda t: t[1])
    colors = {"plasma": "#7b5ea7", "electron": "#2a7ab9", "beam": "0.45", "ion": "#c4512b",
              "pic": "#d4a017", "ionization": "#3a9a5b"}
    fig, ax = plt.subplots(figsize=(6.0, 3.3))
    y = np.arange(len(items))
    ax.barh(y, [t[1] for t in items], color=[colors[t[2]] for t in items], height=0.6)
    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels([t[0] for t in items], fontsize=8.5)
    ax.set_xlabel("Characteristic time [s]")
    ax.set_xlim(1e-11, 1e-3)
    ax.grid(axis="x", which="major", ls=":", lw=0.6)
    fig.tight_layout()
    return fig


def envelope_cases(d: dict[str, float], dp: DesignPoint) -> tuple[dict[str, float], dict]:
    ratios = [1.0, 0.5, 0.2, 0.1]
    curves = {"avg": {}, "peak": {}}
    growth: dict[str, float] = {}
    for r in ratios:
        z, a = laminar_envelope_drift(dp.beam_radius_m, r * d["K0"], dp.cell_length_m)
        curves["avg"][r] = (z, a)
        growth[f"growth_avg_{r}"] = a[-1] / dp.beam_radius_m
        z, a = laminar_envelope_drift(dp.beam_radius_m, r * d["K0_peak"], dp.cell_length_m)
        curves["peak"][r] = (z, a)
    eta_avg = 0.9
    keff_peak = 1.0 - eta_avg / dp.bunching_factor
    z, a = laminar_envelope_drift(dp.beam_radius_m, keff_peak * d["K0_peak"], dp.cell_length_m)
    curves["peak"]["static"] = (z, a)
    growth["keff_peak_static_bunch"] = keff_peak
    growth["growth_peak_static_bunch"] = a[-1] / dp.beam_radius_m
    return growth, curves


def fig_envelope(curves: dict, dp: DesignPoint) -> plt.Figure:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.9), sharey=True)
    shades = {1.0: "0.1", 0.5: "#2a7ab9", 0.2: "#3a9a5b", 0.1: "#c4512b"}
    for r, (z, a) in curves["avg"].items():
        a1.plot(z * 100, a / dp.beam_radius_m, color=shades[r], label=fr"$K_{{\rm eff}}/K_0={r:g}$")
    for r, (z, a) in curves["peak"].items():
        if r == "static":
            a2.plot(z * 100, a / dp.beam_radius_m, "k--", lw=1.2,
                    label=fr"static bkg., $\eta_{{\rm avg}}=0.9$")
        else:
            a2.plot(z * 100, a / dp.beam_radius_m, color=shades[r])
    a1.set_title(r"DC slice, $I=I_{\rm avg}$", fontsize=10)
    a2.set_title(fr"Peak slice, $I=B_f I_{{\rm avg}}$ ($B_f={dp.bunching_factor:g}$)", fontsize=10)
    for ax in (a1, a2):
        ax.set_xlabel("Drift length $z$ [cm]")
        ax.set_yscale("log")
        ax.grid(ls=":", lw=0.6)
    a1.set_ylabel(r"$a(z)/a_0$")
    a1.legend(frameon=False, fontsize=8)
    a2.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    return fig


def fig_peak_perveance(dp: DesignPoint, d: dict[str, float]) -> plt.Figure:
    bf = np.linspace(1, 12, 300)
    fig, ax = plt.subplots(figsize=(3.4, 2.8))
    for eta, c in [(0.5, "#2a7ab9"), (0.9, "#3a9a5b"), (1.0, "#c4512b")]:
        ax.plot(bf, 1 - eta / bf, color=c, label=fr"$\eta_{{\rm avg}}={eta:g}$")
    for b in (dp.bunching_factor, d["uniform_fill_bunching_factor"]):
        ax.axvline(b, color="0.5", ls=":", lw=1)
    ax.set_xlabel(r"Bunching factor $B_f$")
    ax.set_ylabel(r"$K_{\rm eff,peak}/K_{0,\rm peak}$")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.grid(ls=":", lw=0.6)
    fig.tight_layout()
    return fig


def provenance() -> dict:
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "warpx_source": {"path": str(WARPX_DIR), "git": get_git_info(WARPX_DIR),
                         "note": "Not used: all manuscript numbers are analytical."},
    }


def main() -> None:
    args = parse_args()
    setup_publication_style()
    dp = DesignPoint()
    d = compute_design_numbers(dp)
    growth, curves = envelope_cases(d, dp)
    macros = build_macros(d, dp, growth)

    figs = {
        "fig1_beamline_layout": fig_layout(),
        "fig2_cross_sections_tau": fig_cross_sections_tau(d, dp),
        "fig3_timescales": fig_timescales(d),
        "fig4_envelope_drift": fig_envelope(curves, dp),
        "fig5_peak_perveance": fig_peak_perveance(dp, d),
    }

    if args.dry_run:
        print(f"[DRY RUN SUCCESS] {len(macros)} macros and {len(figs)} figures computed; nothing written.")
        for k in ("K0", "tau_h2_s", "tau_kr_s", "p_kr_equal_tau_torr"):
            print(f"  {k:22s} = {d[k]:.4g}")
        return

    out = args.output_dir
    (out / "figures").mkdir(parents=True, exist_ok=True)
    for name, fig in figs.items():
        save_figure(fig, out / "figures" / name)
        plt.close(fig)
    write_macros(macros, out / "numbers.tex")
    payload = {"provenance": provenance(), "design_point": design_point_dict(dp),
               "numbers": d, "envelope": growth}
    (out / "manuscript_numbers.json").write_text(json.dumps(payload, indent=2, default=str))
    print(f"Wrote {len(figs)} figures, numbers.tex and manuscript_numbers.json to {out}")


if __name__ == "__main__":
    main()
