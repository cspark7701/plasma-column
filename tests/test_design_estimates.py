"""Tests for plasma_column.design_estimates (numbers quoted in the manuscript)."""

from __future__ import annotations

import math

import pytest

from plasma_column.design_estimates import (
    DesignPoint,
    compute_design_numbers,
    doubling_length_m,
    ion_expulsion_time_s,
    laminar_envelope_drift,
    potential_well_depth_V,
)


@pytest.fixture(scope="module")
def numbers() -> dict[str, float]:
    return compute_design_numbers(DesignPoint())


def test_beam_kinematics_30keV(numbers):
    # beta = sqrt(2 E / m c^2) for a non-relativistic 30 keV proton
    assert numbers["beta"] == pytest.approx(math.sqrt(2 * 30.0 / 938272.0881), rel=1e-3)
    assert numbers["v_m_s"] == pytest.approx(2.397e6, rel=1e-3)


def test_generalized_perveance(numbers):
    # K0 = 2 I / (I0 beta^3 gamma^3), I0 = 4 pi eps0 m_p c^3 / e ~ 3.13e7 A
    i0 = 3.1268e7
    assert numbers["K0"] == pytest.approx(2 * 0.01 / (i0 * numbers["beta"] ** 3), rel=2e-3)
    assert numbers["K0_peak"] == pytest.approx(5 * numbers["K0"])


def test_ionization_times_and_equal_tau_pressure(numbers):
    assert numbers["tau_h2_s"] == pytest.approx(
        1 / (numbers["n_h2_m3"] * numbers["sigma_h2_m2"] * numbers["v_m_s"]))
    # Kr at 1e-6 Torr is slower than H2 at 1e-5 Torr because sigma ratio < 10
    assert numbers["sigma_ratio_kr_h2"] < 10
    assert numbers["tau_kr_s"] > numbers["tau_h2_s"]
    p_eq = numbers["p_kr_equal_tau_torr"]
    from plasma_column.gas import gas_density_m3
    tau_kr_eq = 1 / (gas_density_m3(p_eq) * numbers["sigma_kr_m2"] * numbers["v_m_s"])
    assert tau_kr_eq == pytest.approx(numbers["tau_h2_s"], rel=1e-9)


def test_doubling_length_matches_envelope_integration():
    a0, k = 2e-3, 1.25e-3
    z2 = doubling_length_m(a0, k)
    _, a = laminar_envelope_drift(a0, k, z2)
    assert a[-1] / a0 == pytest.approx(2.0, rel=1e-5)


def test_envelope_monotonic_in_perveance():
    a0, L = 2e-3, 0.2
    finals = [laminar_envelope_drift(a0, k, L)[1][-1] for k in (0.0, 1e-4, 1e-3)]
    assert finals[0] == pytest.approx(a0)
    assert finals[0] < finals[1] < finals[2]


def test_well_depth_and_ion_expulsion_scaling():
    lam, a, b = 4e-9, 2e-3, 10e-3
    assert potential_well_depth_V(2 * lam, a, b) == pytest.approx(2 * potential_well_depth_V(lam, a, b))
    t_h2 = ion_expulsion_time_s(lam, a, 2.016 * 1.6605e-27)
    t_kr = ion_expulsion_time_s(lam, a, 83.8 * 1.6605e-27)
    assert t_kr / t_h2 == pytest.approx(math.sqrt(83.8 / 2.016), rel=1e-6)


def test_timescale_ordering(numbers):
    # Electrons cross the beam much faster than the bunch gap; PIC runs are far shorter than tau.
    assert numbers["t_electron_cross_s"] < numbers["bunch_gap_s"]
    assert numbers["pic_duration_dynamic_s"] < 1e-2 * numbers["tau_h2_s"]
    assert numbers["eta_free_escape_h2"] < 1e-2
