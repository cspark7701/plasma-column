"""
tests/test_analytic_ionization_rate.py

Unit tests for analytical ion-impact MCC ionization rate formulas,
species cross-section ratios, and time-step probability calculations.
"""

import sys
from pathlib import Path
import math
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_mcc_verification import compute_analytic_mcc_rates
from plasma_column.gas import get_h2_cross_section, get_kr_cross_section


def test_no_gas_zero_rate():
    """Verify zero pressure gives zero ionization rate and zero expected electrons."""
    res = compute_analytic_mcc_rates(pressure_torr=0.0, sigma_m2=1.0e-20)
    assert res["gas_density_m3"] == 0.0
    assert res["prob_per_step"] == 0.0
    assert res["expected_macro_electrons"] == 0.0


def test_zero_cross_section_zero_rate():
    """Verify zero cross section gives zero ionization rate."""
    res = compute_analytic_mcc_rates(pressure_torr=1.0e-5, sigma_m2=0.0)
    assert res["prob_per_step"] == 0.0
    assert res["expected_macro_electrons"] == 0.0


def test_fixed_cross_section_rate():
    """Verify fixed cross section analytic ionization rate matches dNe/dt = Np * n_gas * sigma * v_p."""
    res = compute_analytic_mcc_rates(
        energy_keV=30.0, pressure_torr=1.0e-5, temp_k=300.0, sigma_m2=1.0e-20, N_protons=1000.0
    )

    # Speed ~ 2.4e6 m/s, n_gas ~ 3.2e17 m^-3, sigma = 1.0e-20 m^2
    # Rate per proton ~ 3.2e17 * 1.0e-20 * 2.4e6 ~ 7.7e3 s^-1
    assert 7.0e3 < res["rate_per_proton_s1"] < 8.5e3
    assert res["expected_macro_electrons"] > 0.0


def test_h2_vs_kr_cross_section_ratio():
    """Verify H2 vs Kr cross-section ratio at 30 keV."""
    sig_h2 = get_h2_cross_section(30.0)
    sig_kr = get_kr_cross_section(30.0)

    # Kr cross section is ~ 8.96e-20 m^2, H2 is ~ 1.61e-20 m^2 (ratio ~ 5.56)
    ratio = sig_kr / sig_h2
    assert 5.0 < ratio < 6.5


def test_timestep_collision_probability():
    """Verify collision probability formula P = 1 - exp(-n_gas * sigma * v_p * dt)."""
    res1 = compute_analytic_mcc_rates(dt_s=1.0e-11)
    res2 = compute_analytic_mcc_rates(dt_s=5.0e-12)

    p1 = res1["prob_per_step"]
    p2 = res2["prob_per_step"]

    # Halving dt should approximately halve single-step collision probability
    assert math.isclose(p1 / p2, 2.0, rel_tol=1e-2)
