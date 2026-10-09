"""
src/plasma_column/design_estimates.py

Closed-form design estimates for the compact plasma neutralizer used by the
journal manuscript (paper/manuscript/). Every number quoted in the manuscript
text is produced by :func:`compute_design_numbers`, so text, figures and code
cannot drift apart.

All quantities are analytical, order-of-magnitude estimates for a uniform
(KV-like) round beam of edge radius ``a`` inside a grounded pipe of radius
``b``. They are not substitutes for PIC results.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from plasma_column.constants import AMU, EPSILON_0, ME, QE, estimate_cfl_timestep
from plasma_column.beam import ProtonBeam
from plasma_column.gas import gas_density_m3, get_h2_cross_section, get_kr_cross_section


# --------------------------------------------------------------------------- #
# Single-formula helpers
# --------------------------------------------------------------------------- #
def line_charge_density_C_m(current_A: float, speed_m_s: float) -> float:
    """Beam line-charge density lambda = I / v [C/m]."""
    return current_A / speed_m_s


def uniform_beam_density_m3(current_A: float, speed_m_s: float, radius_m: float) -> float:
    """Proton number density of a uniform round beam of edge radius ``radius_m`` [m^-3]."""
    return line_charge_density_C_m(current_A, speed_m_s) / (QE * math.pi * radius_m**2)


def electron_plasma_frequency_rad_s(n_e_m3: float) -> float:
    """Electron plasma frequency omega_pe [rad/s]."""
    return math.sqrt(n_e_m3 * QE**2 / (EPSILON_0 * ME))


def potential_well_depth_V(lambda_C_m: float, beam_radius_m: float, pipe_radius_m: float) -> float:
    """
    Axis-to-wall potential of an uncompensated uniform beam in a grounded pipe [V]:

        Delta Phi = lambda / (4 pi eps0) * [1 + 2 ln(b/a)]
    """
    return lambda_C_m / (4.0 * math.pi * EPSILON_0) * (1.0 + 2.0 * math.log(pipe_radius_m / beam_radius_m))


def ion_expulsion_time_s(lambda_C_m: float, beam_radius_m: float, ion_mass_kg: float,
                         r_start_fraction: float = 0.5) -> float:
    """
    Time for a singly charged ion born at rest at r0 = f*a to reach the beam edge r = a.

    Inside a uniform beam the radial field E = lambda r / (2 pi eps0 a^2) is linear,
    so r(t) = r0 cosh(t / t_i) with t_i = sqrt(2 pi eps0 a^2 M / (e lambda)).
    """
    t_i = math.sqrt(2.0 * math.pi * EPSILON_0 * beam_radius_m**2 * ion_mass_kg / (QE * lambda_C_m))
    return t_i * math.acosh(1.0 / r_start_fraction)


def electron_crossing_time_s(radius_m: float, electron_energy_eV: float) -> float:
    """Time for a free electron of kinetic energy E_e to cross one beam radius [s]."""
    return radius_m / electron_speed_m_s(electron_energy_eV)


def electron_speed_m_s(electron_energy_eV: float) -> float:
    """Non-relativistic electron speed for kinetic energy E_e [m/s]."""
    return math.sqrt(2.0 * electron_energy_eV * QE / ME)


def axial_field_for_larmor_radius_T(electron_energy_eV: float, larmor_radius_m: float) -> float:
    """Axial magnetic field giving an electron Larmor radius r_L = m v / (e B) [T]."""
    return ME * electron_speed_m_s(electron_energy_eV) / (QE * larmor_radius_m)


def laminar_envelope_drift(radius0_m: float, perveance: float, length_m: float,
                           emittance_m_rad: float = 0.0, n_steps: int = 4000) -> tuple[np.ndarray, np.ndarray]:
    """
    Integrates the round-beam envelope equation in a field-free drift,

        a'' = K / a + eps^2 / a^3,

    from a parallel beam (a'(0) = 0) with RK4. Returns (z [m], a(z) [m]).
    """
    z = np.linspace(0.0, length_m, n_steps + 1)
    h = z[1] - z[0]
    a = np.empty_like(z)
    y = np.array([radius0_m, 0.0])

    def rhs(state: np.ndarray) -> np.ndarray:
        r, rp = state
        return np.array([rp, perveance / r + emittance_m_rad**2 / r**3])

    a[0] = y[0]
    for i in range(n_steps):
        k1 = rhs(y)
        k2 = rhs(y + 0.5 * h * k1)
        k3 = rhs(y + 0.5 * h * k2)
        k4 = rhs(y + h * k3)
        y = y + (h / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        a[i + 1] = y[0]
    return z, a


def doubling_length_m(radius0_m: float, perveance: float) -> float:
    """
    Drift length over which a parallel, zero-emittance beam doubles its radius
    under perveance K (exact quadrature of a'' = K/a):

        z_2 = a0 / sqrt(2K) * int_1^2 dx / sqrt(ln x)
    """
    # Substitute x = exp(u^2): int_1^2 dx/sqrt(ln x) = 2 int_0^sqrt(ln2) exp(u^2) du
    u = np.linspace(0.0, math.sqrt(math.log(2.0)), 20001)
    integral = 2.0 * np.trapezoid(np.exp(u**2), u)
    return radius0_m / math.sqrt(2.0 * perveance) * integral


# --------------------------------------------------------------------------- #
# Aggregate design point
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DesignPoint:
    """Baseline parameters of the manuscript design point."""

    energy_keV: float = 30.0
    current_avg_mA: float = 10.0
    beam_radius_m: float = 2.0e-3
    pipe_radius_m: float = 10.0e-3
    cell_length_m: float = 0.20
    rf_frequency_hz: float = 50.0e6
    bunch_phase_width_deg: float = 36.0
    bunching_factor: float = 5.0
    pressure_h2_torr: float = 1.0e-5
    pressure_kr_torr: float = 1.0e-6
    temperature_K: float = 300.0
    secondary_electron_energy_eV: float = 10.0
    # PIC numerics: defaults of scripts/plasma_column_mcc_picmi_v7.py (PlasmaColumnConfig)
    pic_nx: int = 64
    pic_ny: int = 64
    pic_nz: int = 512
    pic_xmax_m: float = 1.0e-2
    pic_zmin_m: float = -2.0e-2
    pic_zmax_m: float = 2.4e-1
    pic_cfl: float = 0.5
    pic_steps_seeded: int = 20000
    pic_steps_dynamic: int = 120000


def compute_design_numbers(dp: DesignPoint = DesignPoint()) -> dict[str, float]:
    """Computes every analytical number quoted in the manuscript."""
    beam = ProtonBeam(energy_keV=dp.energy_keV, current_mA=dp.current_avg_mA, radius_m=dp.beam_radius_m)
    v = beam.beta * 299792458.0
    I_avg = dp.current_avg_mA * 1e-3
    I_peak = dp.bunching_factor * I_avg

    lam_avg = line_charge_density_C_m(I_avg, v)
    lam_peak = line_charge_density_C_m(I_peak, v)
    n_b_avg = uniform_beam_density_m3(I_avg, v, dp.beam_radius_m)
    n_b_peak = dp.bunching_factor * n_b_avg

    sig_h2 = get_h2_cross_section(dp.energy_keV)
    sig_kr = get_kr_cross_section(dp.energy_keV)
    n_h2 = gas_density_m3(dp.pressure_h2_torr, dp.temperature_K)
    n_kr = gas_density_m3(dp.pressure_kr_torr, dp.temperature_K)
    tau_h2 = 1.0 / (n_h2 * sig_h2 * v)
    tau_kr = 1.0 / (n_kr * sig_kr * v)

    K0 = beam.perveance_K0
    pic_dt = estimate_cfl_timestep(2 * dp.pic_xmax_m / dp.pic_nx, 2 * dp.pic_xmax_m / dp.pic_ny,
                                   (dp.pic_zmax_m - dp.pic_zmin_m) / dp.pic_nz, dp.pic_cfl)
    T_rf = 1.0 / dp.rf_frequency_hz
    dt_b = dp.bunch_phase_width_deg / 360.0 * T_rf

    out = {
        "beta": beam.beta,
        "v_m_s": v,
        "I_avg_A": I_avg,
        "I_peak_A": I_peak,
        "K0": K0,
        "K0_peak": dp.bunching_factor * K0,
        "lambda_avg_C_m": lam_avg,
        "n_beam_avg_m3": n_b_avg,
        "n_beam_peak_m3": n_b_peak,
        "sigma_h2_m2": sig_h2,
        "sigma_kr_m2": sig_kr,
        "sigma_ratio_kr_h2": sig_kr / sig_h2,
        "n_h2_m3": n_h2,
        "n_kr_m3": n_kr,
        "tau_h2_s": tau_h2,
        "tau_kr_s": tau_kr,
        "p_kr_equal_tau_torr": dp.pressure_h2_torr * sig_h2 / sig_kr,
        "ionization_prob_per_pass_h2": n_h2 * sig_h2 * dp.cell_length_m,
        "ionization_prob_per_pass_kr": n_kr * sig_kr * dp.cell_length_m,
        "cell_transit_s": dp.cell_length_m / v,
        "T_rf_s": T_rf,
        "bunch_duration_s": dt_b,
        "bunch_length_m": v * dt_b,
        "bunch_gap_s": T_rf - dt_b,
        "uniform_fill_bunching_factor": 360.0 / dp.bunch_phase_width_deg,
        "omega_pe_avg_rad_s": electron_plasma_frequency_rad_s(n_b_avg),
        "omega_pe_peak_rad_s": electron_plasma_frequency_rad_s(n_b_peak),
        "well_depth_avg_V": potential_well_depth_V(lam_avg, dp.beam_radius_m, dp.pipe_radius_m),
        "well_depth_peak_V": potential_well_depth_V(lam_peak, dp.beam_radius_m, dp.pipe_radius_m),
        "t_expel_h2p_avg_s": ion_expulsion_time_s(lam_avg, dp.beam_radius_m, 2.01588 * AMU),
        "t_expel_krp_avg_s": ion_expulsion_time_s(lam_avg, dp.beam_radius_m, 83.798 * AMU),
        "t_expel_h2p_peak_s": ion_expulsion_time_s(lam_peak, dp.beam_radius_m, 2.01588 * AMU),
        "t_expel_krp_peak_s": ion_expulsion_time_s(lam_peak, dp.beam_radius_m, 83.798 * AMU),
        "t_electron_cross_s": electron_crossing_time_s(dp.beam_radius_m, dp.secondary_electron_energy_eV),
        "pic_dt_s": pic_dt,
        "pic_duration_s": pic_dt * dp.pic_steps_seeded,
        "pic_duration_dynamic_s": pic_dt * dp.pic_steps_dynamic,
        "z_double_K0_m": doubling_length_m(dp.beam_radius_m, K0),
        "z_double_K0_peak_m": doubling_length_m(dp.beam_radius_m, dp.bunching_factor * K0),
    }
    # Free longitudinal escape of a secondary electron from the gas cell, and the
    # resulting ceiling eta ~ tau_conf / tau on cell-local neutralization.
    out["t_electron_escape_cell_s"] = dp.cell_length_m / electron_speed_m_s(dp.secondary_electron_energy_eV)
    out["eta_free_escape_h2"] = out["t_electron_escape_cell_s"] / tau_h2
    out["eta_free_escape_kr"] = out["t_electron_escape_cell_s"] / tau_kr
    out["ion_fraction_h2"] = out["t_expel_h2p_avg_s"] / tau_h2
    out["ion_fraction_kr"] = out["t_expel_krp_avg_s"] / tau_kr
    out["B_confine_T"] = axial_field_for_larmor_radius_T(dp.secondary_electron_energy_eV, dp.beam_radius_m / 10.0)
    out["pic_duration_over_tau_h2"] = out["pic_duration_dynamic_s"] / tau_h2
    out["omega_pe_peak_times_bunch"] = out["omega_pe_peak_rad_s"] * dt_b
    return out


def design_point_dict(dp: DesignPoint = DesignPoint()) -> dict[str, float]:
    """Returns the design-point inputs as a plain dict (for metadata)."""
    return asdict(dp)


__all__ = [
    "DesignPoint",
    "compute_design_numbers",
    "design_point_dict",
    "doubling_length_m",
    "axial_field_for_larmor_radius_T",
    "electron_crossing_time_s",
    "electron_speed_m_s",
    "electron_plasma_frequency_rad_s",
    "ion_expulsion_time_s",
    "laminar_envelope_drift",
    "line_charge_density_C_m",
    "potential_well_depth_V",
    "uniform_beam_density_m3",
]
