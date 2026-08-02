"""
tests/test_acceptance.py

Unit tests for spiral inflector entrance acceptance, transmission calculations, and phase space particle generation.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from plasma_column.acceptance import (
    InflectorAcceptance,
    compute_inflector_transmission,
    generate_phase_space_particles,
)


def test_inflector_acceptance_defaults():
    acc = InflectorAcceptance()
    assert acc.aperture_radius_m == 0.005
    assert acc.max_divergence_rad == 0.050


def test_transmission_full_acceptance():
    acc = InflectorAcceptance(aperture_radius_m=0.005)
    # Beam radius 3 mm <= 5 mm aperture -> 100% transmission
    res = compute_inflector_transmission(
        Rx_end=0.003, Ry_end=0.003, dRx_end=0.010, dRy_end=0.010, acceptance=acc
    )
    assert res["transmission_fraction"] == 1.0
    assert res["transmission_percent"] == 100.0
    assert res["r_beam_mm"] == pytest.approx(3.0)


def test_transmission_clipped_aperture():
    acc = InflectorAcceptance(aperture_radius_m=0.005)
    # Beam radius 10 mm > 5 mm aperture -> (5/10)^2 = 0.25 (25% transmission)
    res = compute_inflector_transmission(
        Rx_end=0.010, Ry_end=0.010, dRx_end=0.010, dRy_end=0.010, acceptance=acc
    )
    assert res["transmission_fraction"] == pytest.approx(0.25, abs=1e-3)
    assert res["transmission_percent"] == pytest.approx(25.0, abs=0.1)


def test_phase_space_particle_generation():
    df_xxp, df_yyp = generate_phase_space_particles(
        Rx=0.004, dRx=0.015, Ry=0.004, dRy=0.015, n_particles=500
    )
    assert len(df_xxp) == 500
    assert len(df_yyp) == 500
    assert "x_mm" in df_xxp.columns
    assert "xp_mrad" in df_xxp.columns
    assert "y_mm" in df_yyp.columns
    assert "yp_mrad" in df_yyp.columns

    # Verify non-zero standard deviation matching moments
    assert np.std(df_xxp["x_mm"]) > 0.0
    assert np.std(df_xxp["xp_mrad"]) > 0.0
