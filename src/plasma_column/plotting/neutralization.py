"""
src/plasma_column/plotting/neutralization.py

Plotting pipeline routines for space-charge neutralization kinetics, species populations,
K_eff/K0 ratios, growth rates, spatial profiles, and parameter-scan overlays.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Optional, Sequence
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def setup_publication_style() -> None:
    """Configures Matplotlib default rcParams for publication-quality figures."""
    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
        "axes.grid": True,
        "grid.linestyle": "--",
        "grid.alpha": 0.5,
    })


def save_figure(fig: plt.Figure, output_path_basename: str | Path) -> tuple[Path, Path]:
    """
    Saves matplotlib figure to both .png and .pdf formats as required by project guidelines.
    """
    base_path = Path(output_path_basename).with_suffix("")
    base_path.parent.mkdir(parents=True, exist_ok=True)

    png_path = base_path.with_suffix(".png")
    pdf_path = base_path.with_suffix(".pdf")

    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")

    return png_path, pdf_path


def write_plot_manifest(manifest_entries: list[dict[str, str]], output_file: str | Path) -> Path:
    """Writes manifest.csv recording generated figures, titles, and descriptions."""
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["filename_png", "filename_pdf", "figure_title", "description"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in manifest_entries:
            writer.writerow(entry)

    return path


def plot_particle_counts(
    df: pd.DataFrame,
    output_dir: str | Path,
    case_name: str = "simulation_case",
    title: Optional[str] = None,
) -> tuple[Path, Path]:
    """Plots species particle populations N_p(t), N_e(t), N_i(t) vs time."""
    fig, ax = plt.subplots(figsize=(8, 5))

    time_ns = df["time"].values * 1.0e9 if "time" in df.columns else np.arange(len(df))

    if "Np" in df.columns:
        ax.plot(time_ns, df["Np"], label=r"Protons $N_p$", color="tab:blue", lw=2)
    if "Ne" in df.columns:
        ax.plot(time_ns, df["Ne"], label=r"Electrons $N_e$", color="tab:green", lw=2)
    if "Ni" in df.columns:
        ax.plot(time_ns, df["Ni"], label=r"Ions $N_i$", color="tab:red", lw=2)

    ax.set_xlabel("Time [ns]", fontsize=12)
    ax.set_ylabel("Particle Count", fontsize=12)
    ax.set_title(title or f"Species Populations — {case_name}", fontsize=13)
    ax.grid(True, ls="--", alpha=0.5)
    ax.legend(fontsize=10)

    out_basename = Path(output_dir) / f"{case_name}_particle_counts"
    return save_figure(fig, out_basename)


def plot_neutralization_evolution(
    df: pd.DataFrame,
    output_dir: str | Path,
    case_name: str = "simulation_case",
    title: Optional[str] = None,
) -> tuple[Path, Path]:
    """Plots neutralization fractions eta_electron_only and eta_net vs time."""
    fig, ax = plt.subplots(figsize=(8, 5))

    time_ns = df["time"].values * 1.0e9 if "time" in df.columns else np.arange(len(df))

    if "eta_electron_only" in df.columns:
        ax.plot(time_ns, df["eta_electron_only"], label=r"$\eta_{\text{electron\_only}} = N_e / N_p$", color="tab:green", lw=2)
    if "eta_net" in df.columns:
        ax.plot(time_ns, df["eta_net"], label=r"$\eta_{\text{net}} = (N_e - N_i) / N_p$", color="tab:purple", lw=2)

    ax.set_xlabel("Time [ns]", fontsize=12)
    ax.set_ylabel("Neutralization Fraction", fontsize=12)
    ax.set_ylim(-0.05, 1.1)
    ax.set_title(title or f"Neutralization Fraction Evolution — {case_name}", fontsize=13)
    ax.grid(True, ls="--", alpha=0.5)
    ax.legend(fontsize=10)

    out_basename = Path(output_dir) / f"{case_name}_neutralization_evolution"
    return save_figure(fig, out_basename)


def plot_keff_over_k0(
    df: pd.DataFrame,
    output_dir: str | Path,
    case_name: str = "simulation_case",
    title: Optional[str] = None,
) -> tuple[Path, Path]:
    """Plots effective perveance reduction ratio K_eff / K0 vs time."""
    fig, ax = plt.subplots(figsize=(8, 5))

    time_ns = df["time"].values * 1.0e9 if "time" in df.columns else np.arange(len(df))

    if "keff_over_k0" in df.columns:
        ax.plot(time_ns, df["keff_over_k0"], label=r"$K_{\text{eff}}/K_0 = 1 - \eta_{\text{net}}$", color="tab:red", lw=2)

    ax.set_xlabel("Time [ns]", fontsize=12)
    ax.set_ylabel(r"Perveance Reduction Ratio $K_{\text{eff}}/K_0$", fontsize=12)
    ax.set_ylim(-0.05, 1.1)
    ax.set_title(title or f"Effective Perveance Ratio — {case_name}", fontsize=13)
    ax.grid(True, ls="--", alpha=0.5)
    ax.legend(fontsize=10)

    out_basename = Path(output_dir) / f"{case_name}_keff_over_k0"
    return save_figure(fig, out_basename)


def plot_multi_case_neutralization(
    cases: list[tuple[str, pd.DataFrame]],
    output_dir: str | Path,
    column: str = "eta_net",
    time_column: str = "time",
    time_scale: float = 1.0e9,
    time_unit: str = "ns",
    ylabel: str = r"Net Neutralization $(N_e - N_i) / N_p$",
    title: str = "Neutralization History — All Cases",
    output_name: str = "multi_case_neutralization",
    ylim: tuple[float, float] = (-0.05, 1.15),
    show_legend: bool = True,
) -> tuple[Path, Path]:
    """Overlay neutralization time histories from multiple cases on a single axes."""
    _COLORS = [
        "tab:blue", "tab:orange", "tab:green", "tab:red",
        "tab:purple", "tab:brown", "tab:pink", "tab:gray",
        "tab:olive", "tab:cyan",
    ]
    _STYLES = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]

    fig, ax = plt.subplots(figsize=(10, 6))

    plotted = 0
    for i, (label, df) in enumerate(cases):
        if column not in df.columns:
            continue
        t = df[time_column].values * time_scale if time_column in df.columns else np.arange(len(df))
        y = df[column].values
        color  = _COLORS[i % len(_COLORS)]
        lstyle = _STYLES[i // len(_COLORS) % len(_STYLES)]
        ax.plot(t, y, label=label, color=color, ls=lstyle, lw=2)
        plotted += 1

    if plotted == 0:
        ax.text(0.5, 0.5, f"No data found\n(column: '{column}')",
                ha="center", va="center", transform=ax.transAxes, fontsize=12, color="gray")

    ax.set_xlabel(f"Time [{time_unit}]", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_ylim(*ylim)
    ax.set_title(title, fontsize=13)
    ax.grid(True, ls="--", alpha=0.5)
    if show_legend and plotted > 0:
        ax.legend(fontsize=9, loc="best")

    out_basename = Path(output_dir) / output_name
    return save_figure(fig, out_basename)


def plot_species_growth_rates(
    df: pd.DataFrame,
    output_dir: str | Path,
    case_name: str = "simulation_case",
    time_column: str = "time",
    ne_column: str = "Ne",
    ni_column: str = "Ni",
    smooth_window: int = 5,
    title: Optional[str] = None,
) -> tuple[Path, Path]:
    """Plot dNe/dt and dNi/dt (ionisation-rate proxies) versus time."""
    fig, ax = plt.subplots(figsize=(9, 5))

    t = df[time_column].values if time_column in df.columns else np.arange(len(df))
    t_ns = t * 1.0e9

    def _rate(y: np.ndarray, t: np.ndarray, window: int) -> np.ndarray:
        dy = np.gradient(y, t)
        if window > 1:
            dy = pd.Series(dy).rolling(window, center=True, min_periods=1).mean().values
        return dy

    if ne_column in df.columns:
        dNe = _rate(df[ne_column].values, t, smooth_window)
        ax.plot(t_ns, dNe, label=r"$dN_e/dt$", color="tab:green", lw=1.8)

    if ni_column in df.columns:
        dNi = _rate(df[ni_column].values, t, smooth_window)
        ax.plot(t_ns, dNi, label=r"$dN_i/dt$  (gas ions)", color="tab:red", lw=1.8, ls="--")

    ax.axhline(0, color="black", lw=0.8, ls=":")
    ax.set_xlabel("Time [ns]", fontsize=12)
    ax.set_ylabel("Growth Rate [particles / s]", fontsize=12)
    ax.set_title(title or f"Species Growth Rates — {case_name}", fontsize=13)
    ax.grid(True, ls="--", alpha=0.5)
    ax.legend(fontsize=10)

    if smooth_window > 1:
        ax.text(0.98, 0.02, f"Smoothed (window={smooth_window})",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=8, color="gray", style="italic")

    out_basename = Path(output_dir) / f"{case_name}_species_growth_rates"
    return save_figure(fig, out_basename)


def plot_radial_density_profile(
    radial_df: pd.DataFrame,
    output_dir: str | Path,
    case_name: str = "simulation_case",
    r_unit: float = 1.0e3,
    r_unit_label: str = "mm",
    title: Optional[str] = None,
    highlight_core_r: Optional[float] = None,
) -> tuple[Path, Path]:
    """Plot radial density profiles ne(r), ni(r), np(r)."""
    fig, ax = plt.subplots(figsize=(8, 5))

    r_mm = radial_df["r"].values * r_unit

    if "np_r" in radial_df.columns:
        ax.semilogy(r_mm, radial_df["np_r"].clip(lower=1), label=r"Protons $n_p(r)$", color="tab:blue", lw=2)
    if "ne_r" in radial_df.columns:
        ax.semilogy(r_mm, radial_df["ne_r"].clip(lower=1), label=r"Electrons $n_e(r)$", color="tab:green", lw=2)
    if "ni_r" in radial_df.columns:
        ax.semilogy(r_mm, radial_df["ni_r"].clip(lower=1), label=r"Gas ions $n_i(r)$", color="tab:red", lw=2, ls="--")

    if highlight_core_r is not None:
        ax.axvline(highlight_core_r * r_unit, color="gray", lw=1.2, ls=":",
                   label=f"Core radius ({highlight_core_r*r_unit:.1f} {r_unit_label})")

    ax.set_xlabel(f"Radius $r$ [{r_unit_label}]", fontsize=12)
    ax.set_ylabel(r"Number density [m$^{-3}$]", fontsize=12)
    ax.set_title(title or f"Radial Density Profiles — {case_name}", fontsize=13)
    ax.grid(True, ls="--", alpha=0.5)
    ax.legend(fontsize=10)

    out_basename = Path(output_dir) / f"{case_name}_radial_density_profile"
    return save_figure(fig, out_basename)


def plot_neutralization_vs_z(
    z_df: pd.DataFrame,
    output_dir: str | Path,
    case_name: str = "simulation_case",
    z_unit: float = 1.0e2,
    z_unit_label: str = "cm",
    z_col_range: Optional[tuple[float, float]] = None,
    title: Optional[str] = None,
) -> tuple[Path, Path]:
    """Plot local neutralization η(z) and K_eff/K0(z) along beam axis."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

    z_u = z_df["z"].values * z_unit

    if "eta_electron_only_local_z" in z_df.columns:
        ax1.plot(z_u, z_df["eta_electron_only_local_z"], label=r"$\eta_e(z) = n_e/n_p$", color="tab:green", lw=2)
    if "eta_net_local_z" in z_df.columns:
        ax1.plot(z_u, z_df["eta_net_local_z"], label=r"$\eta_\mathrm{net}(z) = (n_e-n_i)/n_p$", color="tab:purple", lw=2, ls="--")

    ax1.axhline(1.0, color="black", lw=0.8, ls=":", label="Full compensation")
    ax1.set_ylabel("Local Neutralization Fraction", fontsize=11)
    ax1.set_ylim(-0.05, 1.2)
    ax1.legend(fontsize=9, loc="upper right")
    ax1.grid(True, ls="--", alpha=0.5)
    ax1.set_title(title or f"Axial Neutralization Profile — {case_name}", fontsize=13)

    if "keff_over_k0_local_z" in z_df.columns:
        ax2.plot(z_u, z_df["keff_over_k0_local_z"], label=r"$K_\mathrm{eff}/K_0(z)$", color="tab:red", lw=2)

    ax2.axhline(0.0, color="black", lw=0.8, ls=":", label="Full compensation")
    ax2.axhline(1.0, color="gray", lw=0.8, ls="--", label="No compensation")
    ax2.set_xlabel(f"Axial Position $z$ [{z_unit_label}]", fontsize=11)
    ax2.set_ylabel(r"$K_\mathrm{eff}/K_0$", fontsize=11)
    ax2.set_ylim(-0.1, 1.15)
    ax2.legend(fontsize=9, loc="upper right")
    ax2.grid(True, ls="--", alpha=0.5)

    if z_col_range is not None:
        z_lo, z_hi = z_col_range[0] * z_unit, z_col_range[1] * z_unit
        for ax in (ax1, ax2):
            ax.axvspan(z_lo, z_hi, alpha=0.08, color="tab:blue", label="Plasma cell")

    fig.tight_layout()
    out_basename = Path(output_dir) / f"{case_name}_neutralization_vs_z"
    return save_figure(fig, out_basename)


