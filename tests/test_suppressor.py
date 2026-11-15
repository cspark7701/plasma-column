"""Axisymmetric suppressor model (task CW4)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from plasma_column.suppressor import SuppressorConfig, barrier_V, solve


def test_uncompensated_beam_potential_on_axis():
    cfg = SuppressorConfig(suppressor_voltage_V=0.0, eta_down=0.0, length_m=0.0005, aperture_m=0.0099,
                           dr_m=2.5e-4, dz_m=1e-3)
    sol = solve(cfg)
    lam = cfg.beam_current_A / cfg.beam_speed_m_s
    expected = lam / (4 * math.pi * 8.8541878128e-12) * (1 + 2 * math.log(cfg.pipe_radius_m / cfg.beam_radius_m))
    assert barrier_V(sol, cfg)["phi_upstream_V"] == pytest.approx(expected, rel=0.03)


def test_compensation_lowers_upstream_potential():
    a = barrier_V(solve(c := SuppressorConfig(suppressor_voltage_V=0.0, eta_down=0.0, dz_m=1e-3)), c)
    b = barrier_V(solve(c := SuppressorConfig(suppressor_voltage_V=0.0, eta_down=0.9, dz_m=1e-3)), c)
    assert b["phi_upstream_V"] == pytest.approx(0.1 * a["phi_upstream_V"], rel=0.05)


def test_suppressor_voltage_creates_barrier():
    lo = barrier_V(solve(c := SuppressorConfig(suppressor_voltage_V=0.0, dz_m=5e-4)), c)
    hi = barrier_V(solve(c := SuppressorConfig(suppressor_voltage_V=1000.0, dz_m=5e-4)), c)
    assert lo["barrier_V"] < 0  # no suppressor: downstream uncompensated beam is a potential hill
    assert hi["barrier_V"] > 50


def test_suppressor_lens_focuses_and_scales_as_voltage_squared():
    from plasma_column.suppressor import lens_focal_length_m

    s0 = solve(SuppressorConfig(suppressor_voltage_V=0.0, dz_m=5e-4))
    f1 = lens_focal_length_m(solve(SuppressorConfig(suppressor_voltage_V=500.0, dz_m=5e-4)), s0, 30e3)
    f2 = lens_focal_length_m(solve(SuppressorConfig(suppressor_voltage_V=1000.0, dz_m=5e-4)), s0, 30e3)
    assert f1 > 0 and f2 > 0  # an einzel-type single-electrode lens always focuses
    assert f1 / f2 == pytest.approx(4.0, rel=0.15)  # weak lens: 1/f ~ V_s^2
