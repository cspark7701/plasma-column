"""
src/plasma_column/plotting/paper_figures.py

Dedicated multi-panel paper figure generators (fig01–fig10) for manuscript submission.
Exports figure pairs (.png and .pdf) into paper/figures/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .neutralization import save_figure, setup_publication_style


def generate_fig01_axial_injection_concept(output_dir: str | Path) -> tuple[Path, Path]:
    """Figure 01: Schematic & concept of cyclotron axial injection with neutralizer cell."""
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.text(0.5, 0.5, "Figure 01: Axial Injection Schematic & Neutralizer Placement\n(buncher -> neutralizer -> solenoid -> Q1 -> Q2 -> inflector)",
            ha="center", va="center", fontsize=12)
    ax.axis("off")
    return save_figure(fig, Path(output_dir) / "fig01_axial_injection_concept")


def generate_fig02_plasma_neutralizer_module(output_dir: str | Path) -> tuple[Path, Path]:
    """Figure 02: Plasma neutralizer cell geometry & gas injection concept."""
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.text(0.5, 0.5, "Figure 02: Compact Plasma Neutralizer Module & Gas Injection Geometry",
            ha="center", va="center", fontsize=12)
    ax.axis("off")
    return save_figure(fig, Path(output_dir) / "fig02_plasma_neutralizer_module")
