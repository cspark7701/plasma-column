"""
src/plasma_column/bunched_cell.py

RF-averaged vs peak-bunch neutralization of a bunched beam inside the plasma cell, from one
WarpX density snapshot (task B2 of docs/physics_notes/simulation_strategy_tasks.md).

The bunches are spatially separated by the RF wavelength lambda_RF = v_beam / f_RF (4.8 cm for
30 keV protons at 50 MHz), so one snapshot of a 20 cm cell holds about four bunches. Along z, in
the beam core (r <= r_core):

    eta_avg   = sum (n_e - n_i) / sum n_p over a whole number of RF wavelengths
    eta_peak  = sum (n_e - n_i) / sum n_p over the z-bins of the top peak_fraction of lambda_p
                (0.1: the 36 deg acceptance window, i.e. the peak bunch the cyclotron takes)
    K_eff,peak / K0,peak = 1 - eta_peak     (negative = overcompensated, labeled)

and the bunching factor seen in the cell, B_cell = max(lambda_p) / mean(lambda_p) over those
wavelengths, from the proton line density lambda_p(z) over the whole cross-section. The peak-bunch
bins are also chosen on lambda_p, so that the transverse growth of the beam along z (which changes
the core density) is not mistaken for bunching. For an electron cloud that does not follow the bunches,
eta_peak ~ eta_avg / B_cell (AGENTS.md: K_eff,peak / K0,peak ~ 1 - eta_avg / B_f).
"""

from __future__ import annotations

import math

import numpy as np

from plasma_column.constants import MP, QE


def beam_speed_m_s(kinetic_energy_eV: float) -> float:
    """Relativistic proton speed [m/s]."""
    gamma = 1.0 + kinetic_energy_eV * QE / (MP * 299792458.0**2)
    return 299792458.0 * math.sqrt(1.0 - 1.0 / gamma**2)


def rf_wavelength_m(kinetic_energy_eV: float, rf_frequency_hz: float) -> float:
    """Bunch spacing lambda_RF = v / f_RF [m]."""
    return beam_speed_m_s(kinetic_energy_eV) / rf_frequency_hz


def core_z_profiles(ne_3d: np.ndarray, ni_3d: np.ndarray, np_3d: np.ndarray,
                    x: np.ndarray, y: np.ndarray, z: np.ndarray,
                    r_core_m: float = 0.002) -> dict[str, np.ndarray]:
    """
    Densities averaged over the core cross-section r <= r_core, as functions of z [m^-3], and the
    proton line density over the whole cross-section [m^-1].
    """
    X, Y = np.meshgrid(x, y, indexing="ij")
    core = np.sqrt(X**2 + Y**2) <= r_core_m
    if not np.any(core):
        raise ValueError("no grid cell inside r_core")
    area = (x[1] - x[0]) * (y[1] - y[0]) if len(x) > 1 and len(y) > 1 else 1.0
    return {"z": np.asarray(z, float),
            "ne": ne_3d[core].mean(axis=0), "ni": ni_3d[core].mean(axis=0), "np": np_3d[core].mean(axis=0),
            "np_line": np_3d.sum(axis=(0, 1)) * area}


def bunch_metrics(prof: dict[str, np.ndarray], z_start_m: float, wavelength_m: float, n_wavelengths: int,
                  peak_fraction: float = 0.1) -> dict[str, float]:
    """eta_avg, eta_peak, B_cell and the electron modulation over n whole RF wavelengths from z_start."""
    z = prof["z"]
    m = (z >= z_start_m) & (z < z_start_m + n_wavelengths * wavelength_m)
    ne, ni, npr = prof["ne"][m], prof["ni"][m], prof["np"][m]
    lam = prof.get("np_line", prof["np"])[m]
    nan = {k: float("nan") for k in ("eta_avg", "eta_peak", "keff_over_k0_peak", "bunching_factor_cell",
                                      "ne_modulation", "eta_gap_excess")}
    if npr.size == 0 or npr.max() <= 0 or lam.max() <= 0:
        return nan
    net = ne - ni
    eta_avg = float(net.sum() / npr.sum())
    peak = lam >= np.quantile(lam, 1.0 - peak_fraction)
    eta_peak = float(net[peak].sum() / npr[peak].sum())
    gap = lam < 0.1 * lam.max()
    return {
        "eta_avg": eta_avg,
        "eta_peak": eta_peak,
        "keff_over_k0_peak": 1.0 - eta_peak,
        "bunching_factor_cell": float(lam.max() / lam.mean()),
        # Relative modulation of n_e along z: ~0 if the electrons do not follow the bunches.
        "ne_modulation": float(ne.std() / ne.mean()) if ne.mean() > 0 else float("nan"),
        # Net negative charge left in the gaps, relative to the mean beam density.
        "eta_gap_excess": float(net[gap].mean() / npr.mean()) if np.any(gap) else float("nan"),
    }
