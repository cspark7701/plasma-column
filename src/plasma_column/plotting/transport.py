"""
src/plasma_column/plotting/transport.py

Plotting pipeline routines for beam phase space distributions, RMS beam envelope ODE transport,
and inflector acceptance ellipses.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .neutralization import save_figure, setup_publication_style


def plot_phase_space(
    x: np.ndarray,
    px: np.ndarray,
    output_dir: str | Path,
    case_name: str = "simulation_case",
    x_label: str = r"$x$ [mm]",
    px_label: str = r"$p_x / p_0$ [mrad]",
    species_label: str = "beam protons",
    title: Optional[str] = None,
    max_points: int = 20_000,
    alpha: float = 0.25,
    color: str = "tab:blue",
    rms_ellipse: bool = True,
    output_name: Optional[str] = None,
) -> tuple[Path, Path]:
    """
    Plot a transverse phase-space scatter (x, px) with optional RMS ellipse overlay.
    """
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(7, 6))

    x  = np.asarray(x, dtype=float)
    px = np.asarray(px, dtype=float)

    n = len(x)
    if n > max_points:
        idx = np.random.default_rng(42).choice(n, max_points, replace=False)
        x_plot, px_plot = x[idx], px[idx]
    else:
        x_plot, px_plot = x, px

    ax.scatter(x_plot, px_plot, s=1.5, alpha=alpha, color=color, rasterized=True,
               label=f"{species_label} (N={n:,})")

    if rms_ellipse and len(x) > 3:
        from matplotlib.patches import Ellipse
        cov = np.cov(x, px)
        sigma_x  = np.sqrt(cov[0, 0])
        sigma_px = np.sqrt(cov[1, 1])
        rho      = cov[0, 1] / (sigma_x * sigma_px + 1e-30)
        angle_rad = 0.5 * np.arctan2(2 * rho * sigma_x * sigma_px,
                                      sigma_x**2 - sigma_px**2)
        ell = Ellipse(
            xy=(np.mean(x), np.mean(px)),
            width=2 * sigma_x,
            height=2 * sigma_px,
            angle=np.degrees(angle_rad),
            edgecolor="black", facecolor="none", lw=1.5, ls="--", label=r"1-$\sigma$ RMS ellipse",
        )
        ax.add_patch(ell)
        emittance = np.sqrt(max(np.linalg.det(cov), 0.0))
        ax.text(0.02, 0.97,
                rf"$\varepsilon_\mathrm{{rms}} = {emittance:.3g}$ mm·mrad",
                transform=ax.transAxes, va="top", ha="left", fontsize=9, color="black")

    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel(px_label, fontsize=12)
    ax.set_title(title or f"Transverse Phase Space — {case_name}", fontsize=13)
    ax.legend(fontsize=9, loc="lower right", markerscale=4)
    ax.grid(True, ls="--", alpha=0.4)

    stem = output_name or f"{case_name}_phase_space"
    out_basename = Path(output_dir) / stem
    return save_figure(fig, out_basename)


def plot_beam_envelope_transport(
    envelope_df: pd.DataFrame,
    output_dir: str | Path,
    case_name: str = "simulation_case",
    aperture_r_mm: float = 5.0,
    output_name: Optional[str] = None,
    title: Optional[str] = None,
) -> tuple[Path, Path]:
    """
    Plots transverse beam envelope r(z) along injection line through Solenoid, Q1, Q2, and Inflector.
    """
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(9, 5))

    z_cm = envelope_df["z"].values * 100.0 if "z" in envelope_df.columns else np.arange(len(envelope_df))
    r_mm = envelope_df["r"].values * 1000.0 if "r" in envelope_df.columns else np.ones_like(z_cm)

    ax.plot(z_cm, r_mm, label=r"RMS beam radius $r(z)$", color="tab:blue", lw=2)
    ax.axhline(aperture_r_mm, color="tab:red", lw=1.2, ls="--", label=f"Inflector Aperture ({aperture_r_mm:.1f} mm)")

    ax.set_xlabel("Axial Distance $z$ [cm]", fontsize=12)
    ax.set_ylabel("Beam Envelope Radius $r$ [mm]", fontsize=12)
    ax.set_title(title or f"Beam Envelope Transport — {case_name}", fontsize=13)
    ax.grid(True, ls="--", alpha=0.5)
    ax.legend(fontsize=10)

    stem = output_name or f"{case_name}_beam_envelope"
    out_basename = Path(output_dir) / stem
    return save_figure(fig, out_basename)
