"""
src/plasma_column/notebook_utils.py

Utility helpers and cell template generators for Jupyter notebooks in the plasma-column project.
Provides:
- print_simulation_config(): Formatted table display of simulation configuration parameters.
- make_code_cell(), make_markdown_cell(), create_notebook(), write_notebook_file(): Factory functions for generating Jupyter notebooks programmatically.
- COMMON_IMPORTS, PLOT_IMPORTS: Canonical import cell snippets for project notebooks.
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


# ── Notebook Factory Helpers ──────────────────────────────────────────────────

def make_code_cell(source: str | list[str]) -> dict[str, Any]:
    """Factory function creating a standard v4 Jupyter notebook code cell dict."""
    if isinstance(source, str):
        lines = [line + "\n" for line in source.splitlines()]
    else:
        lines = [line + "\n" if not line.endswith("\n") else line for line in source]
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines,
    }


def make_markdown_cell(source: str | list[str]) -> dict[str, Any]:
    """Factory function creating a standard v4 Jupyter notebook markdown cell dict."""
    if isinstance(source, str):
        lines = [line + "\n" for line in source.splitlines()]
    else:
        lines = [line + "\n" if not line.endswith("\n") else line for line in source]
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": lines,
    }


def create_notebook(
    cells: list[dict[str, Any]],
    display_name: str = "Python 3 (warpx-dev)",
    kernel_name: str = "python3",
) -> dict[str, Any]:
    """Factory creating a full v4 Jupyter notebook JSON dictionary structure."""
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": display_name,
                "language": "python",
                "name": kernel_name,
            },
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write_notebook_file(nb_dict: dict[str, Any], output_path: str | Path) -> Path:
    """Writes Jupyter notebook dictionary to JSON file on disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb_dict, f, indent=1)
    return path


# ── Reusable Imports Snippets ─────────────────────────────────────────────────

COMMON_IMPORTS = [
    "from pathlib import Path\n",
    "import os, sys, subprocess, time\n",
    "import numpy as np\n",
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "\n",
    "# Locate project root\n",
    "_ROOT = Path.cwd()\n",
    "while _ROOT.name != 'plasma_column' and _ROOT.parent != _ROOT:\n",
    "    _ROOT = _ROOT.parent\n",
    "if str(_ROOT / 'src') not in sys.path:\n",
    "    sys.path.insert(0, str(_ROOT / 'src'))\n",
    "\n",
    "WORK           = Path.home() / 'Work' / 'simulation_codes-working'\n",
    "WARPX_DATA_DIR = WORK / 'warpx-data'\n",
    "RUNS_DIR       = _ROOT / 'runs'\n",
    "PLOTS_DIR      = _ROOT / 'plots'\n",
    "RUNS_DIR.mkdir(exist_ok=True)\n",
    "PLOTS_DIR.mkdir(exist_ok=True)\n",
    "\n",
    "os.environ['WARPX_DATA_DIR']  = str(WARPX_DATA_DIR)\n",
    "os.environ['LD_LIBRARY_PATH'] = (\n",
    "    str(WORK / 'warpx' / 'install' / 'lib') + ':'\n",
    "    + os.environ.get('LD_LIBRARY_PATH', '')\n",
    ")\n",
    "print('Python :', sys.executable)\n",
    "print('ROOT   :', _ROOT)\n",
    "print('WarpX data:', WARPX_DATA_DIR)\n",
]

PLOT_IMPORTS = [
    "from plasma_column.plotting import (\n",
    "    setup_publication_style,\n",
    "    plot_multi_case_neutralization,\n",
    "    plot_neutralization_evolution,\n",
    "    plot_particle_counts,\n",
    "    plot_keff_over_k0,\n",
    "    plot_species_growth_rates,\n",
    "    plot_neutralization_panel,\n",
    "    plot_bunched_beam_keff,\n",
    "    plot_keff_pressure_scan,\n",
    "    plot_radial_density_profile,\n",
    "    plot_neutralization_vs_z,\n",
    "    plot_phase_space,\n",
    "    save_figure,\n",
    ")\n",
    "from plasma_column.diagnostics import (\n",
    "    load_particle_number_diagnostic,\n",
    "    compute_particle_number_metrics,\n",
    "    DataLoader,\n",
    ")\n",
    "import warnings\n",
    "setup_publication_style()\n",
    "print('Plotting helpers loaded.')\n",
]


# ── ANSI Colour Helpers ───────────────────────────────────────────────────────

def _colour(code: str, text: str) -> str:
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text


_BOLD   = lambda t: _colour("1", t)
_GREEN  = lambda t: _colour("32", t)
_YELLOW = lambda t: _colour("33", t)
_CYAN   = lambda t: _colour("36", t)
_DIM    = lambda t: _colour("2",  t)


def _git_commit(repo: Path | None = None) -> str:
    """Return short git commit hash of *repo* (or CWD)."""
    cwd = str(repo) if repo else "."
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=cwd, text=True,
            stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def _warpx_location() -> str:
    """Return the path to the installed pywarpx package, or 'not found'."""
    try:
        import pywarpx
        return str(Path(pywarpx.__file__).parent)
    except ImportError:
        return "not found"


def print_simulation_config(
    notebook_title: str,
    defaults: dict[str, Any],
    overrides: dict[str, Any] | None = None,
    extra_info: dict[str, Any] | None = None,
    repo_root: Path | None = None,
) -> None:
    """
    Print a clear, table-formatted simulation configuration summary.
    """
    overrides = overrides or {}
    extra_info = extra_info or {}

    git_hash  = _git_commit(repo_root)
    warpx_loc = _warpx_location()
    now_str   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n" + "=" * 70)
    print(_BOLD(f"  {notebook_title}"))
    print("=" * 70)
    print(f"  Timestamp   : {now_str}")
    print(f"  Git Commit  : {_CYAN(git_hash)}")
    print(f"  PyWarpX Loc : {warpx_loc}")

    if extra_info:
        for k, v in extra_info.items():
            print(f"  {k:<12}: {v}")

    print("-" * 70)
    print(f"  {'Parameter':<24} {'Configured Value':<24} {'Status':<16}")
    print("-" * 70)

    all_keys = list(defaults.keys())
    for k in overrides:
        if k not in all_keys:
            all_keys.append(k)

    for key in all_keys:
        default_val = defaults.get(key, "(none)")
        if key in overrides:
            val_str = str(overrides[key])
            status  = _YELLOW("★ CHANGED")
        else:
            val_str = str(default_val)
            status  = _DIM("default")

        print(f"  {key:<24} {val_str:<24} {status:<16}")

    print("=" * 70 + "\n")
