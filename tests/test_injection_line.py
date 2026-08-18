"""
tests/test_injection_line.py

Unit tests for InjectionLine layout, element lookup, and transverse envelope ODE integration.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from plasma_column.beam import ProtonBeam
from plasma_column.injection_line import (
    InjectionLine,
    Element,
    Drift,
    Solenoid,
    Quadrupole,
    compute_beam_envelope,
)


def test_injection_line_layout_length():
    line = InjectionLine(
        plasma_cell_length=0.20,
        drift1_length=0.10,
        solenoid_length=0.25,
        drift2_length=0.10,
        q1_length=0.12,
        drift3_length=0.08,
        q2_length=0.12,
        drift4_length=0.15,
    )
    expected_length = 0.20 + 0.10 + 0.25 + 0.10 + 0.12 + 0.08 + 0.12 + 0.15
    assert math.isclose(line.total_length, expected_length, abs_tol=1e-6)


def test_element_lookup_at_z():
    line = InjectionLine()
    # At z = 0.05 m -> inside plasma neutralizer (0.0 to 0.20 m)
    elem, kx, ky = line.get_element_at(0.05)
    assert elem == "plasma_neutralizer"

    # At z = 0.25 m -> inside drift1 (0.20 to 0.30 m)
    elem, kx, ky = line.get_element_at(0.25)
    assert elem == "drift1"

    # At z = 0.40 m -> inside solenoid (0.30 to 0.55 m)
    elem, kx, ky = line.get_element_at(0.40)
    assert elem == "solenoid"


def test_envelope_integration_uncompensated():
    beam = ProtonBeam(energy_keV=30.0, current_mA=10.0, radius_m=0.002)
    line = InjectionLine()

    # Solve envelope ODE for uncompensated beam (eta = 0.0)
    z_eval, Rx_arr, Ry_arr = compute_beam_envelope(beam, line, eta_net=0.0)
    assert len(z_eval) > 10
    assert len(Rx_arr) == len(z_eval)
    assert len(Ry_arr) == len(z_eval)

    # Beam envelope radius should be positive throughout
    assert np.all(Rx_arr > 0.0)
    assert np.all(Ry_arr > 0.0)


def test_envelope_integration_neutralized_focusing():
    beam = ProtonBeam(energy_keV=30.0, current_mA=10.0, radius_m=0.002)
    line = InjectionLine()

    # Highly neutralized beam (eta = 0.90) should experience reduced space charge expansion
    z1, Rx_uncomp, Ry_uncomp = compute_beam_envelope(beam, line, eta_net=0.0)
    z2, Rx_comp, Ry_comp = compute_beam_envelope(beam, line, eta_net=0.90)

    # Maximum radius of compensated beam should be smaller than uncompensated beam
    r_max_uncomp = np.max(Rx_uncomp)
    r_max_comp = np.max(Rx_comp)
    assert r_max_comp < r_max_uncomp


def test_envelope_cell_only_vs_uniform_neutralization():
    """
    Verify that cell-only neutralization (eta_cell=0.9, eta_downstream=0.0)
    experiences more downstream expansion than uniform neutralization (eta_downstream=0.9),
    but remains smaller than full vacuum (eta_cell=0.0).
    """
    beam = ProtonBeam(energy_keV=30.0, current_mA=10.0, radius_m=0.002)
    line = InjectionLine()

    z, rx_vac, ry_vac = compute_beam_envelope(beam, line, eta_cell=0.0, eta_downstream=0.0)
    z, rx_cell, ry_cell = compute_beam_envelope(beam, line, eta_cell=0.90, eta_downstream=0.0)
    z, rx_unif, ry_unif = compute_beam_envelope(beam, line, eta_cell=0.90, eta_downstream=0.90)

    # At the inflector entrance:
    assert rx_unif[-1] < rx_cell[-1] < rx_vac[-1]
    assert ry_unif[-1] < ry_cell[-1] < ry_vac[-1]

    # Inside the plasma cell (z <= 0.20 m), cell-only and uniform curves must agree closely (< 0.1%)
    cell_mask = z <= line.plasma_cell_length
    assert np.allclose(rx_cell[cell_mask], rx_unif[cell_mask], rtol=1e-2)


def test_envelope_custom_keff_func():
    """Verify arbitrary keff_func is evaluated properly by compute_beam_envelope."""
    beam = ProtonBeam(energy_keV=30.0, current_mA=10.0, radius_m=0.002)
    line = InjectionLine()

    # Step function keff
    def custom_keff(z: float) -> float:
        return 0.0 if z < 0.5 else beam.perveance_K0

    z, rx_custom, ry_custom = compute_beam_envelope(beam, line, keff_func=custom_keff)
    assert len(z) == 500
    assert np.all(rx_custom > 0.0)
