"""
src/plasma_column/neutralization.py

Core neutralization physics module providing analytical calculations for:
- Gas density and ionization time constants
- Beam relativistic velocity (beta, gamma, speed)
- Neutralization buildup fraction eta(t)
- Effective perveance reduction ratios K_eff / K0
- Bunched-beam peak perveance and phase/length calculations
"""

from __future__ import annotations

import math
import warnings
from typing import Union
import numpy as np

from plasma_column.constants import C, QE, MP, KB, TORR_TO_PA
import plasma_column.gas as _gas

ArrayOrFloat = Union[float, np.ndarray]


def gas_density_m3(pressure_torr: float, temperature_K: float = 300.0) -> float:
    """
    Computes ideal gas number density n_gas [m^-3] from pressure in Torr and temperature in K.

    .. deprecated:: 0.2.0
       Use :func:`plasma_column.gas.gas_density_m3` or :attr:`plasma_column.gas.NeutralGas.number_density`.
    """
    warnings.warn(
        "gas_density_m3 has moved to plasma_column.gas (or use NeutralGas.number_density).",
        DeprecationWarning,
        stacklevel=2,
    )
    return _gas.gas_density_m3(pressure_torr, temperature_K)


def proton_beta_gamma_speed(kinetic_energy_keV: float = 30.0) -> tuple[float, float, float]:
    """
    Computes relativistic beta, gamma, and beam speed [m/s] for a proton of given kinetic energy in keV.

    .. deprecated:: 0.2.0
       Use :class:`plasma_column.beam.ProtonBeam` properties (beta, gamma, velocity).
    """
    warnings.warn(
        "proton_beta_gamma_speed is deprecated; use ProtonBeam properties in plasma_column.beam.",
        DeprecationWarning,
        stacklevel=2,
    )
    from plasma_column.beam import ProtonBeam
    b = ProtonBeam(energy_keV=kinetic_energy_keV)
    return b.beta, b.gamma, b.velocity


def ionization_tau_s(n_gas_m3: float, sigma_m2: float, beam_speed_m_s: float) -> float:
    """
    Computes characteristic ionization buildup time tau [s]:
    Formula: tau = 1 / (n_gas * sigma * v_beam)

    .. deprecated:: 0.2.0
       Use :func:`plasma_column.gas.ionization_tau_s`.
    """
    warnings.warn(
        "ionization_tau_s has moved to plasma_column.gas.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _gas.ionization_tau_s(n_gas_m3, sigma_m2, beam_speed_m_s)


def neutralization_fraction(
    t_s: ArrayOrFloat, tau_s: float, eta_ss: float = 1.0
) -> ArrayOrFloat:
    """
    Analytic neutralization fraction build-up curve:
    Formula: eta(t) = eta_ss * (1 - exp(-t / tau))
    """
    if math.isinf(tau_s) or tau_s <= 0:
        if isinstance(t_s, np.ndarray):
            return np.zeros_like(t_s, dtype=float)
        return 0.0
    if isinstance(t_s, np.ndarray):
        return eta_ss * (1.0 - np.exp(-t_s / tau_s))
    return eta_ss * (1.0 - math.exp(-t_s / tau_s))


def keff_over_k0_from_eta(eta: ArrayOrFloat) -> ArrayOrFloat:
    """
    Computes effective perveance ratio K_eff / K0 from net neutralization fraction eta_net.
    Formula: K_eff / K0 = 1 - eta_net
    """
    return 1.0 - eta


def bunch_length_s(rf_frequency_hz: float, phase_width_deg: float) -> float:
    """
    Computes RF bunch temporal width Delta_t_b [s] from RF frequency in Hz and phase width in degrees.

    .. deprecated:: 0.2.0
       Use :attr:`plasma_column.beam.RFFocusedBeam.bunch_duration_s`.
    """
    warnings.warn(
        "bunch_length_s is deprecated; use RFFocusedBeam.bunch_duration_s in plasma_column.beam.",
        DeprecationWarning,
        stacklevel=2,
    )
    from plasma_column.beam import RFFocusedBeam
    rf = RFFocusedBeam(rf_frequency_hz=rf_frequency_hz, bunch_phase_width_deg=phase_width_deg)
    return rf.bunch_duration_s


def bunch_length_m(
    beam_speed_m_s: float, rf_frequency_hz: float, phase_width_deg: float
) -> float:
    """
    Computes RF bunch spatial width Delta_z_b [m] from beam speed, RF frequency, and phase width in degrees.

    .. deprecated:: 0.2.0
       Use :attr:`plasma_column.beam.RFFocusedBeam.bunch_length_m`.
    """
    warnings.warn(
        "bunch_length_m is deprecated; use RFFocusedBeam.bunch_length_m in plasma_column.beam.",
        DeprecationWarning,
        stacklevel=2,
    )
    from plasma_column.beam import RFFocusedBeam
    rf = RFFocusedBeam(rf_frequency_hz=rf_frequency_hz, bunch_phase_width_deg=phase_width_deg)
    return beam_speed_m_s * rf.bunch_duration_s


def peak_keff_over_k0_from_average_eta(
    eta_avg: ArrayOrFloat, bunching_factor: float
) -> ArrayOrFloat:
    """
    Computes approximate peak-bunch effective perveance ratio:
    Formula: K_eff,peak / K0,peak ~= 1 - eta_avg / B_f
    """
    if bunching_factor <= 0:
        raise ValueError("bunching_factor must be positive")
    return 1.0 - (eta_avg / bunching_factor)


def compute_neutralization_ratios(
    N_p: float, N_e: float, N_i: float
) -> tuple[float, float, float, float]:
    """
    Computes neutralization metrics:
    - eta_electron_only = N_e / N_p
    - eta_net = (N_e - N_i) / N_p
    - K_eff_electron_only / K0 = 1 - eta_electron_only
    - K_eff_net / K0 = 1 - eta_net
    """
    if N_p <= 0:
        return 0.0, 0.0, 1.0, 1.0

    eta_electron_only = N_e / N_p
    eta_net = (N_e - N_i) / N_p

    k_ratio_electron_only = 1.0 - eta_electron_only
    k_ratio_net = 1.0 - eta_net

    return eta_electron_only, eta_net, k_ratio_electron_only, k_ratio_net
