"""Guiding-centre test electrons in the static trap (task C2)."""

from __future__ import annotations

import numpy as np
import pytest

from plasma_column.electron_trap import TrapConfig, confinement_time_s, elastic_cross_section_m2, track


def test_cross_section_peak_near_3eV():
    assert elastic_cross_section_m2(3.0) == pytest.approx(1.7e-19, rel=1e-6)
    assert elastic_cross_section_m2(100.0) < elastic_cross_section_m2(3.0)


def test_plugs_hold_cold_electrons_without_collisions():
    cfg = TrapConfig(collisions=False, beam_heating=False)
    r = track(cfg, n_electrons=300, t_end_s=3e-6, temperature_eV=1.0, n_out=10)
    assert r["surviving"][-1] == 1.0
    # Kinetic energy only: electrons near the cell ends sit in the plug tail (1.1% of V = 3.3 V).
    assert r["mean_energy_eV"][-1] == pytest.approx(r["mean_energy_eV"][0], rel=0.06)


def test_no_plugs_electrons_stream_out():
    cfg = TrapConfig(plug_voltage_V=0.0, collisions=False, beam_heating=False)
    r = track(cfg, n_electrons=500, t_end_s=5e-6, temperature_eV=1.0, n_out=10)
    assert r["surviving"][-1] < 0.2
    assert r["lost_radial"][-1] == 0.0


def test_beam_heating_rate():
    cfg = TrapConfig(collisions=False)
    r = track(cfg, n_electrons=400, t_end_s=10e-6, temperature_eV=1.0, n_out=5, dt_s=1e-9)
    gain = r["mean_energy_eV"][-1] - r["mean_energy_eV"][0]
    expected = cfg.heating_W * 10e-6 / 1.602176634e-19
    assert 0.05 < expected < 1.0
    assert gain == pytest.approx(expected, rel=0.35)


def test_confinement_time_fit():
    t = np.linspace(0, 1e-4, 50)
    assert confinement_time_s(t, np.exp(-t / 3e-5)) == pytest.approx(3e-5, rel=1e-6)
    assert confinement_time_s(t, np.ones_like(t)) == float("inf")


def test_collisions_without_heating_keep_energy():
    cfg = TrapConfig(beam_heating=False, eta=1.0, pressure_torr=1e-3)  # ~100x more collisions
    r = track(cfg, n_electrons=400, t_end_s=2e-6, temperature_eV=1.0, n_out=5)
    assert r["mean_energy_eV"][-1] == pytest.approx(r["mean_energy_eV"][0], rel=0.06)
