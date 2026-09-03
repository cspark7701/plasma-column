"""
src/plasma_column/plotting/transport.py

Plotting pipeline routines for beam phase space distributions, RMS beam envelope ODE transport,
and inflector acceptance ellipses.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union
import matplotlib.pyplot as plt
import matplotlib.patches as patches
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
    envelope_data: Union[pd.DataFrame, tuple[np.ndarray, np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]],
    output_dir: str | Path,
    case_name: str = "simulation_case",
    aperture_r_mm: float = 5.0,
    output_name: Optional[str] = None,
    title: Optional[str] = None,
    show_elements: bool = True,
) -> tuple[Path, Path]:
    """
    Plots transverse beam envelope Rx(z), Ry(z) or r(z) along the injection line
    through Plasma Neutralizer, Solenoid, Q1, Q2, and Spiral Inflector.
    """
    setup_publication_style()

    # Parse input data
    if isinstance(envelope_data, tuple):
        if len(envelope_data) == 3:
            z_raw, rx_raw, ry_raw = envelope_data
            z_cm = np.asarray(z_raw) * 100.0 if np.max(z_raw) < 10.0 else np.asarray(z_raw)
            rx_mm = np.asarray(rx_raw) * 1000.0 if np.max(rx_raw) < 0.5 else np.asarray(rx_raw)
            ry_mm = np.asarray(ry_raw) * 1000.0 if np.max(ry_raw) < 0.5 else np.asarray(ry_raw)
        else:
            z_raw, r_raw = envelope_data
            z_cm = np.asarray(z_raw) * 100.0 if np.max(z_raw) < 10.0 else np.asarray(z_raw)
            rx_mm = np.asarray(r_raw) * 1000.0 if np.max(r_raw) < 0.5 else np.asarray(r_raw)
            ry_mm = None
    elif isinstance(envelope_data, pd.DataFrame):
        df = envelope_data
        z_col = "z" if "z" in df.columns else ("z_cm" if "z_cm" in df.columns else df.columns[0])
        z_vals = df[z_col].values
        z_cm = z_vals * 100.0 if np.max(z_vals) < 10.0 else z_vals

        if "Rx" in df.columns and "Ry" in df.columns:
            rx_vals = df["Rx"].values
            ry_vals = df["Ry"].values
            rx_mm = rx_vals * 1000.0 if np.max(rx_vals) < 0.5 else rx_vals
            ry_mm = ry_vals * 1000.0 if np.max(ry_vals) < 0.5 else ry_vals
        elif "r" in df.columns:
            r_vals = df["r"].values
            rx_mm = r_vals * 1000.0 if np.max(r_vals) < 0.5 else r_vals
            ry_mm = None
        else:
            rx_mm = df.iloc[:, 1].values * 1000.0 if np.max(df.iloc[:, 1].values) < 0.5 else df.iloc[:, 1].values
            ry_mm = df.iloc[:, 2].values * 1000.0 if len(df.columns) > 2 and np.max(df.iloc[:, 2].values) < 0.5 else None
    else:
        raise ValueError(f"Unsupported envelope_data format: {type(envelope_data)}")

    if show_elements:
        fig, (ax_top, ax) = plt.subplots(
            2, 1, figsize=(10, 5.5), gridspec_kw={"height_ratios": [1, 4]}, sharex=True
        )

        # Draw physical beamline elements schematic in top canvas
        # Cell (0 to 20 cm)
        ax_top.add_patch(patches.Rectangle((0, -0.6), 20, 1.2, facecolor="#b2dfdb", edgecolor="black", lw=1))
        ax_top.text(10, 0, "Neutralizer Cell", ha="center", va="center", fontsize=8.5, fontweight="bold")
        # Solenoid (30 to 55 cm)
        ax_top.add_patch(patches.Rectangle((30, -0.75), 25, 1.5, facecolor="#d1c4e9", edgecolor="black", lw=1))
        ax_top.text(42.5, 0, "Solenoid", ha="center", va="center", fontsize=8.5, fontweight="bold")
        # Q1 (65 to 77 cm)
        ax_top.add_patch(patches.Rectangle((65, -0.65), 12, 1.3, facecolor="#ffcdd2", edgecolor="black", lw=1))
        ax_top.text(71, 0, "Q1 (+)", ha="center", va="center", fontsize=8, fontweight="bold")
        # Q2 (85 to 97 cm)
        ax_top.add_patch(patches.Rectangle((85, -0.65), 12, 1.3, facecolor="#bbdefb", edgecolor="black", lw=1))
        ax_top.text(91, 0, "Q2 (-)", ha="center", va="center", fontsize=8, fontweight="bold")
        # Inflector mark at 112 cm
        ax_top.axvline(112, color="tab:red", ls=":", lw=1.5)
        ax_top.text(112, 0.9, "Inflector Entrance", ha="right", va="bottom", fontsize=8, color="tab:red")

        ax_top.set_xlim(-2, max(115.0, np.max(z_cm) + 2))
        ax_top.set_ylim(-1.2, 1.2)
        ax_top.axis("off")
    else:
        fig, ax = plt.subplots(figsize=(9, 5))

    # Envelope curves
    if ry_mm is not None:
        ax.plot(z_cm, rx_mm, label=r"Horizontal $R_x(z)$", color="#1f77b4", lw=2)
        ax.plot(z_cm, ry_mm, label=r"Vertical $R_y(z)$", color="#ff7f0e", lw=2, ls="--")
    else:
        ax.plot(z_cm, rx_mm, label=r"RMS beam radius $r(z)$", color="#1f77b4", lw=2)

    ax.axhline(aperture_r_mm, color="tab:red", lw=1.2, ls=":", label=f"Inflector Aperture ({aperture_r_mm:.1f} mm)")

    ax.set_xlabel("Axial Distance $z$ [cm]", fontsize=11)
    ax.set_ylabel("Beam Envelope Radius [mm]", fontsize=11)
    ax.set_title(title or f"Axial Injection Beam Envelope — {case_name}", fontsize=12)
    ax.grid(True, ls="--", alpha=0.4)
    ax.legend(fontsize=9, loc="upper left")

    plt.tight_layout()

    stem = output_name or f"{case_name}_beam_envelope"
    out_basename = Path(output_dir) / stem
    return save_figure(fig, out_basename)


def plot_multi_case_beam_envelopes(
    case_envelopes: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, str]],
    output_dir: str | Path,
    aperture_radius_mm: float = 5.0,
    output_name: str = "envelope_buncher_to_inflector",
    title: str = "Beam Envelope Transport: Buncher Exit to Inflector Entrance",
) -> tuple[Path, Path]:
    """Plots multi-case horizontal Rx(z) and vertical Ry(z) beam envelopes compared against aperture.

    Args:
        case_envelopes: dict of {case_name: (z_array, Rx_array, Ry_array, color_str)}
        output_dir: directory to save output figures.
        aperture_radius_mm: aperture limit to mark on the plot in mm.
        output_name: file base name for figure.
        title: plot title.
    """
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(9, 5))
    for cname, (z_a, Rx_a, Ry_a, color) in case_envelopes.items():
        z_cm = z_a * 100.0 if np.max(z_a) < 10.0 else z_a
        rx_mm = Rx_a * 1000.0 if np.max(Rx_a) < 0.5 else Rx_a
        ry_mm = Ry_a * 1000.0 if np.max(Ry_a) < 0.5 else Ry_a
        ax.plot(z_cm, rx_mm, label=f"{cname} ($R_x$)", color=color, lw=2)
        ax.plot(z_cm, ry_mm, color=color, lw=1.5, ls="--")

    ax.axhline(aperture_radius_mm, color="black", ls=":", label=f"Inflector Aperture Limit ({aperture_radius_mm:.0f} mm)")
    ax.axhline(-aperture_radius_mm, color="black", ls=":")

    ax.set_xlabel("Axial Distance $z$ [cm]", fontsize=12)
    ax.set_ylabel("Beam Envelope Radius [mm]", fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(True, ls="--", alpha=0.4)

    out_basename = Path(output_dir) / output_name
    return save_figure(fig, out_basename)


def plot_inflector_phase_space_comparison(
    vac_df: pd.DataFrame,
    neut_df: pd.DataFrame,
    output_dir: str | Path,
    plane: str = "x",
    output_name: Optional[str] = None,
    title: Optional[str] = None,
) -> tuple[Path, Path]:
    """Plots comparative transverse phase space (x, x') or (y, y') for vacuum vs neutralized cases."""
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(7, 4.5))

    pos_col = f"{plane}_mm"
    angle_col = f"{plane}p_mrad"
    pos_label = rf"Transverse Position ${plane}$ [mm]"
    angle_label = rf"Divergence ${plane}'$ [mrad]"

    if pos_col in vac_df.columns and angle_col in vac_df.columns:
        ax.scatter(vac_df[pos_col], vac_df[angle_col], alpha=0.4, label="Vacuum Reference", color="tab:blue", s=15)
    if pos_col in neut_df.columns and angle_col in neut_df.columns:
        ax.scatter(neut_df[pos_col], neut_df[angle_col], alpha=0.5, label=r"$\mathrm{H}_2$-Neutralized ($90\%$)", color="tab:green", s=15)

    ax.set_xlabel(pos_label, fontsize=11)
    ax.set_ylabel(angle_label, fontsize=11)
    ax.set_title(title or f"Transverse Phase Space $({plane}, {plane}')$ at Inflector Entrance", fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, ls="--", alpha=0.4)

    stem = output_name or f"inflector_phase_space_{plane}{plane}p"
    out_basename = Path(output_dir) / stem
    return save_figure(fig, out_basename)


def plot_transmission_comparison_bar(
    df_summary: pd.DataFrame,
    output_dir: str | Path,
    output_name: str = "transmission_comparison",
    title: str = "Inflector Transmission Efficiency Comparison",
) -> tuple[Path, Path]:
    """Plots transmission efficiency percentage bar chart across injection line cases."""
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = ["tab:blue", "tab:green", "tab:purple", "tab:orange", "tab:red"]
    bar_colors = [colors[i % len(colors)] for i in range(len(df_summary))]

    bars = ax.bar(
        df_summary["case_name"],
        df_summary["transmission_percent"],
        color=bar_colors,
        width=0.5,
    )
    ax.set_ylabel("Inflector Entrance Transmission [%]", fontsize=11)
    ax.set_ylim(0, 115)
    ax.set_title(title, fontsize=12)
    ax.grid(True, axis="y", ls="--", alpha=0.4)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{height:.1f}%",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    out_basename = Path(output_dir) / output_name
    return save_figure(fig, out_basename)
