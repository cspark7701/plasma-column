"""RF-averaged vs peak-bunch neutralization from z profiles (task B2)."""

from __future__ import annotations

import numpy as np
import pytest

from plasma_column.bunched_cell import bunch_metrics, core_z_profiles, rf_wavelength_m


def _profile(bf_kappa: float, follow: bool, eta: float = 0.9):
    lam = 0.048
    z = np.linspace(0.0, 0.2, 2001)
    shape = np.exp(bf_kappa * (np.cos(2 * np.pi * z / lam) - 1.0))
    npr = shape / shape[: int(len(z) * lam / 0.2)].mean()
    ne_static = eta * np.ones_like(z)
    ne = eta * npr if follow else ne_static
    return {"z": z, "ne": ne + 1.0, "ni": np.ones_like(z), "np": npr}, lam


def test_wavelength_30keV_50MHz():
    assert rf_wavelength_m(30e3, 50e6) == pytest.approx(0.0479, rel=2e-3)


def test_dc_beam_peak_equals_average():
    prof, lam = _profile(0.0, follow=False)
    m = bunch_metrics(prof, 0.0, lam, 3)
    assert m["eta_avg"] == pytest.approx(0.9, rel=1e-3)
    assert m["eta_peak"] == pytest.approx(0.9, rel=1e-3)
    assert m["bunching_factor_cell"] == pytest.approx(1.0, rel=1e-3)


def test_static_electrons_compensate_peak_by_one_over_bf():
    prof, lam = _profile(3.0, follow=False)
    m = bunch_metrics(prof, 0.0, lam, 3)
    assert m["eta_avg"] == pytest.approx(0.9, rel=2e-3)
    # The peak region (top 10% of the line density) carries a mean density just below max, so
    # eta_peak lies just above eta_avg / B_cell.
    assert m["eta_avg"] / m["bunching_factor_cell"] < m["eta_peak"] < 1.3 * m["eta_avg"] / m["bunching_factor_cell"]
    assert m["ne_modulation"] == pytest.approx(0.0, abs=1e-9)
    assert m["eta_gap_excess"] > 0


def test_following_electrons_compensate_peak():
    prof, lam = _profile(3.0, follow=True)
    m = bunch_metrics(prof, 0.0, lam, 3)
    assert m["eta_peak"] == pytest.approx(0.9, rel=2e-3)
    assert m["ne_modulation"] > 0.5


def test_core_z_profiles_average_inside_core():
    x = y = np.linspace(-0.01, 0.01, 21)
    z = np.linspace(0, 0.2, 5)
    X, Y, _ = np.meshgrid(x, y, z, indexing="ij")
    ne = np.where(np.hypot(X, Y) <= 0.002, 2.0, 100.0)
    prof = core_z_profiles(ne, ne, ne, x, y, z, 0.002)
    assert np.allclose(prof["ne"], 2.0)
