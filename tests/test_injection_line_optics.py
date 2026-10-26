"""
tests/test_injection_line_optics.py

Unit tests for downstream injection-line optics, envelope integration,
and spiral inflector entrance transmission calculations.
"""

import sys
from pathlib import Path
import math
import pytest

# Ensure src/ is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plasma_column.beam import ProtonBeam
from plasma_column.injection_line import InjectionLine, compute_beam_envelope
from plasma_column.acceptance import InflectorAcceptance, compute_inflector_transmission, generate_phase_space_particles


def test_injection_line_layout():
    line = InjectionLine()
    assert line.plasma_cell_length == 0.20
    assert line.solenoid_length == 0.25
    assert line.total_length > 1.0  # Total length > 1 m

    elem_name, kx, ky = line.get_element_at(0.10)
    assert elem_name == "plasma_neutralizer"

    elem_name2, _, _ = line.get_element_at(0.40)
    assert elem_name2 == "solenoid"


def test_envelope_integration_vacuum_vs_neutralized():
    beam = ProtonBeam(energy_keV=30.0, current_mA=10.0)
    line = InjectionLine()

    # Vacuum case (eta_net = 0.0)
    z_vac, Rx_vac, Ry_vac = compute_beam_envelope(beam, line, eta_net=0.0)

    # Neutralized case (eta_net = 0.90)
    z_neut, Rx_neut, Ry_neut = compute_beam_envelope(beam, line, eta_net=0.90)

    # Vacuum beam should experience a larger space-charge blowup (largest envelope along the line;
    # the exit radius at a fixed tune depends on the matching)
    assert max(Rx_vac.max(), Ry_vac.max()) > max(Rx_neut.max(), Ry_neut.max())


def test_inflector_transmission_calculation():
    acceptance = InflectorAcceptance(aperture_radius_m=0.005)

    # Small beam inside aperture (3 mm) -> 100% transmission
    res_small = compute_inflector_transmission(0.003, 0.003, 0.0, 0.0, acceptance)
    assert res_small["transmission_fraction"] == 1.0
    assert res_small["transmission_percent"] == 100.0

    # Large beam outside aperture (10 mm) -> clipped transmission
    res_large = compute_inflector_transmission(0.010, 0.010, 0.0, 0.0, acceptance)
    assert res_large["transmission_fraction"] < 0.30
    assert res_large["transmission_percent"] < 30.0


def test_phase_space_generation():
    df_xxp, df_yyp = generate_phase_space_particles(0.004, 0.010, 0.004, 0.010, n_particles=500)
    assert len(df_xxp) == 500
    assert len(df_yyp) == 500
    assert "x_mm" in df_xxp.columns
    assert "xp_mrad" in df_xxp.columns
