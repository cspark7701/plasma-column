"""
tests/test_bunched_beam.py

Unit tests for RF-bunched beam calculations and peak perveance formulas.
"""

import sys
from pathlib import Path
import math
import pytest

# Ensure src/ is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plasma_column.beam import ProtonBeam, RFFocusedBeam


def test_proton_beam_basics():
    beam = ProtonBeam(energy_keV=30.0, current_mA=10.0)
    assert beam.current_A == 0.010
    assert beam.beta > 0.0075 and beam.beta < 0.0085
    assert beam.perveance_K0 > 0.0


def test_rf_focused_beam():
    beam = RFFocusedBeam(
        energy_keV=30.0,
        current_mA=10.0,
        rf_frequency_hz=50.0e6,
        bunch_phase_width_deg=36.0,
        bunching_factor=5.0,
    )

    assert beam.beam_current_average_mA == 10.0
    assert beam.beam_current_peak_mA == 50.0

    # 36 deg at 50 MHz = 2 ns
    assert math.isclose(beam.bunch_duration_s, 2.0e-9, rel_tol=1e-5)

    # 2.3973e6 m/s * 2 ns ~ 4.79 mm
    assert beam.bunch_length_m > 0.004 and beam.bunch_length_m < 0.006

    # Peak perveance ratio: 1 - 0.9 / 5 = 0.82
    k_peak_ratio = beam.peak_effective_perveance_ratio(0.90)
    assert math.isclose(k_peak_ratio, 0.82, rel_tol=1e-5)


def test_bunch_charge_and_conservation():
    """Verify total bunch charge and longitudinal profile integrals."""
    import numpy as np
    from scipy.integrate import quad

    beam = RFFocusedBeam(
        energy_keV=30.0,
        current_mA=10.0,
        rf_frequency_hz=50.0e6,
        bunch_phase_width_deg=36.0,
    )

    q_expected = 10.0e-3 / 50.0e6  # 2.0e-10 C
    assert math.isclose(beam.bunch_charge_C, q_expected, rel_tol=1e-6)

    # Parabolic profile integral
    dz = beam.bunch_length_m
    zm = dz / 2.0
    q_para, _ = quad(lambda z: beam.line_charge_density(z, profile="parabolic"), -zm, zm)
    assert math.isclose(q_para, q_expected, rel_tol=1e-4)

    # Gaussian profile integral
    q_gauss, _ = quad(lambda z: beam.line_charge_density(z, profile="gaussian"), -5 * dz, 5 * dz)
    assert math.isclose(q_gauss, q_expected, rel_tol=1e-4)

    # Peak density checks
    lam_0_p = beam.peak_line_charge_density("parabolic")
    assert lam_0_p > 0.0
    assert math.isclose(beam.line_charge_density(0.0, "parabolic"), lam_0_p, rel_tol=1e-5)


def test_radial_space_charge_electric_field():
    """Verify radial space charge field asymptotics at core and exterior."""
    beam = RFFocusedBeam(
        energy_keV=30.0,
        current_mA=10.0,
        radius_m=0.002,
        rf_frequency_hz=50.0e6,
    )

    # At origin r = 0 -> E_r = 0
    assert beam.radial_electric_field(0.0, z=0.0) == 0.0

    # Inside core (r = 0.5 mm)
    er_core = beam.radial_electric_field(0.0005, z=0.0)
    assert er_core > 0.0

    # Far outside core (r = 20 mm)
    er_far = beam.radial_electric_field(0.020, z=0.0)
    # Outside beam core, E_r ~ lambda / (2 * pi * eps_0 * r)
    from plasma_column.constants import EPSILON_0
    lam_0 = beam.line_charge_density(0.0, "parabolic")
    er_expected_far = lam_0 / (2.0 * math.pi * EPSILON_0 * 0.020)
    assert math.isclose(er_far, er_expected_far, rel_tol=1e-3)

    # Error handling
    with pytest.raises(ValueError):
        beam.radial_electric_field(-0.001)


def test_compute_bunched_beam_compensation_scan():
    from plasma_column.beam import compute_bunched_beam_compensation_scan

    df = compute_bunched_beam_compensation_scan(
        bunching_factors=[1.0, 5.0],
        eta_avg_values=[0.0, 0.90],
    )
    assert len(df) == 4
    assert "bunching_factor" in df.columns
    assert "eta_avg" in df.columns
    assert "K_eff_peak_over_K0_peak" in df.columns

    # B_f=5, eta_avg=0.9 -> 1 - 0.9/5 = 0.82
    row = df[(df["bunching_factor"] == 5.0) & (df["eta_avg"] == 0.90)].iloc[0]
    assert math.isclose(row["K_eff_peak_over_K0_peak"], 0.82, rel_tol=1e-5)


if __name__ == "__main__":
    pytest.main([__file__])
