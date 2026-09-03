"""
tests/test_schema.py

Unit tests for SimulationCaseConfig dataclass schema, validation rules, and YAML parsing.
Includes RT-06 tests: method field, ALLOWED_METHODS, alias normalisation,
build_warpx_cmd_flags, and cross-field consistency checks.
"""

from __future__ import annotations

import warnings
import pytest
from pathlib import Path

from plasma_column.schema import (
    SimulationCaseConfig,
    BeamConfig,
    PlasmaConfig,
    SolenoidConfig,
    NumericsConfig,
    ALLOWED_METHODS,
    METHOD_ALIASES,
    build_warpx_cmd_flags,
    get_runner_script,
)


# ── Existing schema tests ──────────────────────────────────────────────────────

def test_default_simulation_case_config():
    config = SimulationCaseConfig(case_name="test_default")
    assert config.case_name == "test_default"
    assert config.beam.energy_keV == 30.0
    assert config.beam.current_mA == 10.0
    assert config.plasma.gas == "H2"
    assert config.numerics.nx == 32
    # Default NumericsConfig has mcc='electron_impact'; default method='vacuum',
    # so the cross-field consistency check emits a UserWarning — suppress it here.
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        config.validate()


def test_from_yaml_baseline_h2():
    yaml_path = Path(__file__).resolve().parent.parent / "cases" / "baseline_h2.yaml"
    config = SimulationCaseConfig.from_yaml(yaml_path)
    assert config.case_name == "seeded_H2_baseline"
    assert config.beam.energy_keV == 30.0
    assert config.plasma.gas == "H2"
    assert config.plasma.pressure_torr == 1.0e-5
    assert config.numerics.nz == 512
    assert config.numerics.nx == 64
    assert config.numerics.cfl == 0.5
    assert config.numerics.nppc_beam == 16


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
    config = SimulationCaseConfig(case_name="roundtrip_test", method="seeded_compensation")
    d = config.to_dict()
    assert d["case_name"] == "roundtrip_test"
    reconstructed = SimulationCaseConfig.from_dict(d)
    assert reconstructed.case_name == config.case_name
    assert reconstructed.beam.energy_keV == config.beam.energy_keV
    assert reconstructed.to_dict() == config.to_dict()


def test_all_yaml_cases_roundtrip():
    """Verify all single-case YAML files parse, validate, and round-trip losslessly."""
    import yaml
    cases_dir = Path(__file__).resolve().parent.parent / "cases"
    for yaml_file in sorted(cases_dir.glob("*.yaml")):
        with open(yaml_file, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}
        if "matrix_name" in content:
            continue  # matrix scan configuration, not a single case
        config = SimulationCaseConfig.from_yaml(yaml_file)
        assert config.case_name
        d = config.to_dict()
        reconstructed = SimulationCaseConfig.from_dict(d)
        assert reconstructed.to_dict() == d


# ── RT-06: method field tests ──────────────────────────────────────────────────

def test_allowed_methods_importable():
    """ALLOWED_METHODS frozenset must be importable and contain the four canonical values."""
    assert isinstance(ALLOWED_METHODS, frozenset)
    assert "vacuum" in ALLOWED_METHODS
    assert "seeded_compensation" in ALLOWED_METHODS
    assert "python_callback" in ALLOWED_METHODS
    assert "cxx_mcc_custom" in ALLOWED_METHODS


def test_method_aliases_importable():
    assert METHOD_ALIASES["seeded"] == "seeded_compensation"
    assert METHOD_ALIASES["callback"] == "python_callback"


def test_default_method_is_vacuum():
    """SimulationCaseConfig.method defaults to 'vacuum'."""
    config = SimulationCaseConfig(case_name="default_method_test")
    assert config.method == "vacuum"


def test_from_yaml_vacuum_method():
    """cases/vacuum.yaml must parse to method='vacuum'."""
    yaml_path = Path(__file__).resolve().parent.parent / "cases" / "vacuum.yaml"
    config = SimulationCaseConfig.from_yaml(yaml_path)
    assert config.method == "vacuum"


def test_from_yaml_h2_method():
    """cases/baseline_h2.yaml must parse to method='seeded_compensation'."""
    yaml_path = Path(__file__).resolve().parent.parent / "cases" / "baseline_h2.yaml"
    config = SimulationCaseConfig.from_yaml(yaml_path)
    assert config.method == "seeded_compensation"


