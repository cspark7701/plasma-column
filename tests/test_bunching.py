"""Ballistic bunching model (plasma_column.bunching)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from plasma_column.bunching import (
    BuncherModel,
    bunching_along_line,
    phases_at,
    sample_bunched_beam,
    window_bunching_factor,
)


def test_dc_beam_has_unit_bunching_factor():
    b = BuncherModel(voltage_V=0.0, energy_spread_rms_eV=0.0)
    phi, e = sample_bunched_beam(b, 200_000)
    bf, _ = window_bunching_factor(phases_at(1.0, phi, e, b))
    assert bf == pytest.approx(1.0, abs=0.03)


def test_sine_buncher_matches_klystron_bunching_parameter():
    # Fundamental current harmonic of ballistic bunching: |I_1| / I_0 = 2 J_1(X),
    # X = (omega z / v0) * (e V / (2 E)) non-relativistically.
    from scipy.special import j1

    b = BuncherModel(voltage_V=300.0, energy_spread_rms_eV=0.0)
    z = 0.8
    phi, e = sample_bunched_beam(b, 400_000)
    psi = phases_at(z, phi, e, b)
    v0 = math.sqrt(2 * 30e3 * 1.602176634e-19 / 1.67262192369e-27)
    X = (2 * math.pi * 50e6 * z / v0) * (300.0 / (2 * 30e3))
    assert abs(np.mean(np.exp(1j * psi))) == pytest.approx(j1(X), rel=0.03)


def test_bunching_grows_from_cell_to_inflector():
    b = BuncherModel(voltage_V=620.0)
    r = bunching_along_line(np.array([0.0, 0.2, 1.12]), b, n_particles=100_000)
    bf = r["bunching_factor"]
    assert bf[0] < 1.1 < bf[1] < 1.6 < 4.0 < bf[2] <= 10.0


def test_buncher_at_position_shifts_profile():
    import numpy as np

    from plasma_column.bunching import BuncherModel, bunching_along_line, bunching_with_buncher_at

    b = BuncherModel(voltage_V=1500.0)
    z = np.array([0.0, 0.3, 0.5, 0.8])
    bf = bunching_with_buncher_at(z, 0.3, b, n_particles=50_000)
    assert bf[0] == 1.0
    ref = bunching_along_line(np.array([0.0, 0.2, 0.5]), b, n_particles=50_000)["bunching_factor"]
    assert np.allclose(bf[1:], np.maximum(ref, 1.0), rtol=0.05)
