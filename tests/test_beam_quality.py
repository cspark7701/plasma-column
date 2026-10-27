"""Slab rms moments of beam particles (plasma_column.beam_quality, task C3)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from plasma_column.beam_quality import slab_beam_moments
from plasma_column.constants import C, MP


def _beam(n: int = 200_000, sx: float = 1e-3, sxp: float = 5e-3, corr: float = 0.0) -> dict:
    rng = np.random.default_rng(1)
    pz0 = MP * 0.008 * C  # ~30 keV proton
    x = rng.normal(0, sx, n)
    xp = corr * x / sx * sxp + math.sqrt(1 - corr**2) * rng.normal(0, sxp, n)
    y = rng.normal(0, sx, n)
    yp = rng.normal(0, sxp, n)
    return {"x": x, "y": y, "z": rng.uniform(0, 0.2, n), "px": xp * pz0, "py": yp * pz0,
            "pz": np.full(n, pz0), "w": np.ones(n), "time": 0.0}


def test_uncorrelated_gaussian_emittance():
    m = slab_beam_moments(_beam(), 0.0, 0.2)
    assert m["x_rms_mm"] == pytest.approx(1.0, rel=0.01)
    assert m["xp_rms_mrad"] == pytest.approx(5.0, rel=0.01)
    # eps_n = beta gamma sigma_x sigma_x' = 0.008 * 1e-3 * 5e-3 m rad = 0.04 pi mm mrad
    assert m["eps_n_rms_x_mm_mrad"] == pytest.approx(0.04, rel=0.02)


def test_correlation_removes_emittance_and_slab_selects():
    m = slab_beam_moments(_beam(corr=0.99), 0.0, 0.2)
    assert m["eps_n_rms_x_mm_mrad"] == pytest.approx(0.04 * math.sqrt(1 - 0.99**2), rel=0.05)
    assert slab_beam_moments(_beam(), 0.1, 0.2)["n_macro"] == pytest.approx(100_000, rel=0.02)
    assert math.isnan(slab_beam_moments(_beam(), 0.5, 0.6)["x_rms_mm"])
