"""
src/plasma_column/notebook_utils.py

Utility helpers for Jupyter notebooks in the plasma-column project.

Provides:
- print_simulation_config(): prints a formatted table of simulation
  configuration parameters, clearly showing which values are defaults
  and which have been explicitly reconfigured by the user.

Usage (in notebooks, after importing modules and setting parameters):

    from plasma_column.notebook_utils import print_simulation_config

    print_simulation_config(
        notebook_title="Python Callback Source Diagnostics",
        defaults={
            "pressure_torr":       1e-5,
            "max_steps":           2000,
            "diag_period":         500,
            "reduced_diag_period": 10,
            "nx / ny / nz":        "24 / 24 / 128",
            "source_every_n_steps":10,
            "gas":                 "H2",
        },
        overrides={
            "max_steps":           20000,   # reconfigured for production
            "diag_period":         5000,    # reconfigured for production
        },
    )
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


# ── ANSI colour codes (suppressed when stdout is not a TTY) ──────────────────
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

    Parameters
    ----------
    notebook_title : str
        Short descriptive title for this notebook / run session.
    defaults : dict
        All configuration parameters with their DEFAULT values.
        Keys are human-readable parameter names.
    overrides : dict, optional
        Parameters that have been RECONFIGURED from their defaults.
        Only keys present here are marked as "CHANGED" in the table.
    extra_info : dict, optional
        Additional free-form key-value info shown at the bottom
        (e.g. output directory, case names, …).
    repo_root : Path, optional
        Repository root for git commit lookup.  Defaults to CWD.
    """
    overrides = overrides or {}
    extra_info = extra_info or {}
    repo_root  = repo_root or Path.cwd()

    now   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    repo_commit   = _git_commit(repo_root)
    warpx_loc     = _warpx_location()
    python_exec   = sys.executable
    conda_env     = os.environ.get("CONDA_DEFAULT_ENV", "unknown")

    # ── Header ──────────────────────────────────────────────────────────────
    sep  = "═" * 76
    sep2 = "─" * 76
    print()
    print(_BOLD(_CYAN(sep)))
    print(_BOLD(_CYAN(f"  SIMULATION CONFIGURATION  ─  {notebook_title}")))
    print(_BOLD(_CYAN(sep)))
    print(f"  {'Timestamp':<28} {now}")
    print(f"  {'Python':<28} {python_exec}")
    print(f"  {'Conda environment':<28} {conda_env}")
    print(f"  {'Repo git commit':<28} {repo_commit}")
    print(f"  {'pywarpx location':<28} {warpx_loc}")
    print(_CYAN(sep2))

    # ── Parameter table ─────────────────────────────────────────────────────
    # Column widths
    W_PARAM  = 32
    W_VAL    = 20
    W_STATUS = 10

    header = (
        f"  {'Parameter':<{W_PARAM}}  {'Value':<{W_VAL}}  {'Status':<{W_STATUS}}  Note"
    )
    print(_BOLD(header))
    print("  " + "-" * (W_PARAM + W_VAL + W_STATUS + 20))

    for param, default_val in defaults.items():
        if param in overrides:
            new_val = overrides[param]
            status  = _YELLOW("CHANGED")
            note    = _DIM(f"← was: {default_val}")
            val_str = str(new_val)
        else:
            status  = _GREEN("default")
            note    = ""
            val_str = str(default_val)

        print(f"  {param:<{W_PARAM}}  {val_str:<{W_VAL}}  {status:<{W_STATUS}}  {note}")

    # ── Extra info ──────────────────────────────────────────────────────────
    if extra_info:
        print(_CYAN(sep2))
        print(_BOLD("  Additional context"))
        print("  " + "-" * (W_PARAM + W_VAL + W_STATUS + 20))
        for k, v in extra_info.items():
            print(f"  {k:<{W_PARAM}}  {str(v)}")

    print(_BOLD(_CYAN(sep)))
    print()
