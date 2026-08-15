"""
tests/test_basic_physics.py

Lightweight unit tests for core plasma_column physics utilities:
- Proton velocity at 30 keV
- Ideal-gas density conversion (Torr to m^-3)
- Bunch duration and bunch length
- Effective perveance relation K_eff/K0 = 1 - eta
- Plotting functions import without requiring WarpX
"""

import math
import pytest
from plasma_column.beam import ProtonBeam, RFFocusedBeam
from plasma_column.gas import gas_density_m3, NeutralGas
from plasma_column.neutralization import keff_over_k0_from_eta
from plasma_column.plotting import setup_publication_style


def test_proton_velocity_30keV():
    """Verify 30 keV proton relativistic beta and velocity (~2.4e6 m/s)."""
    beam = ProtonBeam(energy_keV=30.0)
    assert 1.0 < beam.gamma < 1.001
    assert 0.0075 < beam.beta < 0.0085
    assert 2.39e6 < beam.velocity < 2.41e6


def test_ideal_gas_density_conversion():
    """Verify ideal gas density conversion at 1e-5 Torr and 300 K."""
    n_gas = gas_density_m3(1.0e-5, 300.0)
    # Expected: ~3.2e17 m^-3
    assert 3.1e17 < n_gas < 3.3e17
    # Zero pressure gives 0
    assert gas_density_m3(0.0) == 0.0
    gas_obj = NeutralGas(pressure_torr=1.0e-5, temperature_K=300.0)
    assert math.isclose(gas_obj.number_density, n_gas)


def test_bunch_duration_and_length():
    """Verify bunch phase duration and length calculations."""
    rf_beam = RFFocusedBeam(
        energy_keV=30.0,
        rf_frequency_hz=50.0e6,
        bunch_phase_width_deg=36.0,
    )
    assert math.isclose(rf_beam.bunch_duration_s, 2.0e-9, rel_tol=1e-5)
    assert 0.0047 < rf_beam.bunch_length_m < 0.0049


def test_effective_perveance_relation():
    """Verify K_eff/K0 = 1 - eta scaling."""
    assert keff_over_k0_from_eta(0.0) == 1.0
    assert math.isclose(keff_over_k0_from_eta(0.85), 0.15, rel_tol=1e-5)
    assert keff_over_k0_from_eta(1.0) == 0.0


def test_plotting_import_without_warpx():
    """Verify plotting functions can be imported and styled without pywarpx/WarpX."""
    setup_publication_style()
    assert True
