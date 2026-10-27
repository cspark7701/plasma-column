"""
src/plasma_column/beam_quality.py

Beam rms size, divergence and emittance in z-slabs from WarpX plotfile particle data
(species beam_protons; written by the seeded driver's ParticleDiagnostic).

Used to check how the plasma-column settings (cell solenoid field, analytic end plugs) change the
beam at the cell exit (docs/physics_notes/simulation_strategy_tasks.md, task C3).

Definitions (weighted by macroparticle weight, per plane u = x, y):
    u' = p_u / p_z
    eps_rms = sqrt(<du^2><du'^2> - <du du'>^2), with du = u - <u>
    eps_n,rms = beta_z gamma * eps_rms, beta_z gamma = <p_z> / (m_p c)
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from plasma_column.constants import C, MP

BEAM_SPECIES = "beam_protons"


def load_beam_particles(plotfile_path: str | Path, species: str = BEAM_SPECIES) -> dict[str, np.ndarray | float]:
    """Positions [m], momenta [kg m/s], weights and time [s] of one species from a plotfile (yt)."""
    import yt  # type: ignore

    yt.set_log_level(50)
    ds = yt.load(str(plotfile_path))
    ad = ds.all_data()
    out: dict[str, np.ndarray | float] = {"time": float(ds.current_time)}
    if (species, "particle_weight") not in ds.field_list:  # e.g. t = 0, before injection
        return {**out, **{k: np.empty(0) for k in ("x", "y", "z", "px", "py", "pz", "w")}}
    for key, field in (("x", "position_x"), ("y", "position_y"), ("z", "position_z"),
                       ("px", "momentum_x"), ("py", "momentum_y"), ("pz", "momentum_z"), ("w", "weight")):
        out[key] = np.asarray(ad[(species, f"particle_{field}")].v, float)
    return out


def _wmean(a: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(a * w) / np.sum(w))


def slab_beam_moments(p: dict, z_min_m: float, z_max_m: float) -> dict[str, float]:
    """Weighted rms moments of the particles with z_min <= z < z_max (NaN if fewer than 10)."""
    m = (p["z"] >= z_min_m) & (p["z"] < z_max_m) & (p["pz"] > 0)
    nan = {k: math.nan for k in ("n_macro", "x_rms_mm", "y_rms_mm", "xp_rms_mrad", "yp_rms_mrad",
                                  "eps_n_rms_x_mm_mrad", "eps_n_rms_y_mm_mrad", "kinetic_energy_keV")}
    if m.sum() < 10:
        return {**nan, "n_macro": float(m.sum())}
    w = p["w"][m]
    pz = p["pz"][m]
    bg = _wmean(pz, w) / (MP * C)
    res = {"n_macro": float(m.sum())}
    for u, pu in (("x", "px"), ("y", "py")):
        du = p[u][m] - _wmean(p[u][m], w)
        up = p[pu][m] / pz
        dup = up - _wmean(up, w)
        s11, s22, s12 = _wmean(du * du, w), _wmean(dup * dup, w), _wmean(du * dup, w)
        res[f"{u}_rms_mm"] = math.sqrt(s11) * 1e3
        res[f"{u}p_rms_mrad"] = math.sqrt(s22) * 1e3
        res[f"eps_n_rms_{u}_mm_mrad"] = bg * math.sqrt(max(s11 * s22 - s12**2, 0.0)) * 1e6
    p2 = p["px"][m] ** 2 + p["py"][m] ** 2 + pz**2
    res["kinetic_energy_keV"] = _wmean(p2 / (2.0 * MP), w) / 1.602176634e-16
    return res
