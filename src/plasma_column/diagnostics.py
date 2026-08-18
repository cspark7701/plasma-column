"""
src/plasma_column/diagnostics.py

Diagnostic parsing routines for particle numbers, species population tracking,
global neutralization metrics, local core space-charge compensation, z-resolved profiles,
radial charge-density diagnostics, and in-memory data caching via DataLoader.
"""

from __future__ import annotations

import json
import threading
import warnings
from pathlib import Path
from typing import Any, Optional
import numpy as np
import pandas as pd
from scipy.stats import binned_statistic

from plasma_column.constants import ELEMENTARY_CHARGE
from plasma_column.neutralization import compute_neutralization_ratios

GLOBAL_WARNING_MSG = (
    "WARNING: local neutralization cannot be inferred from global particle count alone."
)


def warn_global_count_limitation() -> None:
    """
    Issues an explicit warning that global particle-number ratios do not guarantee local space-charge compensation.
    """
    print(GLOBAL_WARNING_MSG)
    warnings.warn(
        "Global particle-number ratios (Ne/Np, Ni/Np) reflect domain-wide counts "
        "and DO NOT guarantee local space-charge compensation inside the beam core "
        "within the plasma column cell.",
        UserWarning,
        stacklevel=2,
    )


class DataLoader:
    """
    Lightweight, thread-safe diagnostic data loader with in-memory caching
    and timestamp (st_mtime) invalidation to accelerate analysis workflows.
    """
    _cache: dict[tuple[Path, float], Any] = {}
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def clear_cache(cls) -> None:
        """Clears all cached DataFrames and metadata dictionaries in a thread-safe manner."""
        with cls._lock:
            cls._cache.clear()

    @classmethod
    def cache_info(cls) -> dict[str, int]:
        """Returns statistics on currently cached files in a thread-safe manner."""
        with cls._lock:
            return {"cached_entries": len(cls._cache)}

    @classmethod
    def load_particle_number(cls, filepath: str | Path, use_cache: bool = True) -> pd.DataFrame:
        """Loads and parses ParticleNumber diagnostic file with thread-safe mtime caching."""
        path = Path(filepath).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Particle number diagnostic file not found: {path}")

        mtime = path.stat().st_mtime
        key = (path, mtime)

        if use_cache:
            with cls._lock:
                if key in cls._cache:
                    return cls._cache[key].copy()

        df = load_particle_number_diagnostic(path, use_cache=False)
        if use_cache:
            with cls._lock:
                cls._cache[key] = df.copy()
        return df

    @classmethod
    def load_local_neutralization(cls, filepath: str | Path, use_cache: bool = True) -> pd.DataFrame:
        """Loads local_neutralization.csv DataFrame with thread-safe mtime caching."""
        path = Path(filepath).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Local neutralization file not found: {path}")

        mtime = path.stat().st_mtime
        key = (path, mtime)

        if use_cache:
            with cls._lock:
                if key in cls._cache:
                    return cls._cache[key].copy()

        df = pd.read_csv(path)
        if use_cache:
            with cls._lock:
                cls._cache[key] = df.copy()
        return df

    @classmethod
    def load_case_metadata(cls, filepath: str | Path, use_cache: bool = True) -> dict[str, Any]:
        """Loads metadata.json dictionary with thread-safe mtime caching."""
        path = Path(filepath).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Metadata file not found: {path}")

        mtime = path.stat().st_mtime
        key = (path, mtime)

        if use_cache:
            with cls._lock:
                if key in cls._cache:
                    return dict(cls._cache[key])

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if use_cache:
            with cls._lock:
                cls._cache[key] = dict(data)
        return data


def load_particle_number_diagnostic(filepath: str | Path, use_cache: bool = False) -> pd.DataFrame:
    """
    Parses WarpX ParticleNumber reduced diagnostic text file into a structured pandas DataFrame.
    Supports both comma-separated and space-separated formats with header comments.
    """
    if use_cache:
        return DataLoader.load_particle_number(filepath, use_cache=True)

    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Particle number diagnostic file not found: {path}")

    header_line = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                header_line = line.strip("# \n")
            else:
                break

    data = np.genfromtxt(path, comments="#")
    if data.ndim == 1 and (np.isnan(data).any() or data.size == 0):
        data = np.genfromtxt(path, comments="#", delimiter=",")

    if data.size == 0:
        return pd.DataFrame()

    if data.ndim == 1:
        data = data.reshape(1, -1)

    ncols = data.shape[1]

    if header_line:
        clean_header = header_line.replace(",", " ").split()
        if len(clean_header) == ncols:
            cols = clean_header
        else:
            cols = [f"col_{i}" for i in range(ncols)]
    else:
        cols = [f"col_{i}" for i in range(ncols)]

    df = pd.DataFrame(data, columns=cols)

    if "step" not in df.columns and ncols >= 1:
        df.rename(columns={cols[0]: "step"}, inplace=True)
    if "time" not in df.columns and ncols >= 2:
        df.rename(columns={cols[1]: "time"}, inplace=True)

    if "Np" not in df.columns:
        if ncols >= 8:
            df["Np"] = data[:, 5]
            df["Ne"] = data[:, 6]
            df["Ni"] = data[:, 7]
        elif ncols >= 5:
            df["Np"] = data[:, 2]
            df["Ne"] = data[:, 3]
            df["Ni"] = data[:, 4]

    return df


