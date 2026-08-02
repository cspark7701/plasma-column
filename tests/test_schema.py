"""
tests/test_schema.py

Unit tests for SimulationCaseConfig dataclass schema, validation rules, and YAML parsing.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from plasma_column.schema import (
    SimulationCaseConfig,
    BeamConfig,
    PlasmaConfig,
    SolenoidConfig,
    NumericsConfig,
)


def test_default_simulation_case_config():
    config = SimulationCaseConfig(case_name="test_default")
    assert config.case_name == "test_default"
    assert config.beam.energy_keV == 30.0
    assert config.beam.current_mA == 10.0
    assert config.plasma.gas == "H2"
    assert config.numerics.nx == 32
    config.validate()


def test_from_yaml_baseline_h2():
    yaml_path = Path(__file__).resolve().parent.parent / "cases" / "baseline_h2.yaml"
    config = SimulationCaseConfig.from_yaml(yaml_path)
    assert config.case_name == "seeded_H2_baseline"
    assert config.beam.energy_keV == 30.0
    assert config.plasma.gas == "H2"
    assert config.plasma.pressure_torr == 1.0e-5
    assert config.numerics.nz == 256


def test_validation_errors():
    # Empty case name
    with pytest.raises(ValueError, match="case_name cannot be empty"):
        SimulationCaseConfig(case_name="").validate()

    # Negative energy
    with pytest.raises(ValueError, match="Beam energy_keV must be positive"):
        SimulationCaseConfig(case_name="bad_energy", beam=BeamConfig(energy_keV=-10.0)).validate()

    # Negative pressure
    with pytest.raises(ValueError, match="Pressure_torr cannot be negative"):
        SimulationCaseConfig(case_name="bad_pressure", plasma=PlasmaConfig(pressure_torr=-1e-5)).validate()

    # Bad grid dimensions
    with pytest.raises(ValueError, match="Grid dimensions must be positive integers"):
        SimulationCaseConfig(case_name="bad_grid", numerics=NumericsConfig(nx=0)).validate()

    # Bad z bounds
    with pytest.raises(ValueError, match="must be strictly greater than zmin_m"):
        SimulationCaseConfig(case_name="bad_z", numerics=NumericsConfig(zmin_m=0.5, zmax_m=0.2)).validate()


def test_to_dict_roundtrip():
    config = SimulationCaseConfig(case_name="roundtrip_test")
    d = config.to_dict()
    assert d["case_name"] == "roundtrip_test"
    reconstructed = SimulationCaseConfig.from_dict(d)
    assert reconstructed.case_name == config.case_name
    assert reconstructed.beam.energy_keV == config.beam.energy_keV
