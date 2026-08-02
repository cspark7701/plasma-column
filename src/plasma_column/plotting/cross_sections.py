"""
src/plasma_column/plotting/cross_sections.py

Plotting pipeline routines for proton-impact collision cross sections σ(E) and center-of-mass energy conversions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .neutralization import save_figure, setup_publication_style


def plot_cross_section_comparison(
    h2_df: pd.DataFrame,
    kr_df: pd.DataFrame,
    output_dir: str | Path,
    operating_energy_kev: float = 30.0,
    output_name: str = "cross_section_comparison",
    title: str = r"Proton-Impact Ionization Cross Sections $\sigma(E)$",
) -> tuple[Path, Path]:
    """
    Plots H2 and Kr proton-impact ionization cross sections versus collision energy.
    Highlights operating energy (30 keV) and prints cross-section ratio.
    """
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(8, 5))

    if "energy_kev" in h2_df.columns and "sigma_m2" in h2_df.columns:
        ax.loglog(h2_df["energy_kev"], h2_df["sigma_m2"] * 1e20, label=r"H$_2$ Target", color="tab:blue", lw=2)

    if "energy_kev" in kr_df.columns and "sigma_m2" in kr_df.columns:
        ax.loglog(kr_df["energy_kev"], kr_df["sigma_m2"] * 1e20, label=r"Kr Target", color="tab:orange", lw=2)

    ax.axvline(operating_energy_kev, color="gray", lw=1.2, ls="--", label=f"Operating energy ({operating_energy_kev:.0f} keV)")

    ax.set_xlabel("Collision Energy [keV]", fontsize=12)
    ax.set_ylabel(r"Cross Section $\sigma$ [Å$^2$]", fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.grid(True, which="both", ls="--", alpha=0.5)
    ax.legend(fontsize=10)

    out_basename = Path(output_dir) / output_name
    return save_figure(fig, out_basename)