def plot_bunched_beam_keff(
    time_ns: np.ndarray,
    eta_avg: np.ndarray,
    output_dir: str | Path,
    case_name: str = "simulation_case",
    bunching_factors: Sequence[float] = (1.0, 2.0, 3.0, 5.0),
    title: Optional[str] = None,
) -> tuple[Path, Path]:
    """Plot effective perveance K_eff/K0 for peak-bunch case vs time."""
    fig, ax = plt.subplots(figsize=(9, 5))
    _COLORS = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple"]

    for i, Bf in enumerate(bunching_factors):
        keff_peak = 1.0 - eta_avg / Bf
        keff_peak = np.clip(keff_peak, 0.0, None)
        label = rf"$B_f = {Bf:.1f}$  →  $K_{{\rm eff,peak}}/K_0$"
        ax.plot(time_ns, keff_peak, label=label,
                color=_COLORS[i % len(_COLORS)], lw=1.8,
                ls="-" if i % 2 == 0 else "--")

    ax.plot(time_ns, np.ones_like(time_ns), color="black", lw=1, ls=":",
            label=r"$K_{\rm eff}/K_0 = 1$ (no compensation)")

    ax.set_xlabel("Time [ns]", fontsize=12)
    ax.set_ylabel(r"$K_{\rm eff,peak} / K_0$", fontsize=12)
    ax.set_ylim(-0.05, 1.15)
    ax.set_title(title or f"Bunched-Beam Effective Perveance — {case_name}", fontsize=13)
    ax.grid(True, ls="--", alpha=0.5)
    ax.legend(fontsize=9, loc="upper right")

    note = (r"$K_{\rm eff,peak}/K_0 \approx 1 - \bar{\eta}/B_f$"
            "\n(plasma reaches avg neutralization only)")
    ax.text(0.02, 0.05, note, transform=ax.transAxes, fontsize=8,
            color="gray", style="italic", va="bottom")

    out_basename = Path(output_dir) / f"{case_name}_bunched_beam_keff"
    return save_figure(fig, out_basename)