def safe_eta(
    ne: float | np.ndarray,
    ni: float | np.ndarray,
    np_val: float | np.ndarray,
    eps: float = 1.0e-30,
) -> tuple[Any, Any]:
    """Calculates (eta_electron_only, eta_net) with guarded division.

    Args:
        ne: Electron count or density (scalar or array).
        ni: Ion count or density (scalar or array).
        np_val: Proton/beam count or density (scalar or array).
        eps: Epsilon denominator guard against division by zero.

    Returns:
        Tuple of (eta_electron_only, eta_net).
    """
    denom = np_val + eps
    eta_e = ne / denom
    eta_net = (ne - ni) / denom
    return eta_e, eta_net


def compute_particle_number_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates neutralization fractions and effective perveance ratios from particle counts.
    Issues global count warning per project rules.
    """
    warn_global_count_limitation()

    if df.empty or "Np" not in df.columns or "Ne" not in df.columns:
        return df

    out = df.copy()
    Np = out["Np"].values.astype(float)
    Ne = out["Ne"].values.astype(float)
    Ni = out["Ni"].values.astype(float) if "Ni" in out.columns else np.zeros_like(Np)

    eta_e, eta_net = safe_eta(Ne, Ni, Np)

    out["eta_electron_only"] = eta_e
    out["eta_net"] = eta_net
    out["keff_over_k0"] = np.maximum(0.0, 1.0 - eta_net)
    out["keff_over_k0_electron_only"] = np.maximum(0.0, 1.0 - eta_e)

    return out


def compute_local_core_neutralization(
    ne_3d: np.ndarray,
    ni_3d: np.ndarray,
    np_3d: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    z_coords: np.ndarray,
    r_core: float = 0.002,
    z_min_col: float = 0.0,
    z_max_col: float = 0.20,
) -> dict[str, Any]:
    """
    Computes volume-averaged electron and ion densities inside the beam core within the plasma column.
    """
    X, Y, Z = np.meshgrid(x_coords, y_coords, z_coords, indexing="ij")
    R = np.sqrt(X**2 + Y**2)

    mask = (R <= r_core) & (Z >= z_min_col) & (Z <= z_max_col)
    if not np.any(mask):
        return {
            "np_core_avg": 0.0,
            "ne_core_avg": 0.0,
            "ni_core_avg": 0.0,
            "eta_electron_only_local": 0.0,
            "eta_net_local": 0.0,
            "keff_over_k0_electron_only_local": 1.0,
            "keff_over_k0_local": 1.0,
            "overcompensated": False,
        }

    np_avg = float(np.mean(np_3d[mask]))
    ne_avg = float(np.mean(ne_3d[mask]))
    ni_avg = float(np.mean(ni_3d[mask]))

    eta_e, eta_net = safe_eta(ne_avg, ni_avg, np_avg)
    keff = 1.0 - float(eta_net)
    overcomp = float(eta_net) > 1.0

    return {
        "np_core_avg": np_avg,
        "ne_core_avg": ne_avg,
        "ni_core_avg": ni_avg,
        "eta_electron_only_local": float(eta_e),
        "eta_net_local": float(eta_net),
        "keff_over_k0_electron_only_local": float(1.0 - float(eta_e)),
        "keff_over_k0_local": float(keff),
        "overcompensated": overcomp,
    }


def compute_radial_density_profiles(
    ne_3d: np.ndarray,
    ni_3d: np.ndarray,
    np_3d: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    z_coords: np.ndarray,
    z_min_col: float = 0.0,
    z_max_col: float = 0.20,
    r_max: float = 0.015,
    n_bins: int = 50,
) -> pd.DataFrame:
    """
    Computes radially averaged density profiles ne(r), ni(r), np(r) within column axial range.
    """
    X, Y, Z = np.meshgrid(x_coords, y_coords, z_coords, indexing="ij")
    R = np.sqrt(X**2 + Y**2)

    z_mask = (Z >= z_min_col) & (Z <= z_max_col)
    r_vals = R[z_mask].flatten()
    np_vals = np_3d[z_mask].flatten()
    ne_vals = ne_3d[z_mask].flatten()
    ni_vals = ni_3d[z_mask].flatten()

    bin_edges = np.linspace(0, r_max, n_bins + 1)
    r_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])

    np_stat, _, _ = binned_statistic(r_vals, np_vals, statistic="mean", bins=bin_edges)
    ne_stat, _, _ = binned_statistic(r_vals, ne_vals, statistic="mean", bins=bin_edges)
    ni_stat, _, _ = binned_statistic(r_vals, ni_vals, statistic="mean", bins=bin_edges)

    np_profile = np.nan_to_num(np_stat, nan=0.0)
    ne_profile = np.nan_to_num(ne_stat, nan=0.0)
    ni_profile = np.nan_to_num(ni_stat, nan=0.0)

    rho_net = ELEMENTARY_CHARGE * (np_profile - ne_profile + ni_profile)

    return pd.DataFrame({
        "r": r_centers,
        "np_r": np_profile,
        "ne_r": ne_profile,
        "ni_r": ni_profile,
        "rho_net_r": rho_net,
    })


def compute_local_neutralization_vs_z(
    ne_3d: np.ndarray,
    ni_3d: np.ndarray,
    np_3d: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    z_coords: np.ndarray,
    r_core: float = 0.002,
) -> pd.DataFrame:
    """
    Computes axial profile of local neutralization eta(z) and K_eff/K0(z) within beam core
    using vectorized NumPy masked array reduction.
    """
    X, Y = np.meshgrid(x_coords, y_coords, indexing="ij")
    R_transverse = np.sqrt(X**2 + Y**2)
    transverse_mask = R_transverse <= r_core

    nz = len(z_coords)

    if np.any(transverse_mask):
        np_z_avg = np.mean(np_3d[transverse_mask, :], axis=0)
        ne_z_avg = np.mean(ne_3d[transverse_mask, :], axis=0)
        ni_z_avg = np.mean(ni_3d[transverse_mask, :], axis=0)

        eta_e_z, eta_net_z = safe_eta(ne_z_avg, ni_z_avg, np_z_avg)
        keff_z = 1.0 - eta_net_z
    else:
        eta_e_z = np.zeros(nz)
        eta_net_z = np.zeros(nz)
        keff_z = np.ones(nz)

    return pd.DataFrame({
        "z": z_coords,
        "eta_electron_only_local_z": eta_e_z,
        "eta_net_local_z": eta_net_z,
        "keff_over_k0_local_z": keff_z,
    })


def compute_charge_density(*args, **kwargs) -> dict[str, float]:
    """
    Calculates spatial charge density rho = e * (np - ne + ni).
    Supports either dictionary core_info or 3D density arrays (ne_3d, ni_3d, np_3d, x, y, z).
    """
    if len(args) == 1 and isinstance(args[0], dict):
        core_info = args[0]
    elif len(args) >= 3:
        ne_3d, ni_3d, np_3d = args[0], args[1], args[2]
        x_coords = args[3] if len(args) > 3 else kwargs.get("x_coords", None)
        y_coords = args[4] if len(args) > 4 else kwargs.get("y_coords", None)
        z_coords = args[5] if len(args) > 5 else kwargs.get("z_coords", None)
        r_core = kwargs.get("r_core", 0.002)
        z_min_col = kwargs.get("z_min_col", 0.0)
        z_max_col = kwargs.get("z_max_col", 0.20)
        core_info = compute_local_core_neutralization(
            ne_3d, ni_3d, np_3d, x_coords, y_coords, z_coords, r_core, z_min_col, z_max_col
        )
    else:
        core_info = kwargs

    e_charge = ELEMENTARY_CHARGE
    rho_p = e_charge * core_info.get("np_core_avg", 0.0)
    rho_e = -e_charge * core_info.get("ne_core_avg", 0.0)
    rho_i = e_charge * core_info.get("ni_core_avg", 0.0)
    rho_net = rho_p + rho_e + rho_i

    return {
        "rho_p": float(rho_p),
        "rho_e": float(rho_e),
        "rho_i": float(rho_i),
        "rho_net": float(rho_net),
    }


# Backwards compatibility alias
compute_beam_core_charge_density = compute_charge_density
