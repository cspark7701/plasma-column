"""
src/plasma_column/warpx_io.py

WarpX plotfile / openPMD diagnostic reader wrappers, metadata I/O utilities, and schema validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import (
    SimulationCaseConfig,
    BeamConfig,
    PlasmaConfig,
    SolenoidConfig,
    NumericsConfig,
)


def save_metadata(metadata: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    return path


def find_plotfiles(case_dir: str | Path) -> list[Path]:
    """
    Discovers WarpX plotfile or openPMD diagnostic directories within a case directory.
    Searches in case_dir/diags/, case_dir/plotfiles/, and case_dir root.
    """
    path = Path(case_dir)
    if not path.is_dir():
        return []

    candidates: list[Path] = []
    search_dirs = [path / "diags", path / "plotfiles", path]

    for sdir in search_dirs:
        if sdir.is_dir():
            for p in sdir.glob("diag*"):
                if p.is_dir():
                    candidates.append(p)
            for p in sdir.glob("plt*"):
                if p.is_dir():
                    candidates.append(p)

    def extract_index(p: Path) -> int:
        digits = "".join(filter(str.isdigit, p.name))
        return int(digits) if digits else 0

    return sorted(list(set(candidates)), key=extract_index)


def load_plotfile_densities(plotfile_path: str | Path) -> dict[str, Any] | None:
    """
    Attempts to read species grid densities and spatial coordinates from a WarpX plotfile.
    Returns None if yt or openPMD is not installed or plotfile cannot be read.
    """
    p = Path(plotfile_path)
    if not p.exists():
        return None

    try:
        import yt  # type: ignore
        ds = yt.load(str(p))
        return {
            "plotfile": str(p),
            "time": float(ds.current_time),
            "yt_ds": ds,
        }
    except Exception:
        return None



# ── Git / environment introspection ───────────────────────────────────────────

def get_git_info(path: Path) -> dict[str, str]:
    """Return git commit, branch, dirty flag, and short status for *path*.

    Args:
        path: Root of a git repository to inspect.

    Returns:
        Dict with keys ``commit``, ``branch``, ``dirty``, ``status``.
        Returns ``{"error": "<msg>"}`` if the path does not exist or git fails.
    """
    import subprocess

    if not path.is_dir():
        return {"error": f"Path {path} does not exist"}

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=path, text=True
        ).strip()
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=path, text=True
        ).strip()
        status_short = subprocess.check_output(
            ["git", "status", "--short"], cwd=path, text=True
        ).strip()
        return {
            "commit": commit,
            "branch": branch,
            "dirty": bool(status_short),
            "status": status_short if status_short else "Clean",
        }
    except Exception as exc:
        return {"error": str(exc)}


def collect_metadata(
    case_config: SimulationCaseConfig,
    case_path: Path,
    *,
    project_root: Path | None = None,
    warpx_dir: Path | None = None,
) -> dict[str, Any]:
    """Build a machine-readable metadata dict for a simulation run.

    Captures the git state of this repository and the WarpX source tree,
    the conda environment, and the full validated case configuration.
    Written to ``metadata.json`` in each case output directory.

    Args:
        case_config: Validated :class:`SimulationCaseConfig` for this run.
        case_path:   Path to the YAML case file that was loaded.
        project_root: Root of the plasma_column repo (auto-detected if None).
        warpx_dir:   Path to the WarpX source tree (uses project default if None).

    Returns:
        Dict ready for ``json.dump``.
    """
    import datetime
    import os
    import sys

    if project_root is None:
        # Resolve upward from this file: src/plasma_column/warpx_io.py -> repo root
        project_root = Path(__file__).resolve().parent.parent.parent

    if warpx_dir is None:
        warpx_dir = Path("/home/cspark/Work/simulation_codes-working/warpx")

    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "case_file": str(Path(case_path).resolve()),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "python_executable": sys.executable,
        "plasma_column_repo": get_git_info(project_root),
        "warpx_source": {
            "path": str(warpx_dir),
            "git": get_git_info(warpx_dir),
        },
        "case_config": case_config.to_dict(),
    }


__all__ = [
    "save_metadata",
    "find_plotfiles",
    "load_plotfile_densities",
    "get_git_info",
    "collect_metadata",
    "SimulationCaseConfig",
    "BeamConfig",
    "PlasmaConfig",
    "SolenoidConfig",
    "NumericsConfig",
]