def test_alias_seeded_normalised():
    """Short alias 'seeded' must be normalised to 'seeded_compensation'."""
    config = SimulationCaseConfig.from_dict({"case_name": "alias_test", "method": "seeded"})
    assert config.method == "seeded_compensation"


def test_alias_callback_normalised():
    """Short alias 'callback' must be normalised to 'python_callback'."""
    config = SimulationCaseConfig.from_dict({"case_name": "cb_test", "method": "callback"})
    assert config.method == "python_callback"


def test_unknown_method_raises():
    """An unrecognised method string must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown simulation method"):
        SimulationCaseConfig.from_dict({"case_name": "bad_method", "method": "not_a_real_method"})


def test_invalid_canonical_method_in_validate():
    """Directly constructing with an invalid canonical method should fail validate()."""
    config = SimulationCaseConfig(case_name="bad", method="not_canonical")
    with pytest.raises(ValueError, match="not in ALLOWED_METHODS"):
        config.validate()


# ── RT-06: build_warpx_cmd_flags tests ────────────────────────────────────────

def test_build_flags_vacuum():
    assert build_warpx_cmd_flags("vacuum") == ["--neutralization", "0.0"]


def test_build_flags_seeded_compensation():
    assert build_warpx_cmd_flags("seeded_compensation") == ["--neutralization", "-1"]


def test_build_flags_alias_seeded():
    """Alias 'seeded' must be resolved by build_warpx_cmd_flags."""
    assert build_warpx_cmd_flags("seeded") == ["--neutralization", "-1"]


def test_build_flags_python_callback():
    flags = build_warpx_cmd_flags("python_callback")
    assert flags == ["--enable_ionization_source", "1"]


def test_build_flags_cxx_mcc_custom():
    assert build_warpx_cmd_flags("cxx_mcc_custom") == ["--mcc", "electron_impact"]


def test_build_flags_unknown_raises():
    with pytest.raises(ValueError, match="Unknown simulation method"):
        build_warpx_cmd_flags("definitely_not_real")


def test_get_runner_script():
    """Verify correct runner script is selected for each method."""
    root = Path(__file__).resolve().parent.parent
    assert get_runner_script("vacuum", root) == root / "scripts" / "plasma_column_mcc_picmi_v7.py"
    assert get_runner_script("seeded_compensation", root) == root / "scripts" / "plasma_column_mcc_picmi_v7.py"
    assert get_runner_script("cxx_mcc_custom", root) == root / "scripts" / "plasma_column_mcc_picmi_v7.py"
    assert get_runner_script("python_callback", root) == root / "scripts" / "plasma_column_callback_source_picmi_v3.py"
    # Aliases
    assert get_runner_script("seeded", root) == root / "scripts" / "plasma_column_mcc_picmi_v7.py"
    assert get_runner_script("callback", root) == root / "scripts" / "plasma_column_callback_source_picmi_v3.py"


# ── RT-06: cross-field consistency warning ─────────────────────────────────────

def test_vacuum_with_mcc_warns():
    """method='vacuum' combined with a non-none mcc setting must emit UserWarning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        SimulationCaseConfig(
            case_name="warn_test",
            method="vacuum",
            numerics=NumericsConfig(mcc="electron_impact"),
        ).validate()
    assert any("MCC collisions have no effect" in str(w.message) for w in caught)


def test_vacuum_with_mcc_none_no_warn():
    """method='vacuum' with mcc='none' must not emit any warning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        SimulationCaseConfig(
            case_name="no_warn_test",
            method="vacuum",
            numerics=NumericsConfig(mcc="none"),
        ).validate()
    assert not any("MCC" in str(w.message) for w in caught)


def test_schema_checkpoint_options():
    cfg = SimulationCaseConfig(case_name="test_chk")
    assert hasattr(cfg.numerics, "checkpoint_period")
    assert cfg.numerics.checkpoint_period == 0
    assert hasattr(cfg.numerics, "restart_from")
    assert cfg.numerics.restart_from is None

    cfg2 = SimulationCaseConfig.from_dict({
        "case_name": "test_chk2",
        "method": "seeded_compensation",
        "numerics": {"checkpoint_period": 500, "restart_from": "auto"}
    })
    assert cfg2.numerics.checkpoint_period == 500
    assert cfg2.numerics.restart_from == "auto"
