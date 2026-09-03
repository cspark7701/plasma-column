"""
src/plasma_column/beam.py

Beam physics calculations, relativistic kinematics, perveance formulas,
and RF bunched beam model definitions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Union
import numpy as np
from plasma_column.constants import C, QE, MP, EPSILON_0


@dataclass
class ProtonBeam:
    """Proton beam physics parameters for continuous (DC) beam."""
    energy_keV: float = 30.0
    current_mA: float = 10.0
    radius_m: float = 2.0e-3
    rms_divergence: float = 0.0

    @property
    def energy_joules(self) -> float:
        return self.energy_keV * 1000.0 * QE

    @property
    def gamma(self) -> float:
        return 1.0 + (self.energy_joules / (MP * C**2))

    @property
    def beta(self) -> float:
        g = self.gamma
        return math.sqrt(1.0 - 1.0 / (g**2))

    @property
    def velocity(self) -> float:
        return self.beta * C

    @property
    def current_A(self) -> float:
        return self.current_mA * 1.0e-3

    @property
    def perveance_K0(self) -> float:
        """Generalized uncompensated beam perveance K0."""
        b = self.beta
        g = self.gamma
        return (QE * self.current_A) / (2.0 * math.pi * EPSILON_0 * MP * (b * C)**3 * (g**3))


@dataclass
class RFFocusedBeam(ProtonBeam):
    """
    RF-bunched proton beam model downstream of the upstream buncher.
    """
    rf_frequency_hz: float = 50.0e6
    bunch_phase_width_deg: float = 36.0
    bunching_factor: float = 5.0

    @property
    def beam_current_average_mA(self) -> float:
        return self.current_mA

    @property
    def beam_current_peak_mA(self) -> float:
        return self.current_mA * self.bunching_factor

    @property
    def bunch_duration_s(self) -> float:
        """Bunch temporal width Delta_t_b [s]."""
        return (self.bunch_phase_width_deg / 360.0) / self.rf_frequency_hz

    @property
    def bunch_length_m(self) -> float:
        """Bunch spatial length Delta_z_b [m]."""
        return self.velocity * self.bunch_duration_s

    @property
    def bunch_charge_C(self) -> float:
        """Total electric charge per RF bunch Q_bunch = I_avg / f_RF [C]."""
        if self.rf_frequency_hz <= 0.0:
            raise ValueError("rf_frequency_hz must be positive")
        return self.current_A / self.rf_frequency_hz

    @property
    def peak_perveance_K0(self) -> float:
        """Uncompensated peak perveance K0,peak."""
        return self.perveance_K0 * self.bunching_factor

    def peak_effective_perveance_ratio(self, eta_avg: float) -> float:
        """
        Computes peak-bunch effective perveance ratio:
        K_eff,peak / K0,peak ~= 1 - eta_avg / B_f
        """
        if self.bunching_factor <= 0:
            raise ValueError("bunching_factor must be positive")
        return 1.0 - (eta_avg / self.bunching_factor)

    def peak_line_charge_density(self, profile: str = "parabolic") -> float:
        """
        Computes maximum line charge density lambda(0) [C/m] at the bunch center.
        """
        q_bunch = self.bunch_charge_C
        dz = self.bunch_length_m

        if profile.lower() in ("parabolic", "para"):
            # lambda_0 = 3 * Q / (2 * dz)
            return (1.5 * q_bunch) / dz
        elif profile.lower() in ("gaussian", "gauss"):
            # FWHM = dz -> sigma_z = dz / (2 * sqrt(2 * ln(2)))
            sigma_z = dz / (2.0 * math.sqrt(2.0 * math.log(2.0)))
            return q_bunch / (math.sqrt(2.0 * math.pi) * sigma_z)
        elif profile.lower() in ("tophat", "uniform"):
            return q_bunch / dz
        else:
            raise ValueError(f"Unknown bunch profile: '{profile}'. Use 'parabolic', 'gaussian', or 'tophat'.")

    def line_charge_density(
        self, z: Union[float, np.ndarray], profile: str = "parabolic"
    ) -> Union[float, np.ndarray]:
        """
        Computes longitudinal slice line charge density lambda(z) [C/m] centered at z = 0.
        """
        q_bunch = self.bunch_charge_C
        dz = self.bunch_length_m
        z_arr = np.asarray(z)
        is_scalar = np.isscalar(z) or z_arr.ndim == 0

        prof = profile.lower()
        if prof in ("parabolic", "para"):
            zm = dz / 2.0
            lambda_z = (1.5 * q_bunch / dz) * np.maximum(0.0, 1.0 - (z_arr / zm)**2)
        elif prof in ("gaussian", "gauss"):
            sigma_z = dz / (2.0 * math.sqrt(2.0 * math.log(2.0)))
            lambda_z = (q_bunch / (math.sqrt(2.0 * math.pi) * sigma_z)) * np.exp(-0.5 * (z_arr / sigma_z)**2)
        elif prof in ("tophat", "uniform"):
            lambda_z = np.where(np.abs(z_arr) <= (dz / 2.0), q_bunch / dz, 0.0)
        else:
            raise ValueError(f"Unknown bunch profile: '{profile}'. Use 'parabolic', 'gaussian', or 'tophat'.")

        return float(lambda_z) if is_scalar else lambda_z

    def radial_electric_field(
        self,
        r: float,
        z: float = 0.0,
        profile: str = "parabolic",
        sigma_r: Optional[float] = None,
    ) -> float:
        """
        Calculates radial space-charge electric field E_r(r, z) [V/m] for Gaussian transverse beam core:
        Formula:
            E_r(r, z) = (lambda(z) / (2 * pi * eps_0 * r)) * [1 - exp(-r^2 / (2 * sigma_r^2))]
        """
        if r < 0.0:
            raise ValueError("Radius r must be non-negative")

        if sigma_r is None:
            sig_r = self.radius_m / 2.0  # RMS beam radius
        else:
            sig_r = float(sigma_r)

        if sig_r <= 0.0:
            raise ValueError("sigma_r must be positive")

        lam = float(self.line_charge_density(z, profile=profile))

        if r == 0.0:
            return 0.0
        elif r < 1.0e-7:
            # Linear core asymptotic limit: E_r ~= lambda * r / (4 * pi * eps_0 * sigma_r^2)
            return (lam * r) / (4.0 * math.pi * EPSILON_0 * (sig_r**2))
        else:
            core_factor = 1.0 - math.exp(-0.5 * (r / sig_r)**2)
            return (lam / (2.0 * math.pi * EPSILON_0 * r)) * core_factor


def compute_bunched_beam_compensation_scan(
    bunching_factors: Sequence[float] = (1.0, 2.0, 3.0, 5.0, 10.0),
    eta_avg_values: Sequence[float] = (0.0, 0.50, 0.80, 0.90, 0.95),
    energy_keV: float = 30.0,
    current_mA: float = 10.0,
    rf_frequency_hz: float = 50.0e6,
    bunch_phase_width_deg: float = 36.0,
) -> pd.DataFrame:
    """Evaluates RF-bunched beam perveance scaling across bunching factors and neutralization fractions.

    Args:
        bunching_factors: Sequence of peak-to-average bunching factors B_f.
        eta_avg_values: Sequence of average plasma neutralization fractions eta_avg.
        energy_keV: Proton beam kinetic energy in keV.
        current_mA: Average proton beam current in mA.
        rf_frequency_hz: RF bunching frequency in Hz.
        bunch_phase_width_deg: RF bunch phase width in degrees.

    Returns:
        pd.DataFrame containing bunch metrics and perveance ratios.
    """
    import pandas as pd
    records = []
    for Bf in bunching_factors:
        beam = RFFocusedBeam(
            energy_keV=energy_keV,
            current_mA=current_mA,
            rf_frequency_hz=rf_frequency_hz,
            bunch_phase_width_deg=bunch_phase_width_deg,
            bunching_factor=Bf,
        )
        for eta_avg in eta_avg_values:
            records.append({
                "bunching_factor": float(Bf),
                "eta_avg": float(eta_avg),
                "rf_frequency_hz": beam.rf_frequency_hz,
                "rf_period_s": 1.0 / beam.rf_frequency_hz,
                "bunch_phase_width_deg": beam.bunch_phase_width_deg,
                "bunch_duration_s": beam.bunch_duration_s,
                "bunch_length_m": beam.bunch_length_m,
                "I_avg_mA": beam.beam_current_average_mA,
                "I_peak_mA": beam.beam_current_peak_mA,
                "K0_avg": beam.perveance_K0,
                "K0_peak": beam.peak_perveance_K0,
                "K_eff_avg_over_K0": 1.0 - float(eta_avg),
                "K_eff_peak_over_K0_peak": beam.peak_effective_perveance_ratio(float(eta_avg)),
            })
    return pd.DataFrame(records)
