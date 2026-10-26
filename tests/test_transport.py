"""Matched envelope transport (plasma_column.transport, task 106)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from plasma_column.injection_line import InjectionLine
from plasma_column.transport import (
    Optics,
    TransportBeam,
    ellipse_fraction_inside_circle,
    envelope,
    perveance_profile,
    transmission,
)


def test_rigidity_and_emittance_of_30keV_protons():
    b = TransportBeam()
    assert b.rigidity_Tm == pytest.approx(0.02503, rel=1e-3)  # sqrt(2 m E) / e
    assert b.emittance_geom_m_rad == pytest.approx(1.0e-6 / b.proton.beta, rel=1e-3)


def test_drift_without_space_charge_matches_emittance_envelope():
    # Field-free, K = 0: R(z)^2 = a0^2 + (eps z / a0)^2 for a waist at z = 0.
    b = TransportBeam(emittance_n_edge_m_rad=0.5e-6)
    line = InjectionLine()
    env = envelope(b, line, Optics(0.0, 0.0, 0.0), lambda z: np.zeros_like(z))
    eps, a0 = b.emittance_geom_m_rad, b.r0_m
    expect = np.sqrt(a0**2 + (eps * env["z_m"] / a0) ** 2)
    assert np.allclose(env["Rx_m"], expect, rtol=1e-6)
    assert np.allclose(env["Ry_m"], expect, rtol=1e-6)


def test_compensation_reduces_growth_and_bunching_increases_it():
    b = TransportBeam(emittance_n_edge_m_rad=0.25e-6)
    line = InjectionLine()
    o = Optics(0.0, 0.0, 0.0)
    K0 = b.proton.perveance_K0
    r_dc = envelope(b, line, o, perveance_profile(K0, line))["Rx_m"][200]
    r_cell = envelope(b, line, o, perveance_profile(K0, line, eta_cell=0.9))["Rx_m"][200]
    z = np.linspace(0, line.total_length, 50)
    r_bunch = envelope(b, line, o, perveance_profile(K0, line, bunching_z_m=z,
                                                    bunching_factor=np.full_like(z, 3.0)))["Rx_m"][200]
    assert r_cell < r_dc < r_bunch


def test_ellipse_fraction_and_transmission_limits():
    assert ellipse_fraction_inside_circle(0.004, 0.004, 0.005) == 1.0
    assert ellipse_fraction_inside_circle(0.010, 0.010, 0.005) == pytest.approx(0.25, abs=0.02)
    b = TransportBeam(emittance_n_edge_m_rad=0.25e-6)
    env = envelope(b, InjectionLine(), Optics(0.0, 0.0, 0.0), lambda z: np.zeros_like(z))
    t = transmission(env, b)
    assert 0.0 <= t["T_total"] <= 1.0
    assert t["T_total"] == pytest.approx(t["T_pipe"] * t["T_inflector_aperture"] * t["T_inflector_divergence"])


def test_old_default_quadrupole_gradients_are_far_too_strong():
    # 5 T/m at Brho = 0.025 T m gives k L ~ 1.7 per 12 cm quadrupole: the beam overfocuses in one
    # plane and blows up in the other (task 106).
    b = TransportBeam()
    kL = math.sqrt(5.0 / b.rigidity_Tm) * 0.12
    assert kL > 1.5


def test_average_compensation_limits_peak_slice_benefit():
    # Electrons cancel only the RF-averaged charge: K_peak / K0,peak = 1 - eta / B_f (AGENTS.md).
    line = InjectionLine()
    z = np.linspace(0, line.total_length, 50)
    bf = np.full_like(z, 5.0)
    zz = np.array([0.1, 0.8])
    k_avg = perveance_profile(1.0, line, 0.96, 0.96, z, bf, compensation="average")(zz)
    k_slice = perveance_profile(1.0, line, 0.96, 0.96, z, bf, compensation="per_slice")(zz)
    assert np.allclose(k_avg, 5.0 - 0.96)
    assert np.allclose(k_slice, 5.0 * 0.04)
    # Identical for a DC beam.
    assert np.allclose(perveance_profile(1.0, line, 0.9, compensation="average")(zz),
                       perveance_profile(1.0, line, 0.9, compensation="per_slice")(zz))
    with pytest.raises(ValueError):
        perveance_profile(1.0, line, compensation="bogus")
