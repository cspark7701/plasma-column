"""Particle tracking to the inflector (task CW5) against the analytic field and the KV envelope."""

from __future__ import annotations

import numpy as np
import pytest

from plasma_column.injection_line import InjectionLine
from plasma_column.particle_tracking import SpaceChargeGrid, kv_beam, rms_emittance_m_rad, track
from plasma_column.transport import Optics, TransportBeam, envelope, perveance_profile


def test_field_of_uniform_disc_is_linear_inside():
    rng = np.random.default_rng(3)
    n, a = 200_000, 0.003
    r = a * np.sqrt(rng.random(n)); th = rng.uniform(0, 2 * np.pi, n)
    x, y = r * np.cos(th), r * np.sin(th)
    g = SpaceChargeGrid(half_width_m=0.012, n=128)
    probe = np.array([0.0015, 0.0, 0.006])
    fx, _ = g.field(np.concatenate([x, probe]), np.concatenate([y, [0.0, 0.0015, 0.0]]),
                    np.concatenate([np.full(n, 1.0 / n), np.zeros(3)]))
    assert fx[n] == pytest.approx(0.0015 / a**2, rel=0.05)
    assert fx[n + 2] == pytest.approx(1.0 / 0.006, rel=0.05)  # outside: line charge 1/r


@pytest.mark.parametrize("eta", [1.0, 0.0])
def test_kv_beam_follows_envelope(eta):
    line = InjectionLine()
    beam = TransportBeam(emittance_n_edge_m_rad=0.25e-6)
    optics = Optics(0.30, -0.4, 0.9)
    K0 = beam.proton.perveance_K0
    env = envelope(beam, line, optics, perveance_profile(K0, line, eta, eta))
    x, xp, y, yp = kv_beam(20_000, beam.r0_m, beam.emittance_geom_m_rad)
    r = track(x, xp, y, yp, line, optics, beam.rigidity_Tm, K0, eta, eta, pipe_radius_m=1.0, record_every=1,
              grid=SpaceChargeGrid(half_width_m=0.04, n=256))  # no pipe loss; grid wide enough for the beam
    i = np.searchsorted(env["z_m"], 0.55)  # before any large blow-up
    j = int(np.argmin(np.abs(r["z_m"] - env["z_m"][i])))
    assert 2.0 * r["x_rms_mm"][j] == pytest.approx(env["Rx_m"][i] * 1e3, rel=0.06)
    assert 2.0 * r["y_rms_mm"][j] == pytest.approx(env["Ry_m"][i] * 1e3, rel=0.06)


def test_rms_emittance_of_kv_beam():
    x, xp, _, _ = kv_beam(100_000, 0.002, 1e-5)
    assert 4.0 * rms_emittance_m_rad(x, xp) == pytest.approx(1e-5, rel=0.02)
