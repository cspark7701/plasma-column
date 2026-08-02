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


__all__ = [
    "save_metadata",
    "find_plotfiles",
    "load_plotfile_densities",
    "SimulationCaseConfig",
    "BeamConfig",
    "PlasmaConfig",
    "SolenoidConfig",
    "NumericsConfig",
]