def plot_neutralization_panel(
    df: pd.DataFrame,
    output_dir: str | Path,
    case_name: str = "simulation_case",
    time_column: str = "time",
    title: Optional[str] = None,
) -> tuple[Path, Path]:
    """3-panel summary figure per case."""
    fig, axes = plt.subplots(3, 1, figsize=(9, 10), sharex=True)

    t_ns = df[time_column].values * 1.0e9 if time_column in df.columns else np.arange(len(df))

    # (a) Species populations
    ax = axes[0]
    for col, label, color in [
        ("Np", r"Protons $N_p$",   "tab:blue"),
        ("Ne", r"Electrons $N_e$", "tab:green"),
        ("Ni", r"Gas ions $N_i$",  "tab:red"),
    ]:
        if col in df.columns:
            ax.plot(t_ns, df[col], label=label, color=color, lw=1.8)
    ax.set_ylabel("Global Particle Count", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, ls="--", alpha=0.5)
    ax.set_title(title or f"Simulation Summary — {case_name}", fontsize=12)

    # (b) Neutralization
    ax = axes[1]
    for col, label, color, ls in [
        ("eta_electron_only", r"$\eta_e = N_e/N_p$",          "tab:green",  "-"),
        ("eta_net",           r"$\eta_\mathrm{net}=(N_e-N_i)/N_p$", "tab:purple", "--"),
    ]:
        if col in df.columns:
            ax.plot(t_ns, df[col], label=label, color=color, lw=1.8, ls=ls)
    ax.axhline(1.0, color="gray", lw=0.8, ls=":")
    ax.set_ylabel("Neutralization Fraction", fontsize=11)
    ax.set_ylim(-0.05, 1.2)
    ax.legend(fontsize=9)
    ax.grid(True, ls="--", alpha=0.5)

    # (c) K_eff/K0
    ax = axes[2]
    for col, label, color in [
        ("keff_over_k0",               r"$K_\mathrm{eff}/K_0$ (net)",            "tab:red"),
        ("keff_over_k0_electron_only", r"$K_\mathrm{eff}/K_0$ (e-only)",         "tab:orange"),
    ]:
        if col in df.columns:
            ax.plot(t_ns, df[col], label=label, color=color, lw=1.8)
    ax.axhline(1.0, color="gray", lw=0.8, ls="--", label="No compensation")
    ax.axhline(0.0, color="black", lw=0.8, ls=":", label="Full compensation")
    ax.set_xlabel("Time [ns]", fontsize=11)
    ax.set_ylabel(r"$K_\mathrm{eff}/K_0$", fontsize=11)
    ax.set_ylim(-0.05, 1.2)
    ax.legend(fontsize=9)
    ax.grid(True, ls="--", alpha=0.5)

    fig.tight_layout()
    out_basename = Path(output_dir) / f"{case_name}_neutralization_panel"
    return save_figure(fig, out_basename)
