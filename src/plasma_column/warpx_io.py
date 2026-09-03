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


def find_checkpoints(case_dir: str | Path) -> list[Path]:
    """
    Discovers WarpX checkpoint directories (e.g. chk000100/, chk000200/) within a case directory.
    Searches in case_dir/checkpoints/, case_dir/diags/, and case_dir root.
    Returns sorted list of checkpoint paths ordered by time-step number.
    """
    path = Path(case_dir)
    if not path.is_dir():
        return []

    candidates: list[Path] = []
    search_dirs = [path / "checkpoints", path / "diags", path]

    for sdir in search_dirs:
        if sdir.is_dir():
            for p in sdir.glob("chk*"):
                if p.is_dir() and (p / "WarpXHeader").exists():
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
        import numpy as np  # type: ignore
        from plasma_column.constants import ELEMENTARY_CHARGE

        ds = yt.load(str(p))
        nx, ny, nz = ds.domain_dimensions
        x = np.linspace(float(ds.domain_left_edge[0]), float(ds.domain_right_edge[0]), nx)
        y = np.linspace(float(ds.domain_left_edge[1]), float(ds.domain_right_edge[1]), ny)
        z = np.linspace(float(ds.domain_left_edge[2]), float(ds.domain_right_edge[2]), nz)

        result: dict[str, Any] = {
            "plotfile": str(p),
            "time": float(ds.current_time),
            "yt_ds": ds,
            "x": x,
            "y": y,
            "z": z,
            "ne_3d": np.zeros((nx, ny, nz)),
            "ni_3d": np.zeros((nx, ny, nz)),
            "np_3d": np.zeros((nx, ny, nz)),
        }

        # Attempt 1: extract species charge density grids from field diagnostics (e.g. boxlib rho_<species>)
        try:
            cg = ds.covering_grid(level=0, left_edge=ds.domain_left_edge, dims=ds.domain_dimensions)
            field_list = [f[1] for f in ds.field_list] if hasattr(ds, "field_list") else []

            for f in field_list:
                f_lower = f.lower()
                if "electron" in f_lower or "rho_plasma_electrons" in f:
                    result["ne_3d"] = np.abs(np.array(cg[("boxlib", f)])) / ELEMENTARY_CHARGE
                elif "proton" in f_lower or "beam" in f_lower or "rho_beam_protons" in f:
                    result["np_3d"] = np.abs(np.array(cg[("boxlib", f)])) / ELEMENTARY_CHARGE
                elif "ion" in f_lower or "rho_gas_ions" in f:
                    result["ni_3d"] = np.abs(np.array(cg[("boxlib", f)])) / ELEMENTARY_CHARGE
        except Exception:
            pass

        # Attempt 2: if field density grids were absent or empty, reconstruct 3D number density
        # from particle positions and weights (particle diagnostics)
        if not np.any(result["np_3d"]) and hasattr(ds, "particle_types"):
            try:
                ad = ds.all_data()
                x_edges = np.linspace(float(ds.domain_left_edge[0]), float(ds.domain_right_edge[0]), nx + 1)
                y_edges = np.linspace(float(ds.domain_left_edge[1]), float(ds.domain_right_edge[1]), ny + 1)
                z_edges = np.linspace(float(ds.domain_left_edge[2]), float(ds.domain_right_edge[2]), nz + 1)
                dx = (float(ds.domain_right_edge[0]) - float(ds.domain_left_edge[0])) / nx
                dy = (float(ds.domain_right_edge[1]) - float(ds.domain_left_edge[1])) / ny
                dz = (float(ds.domain_right_edge[2]) - float(ds.domain_left_edge[2])) / nz
                dV = float(dx * dy * dz)

                if dV > 0:
                    for ptype in ds.particle_types:
                        plower = ptype.lower()
                        if plower in ("all", "nbody"):
                            continue
                        try:
                            px = np.array(ad[(ptype, "particle_position_x")])
                            if len(px) == 0:
                                continue
                            py = np.array(ad[(ptype, "particle_position_y")])
                            pz = np.array(ad[(ptype, "particle_position_z")])
                            pw = np.array(ad[(ptype, "particle_weight")])

                            H, _ = np.histogramdd((px, py, pz), bins=(x_edges, y_edges, z_edges), weights=pw)
                            dens = H / dV

                            if "proton" in plower or "beam" in plower:
                                result["np_3d"] += dens
                            elif "electron" in plower:
                                result["ne_3d"] += dens
                            elif "ion" in plower:
                                result["ni_3d"] += dens
                        except Exception:
                            continue
            except Exception:
                pass

        return result
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
    "find_checkpoints",
    "load_plotfile_densities",
    "get_git_info",
    "collect_metadata",
    "SimulationCaseConfig",
    "BeamConfig",
    "PlasmaConfig",
    "SolenoidConfig",
    "NumericsConfig",
]

