"""
tests/test_run_scan.py

Unit tests for matrix scan loading and case configuration merging.
"""

import sys
from pathlib import Path
import tempfile
import textwrap
import yaml
import pytest

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from plasma_column.schema import merge_dicts, ScanMatrixConfig


def test_merge_dicts():
    default = {"beam": {"energy_keV": 30.0, "current_mA": 10.0}, "solenoid": {"Bz_T": 0.15}}
    override = {"beam": {"current_mA": 15.0}, "gas": "H2"}

    merged = merge_dicts(default, override)
    assert merged["beam"]["energy_keV"] == 30.0
    assert merged["beam"]["current_mA"] == 15.0
    assert merged["solenoid"]["Bz_T"] == 0.15
    assert merged["gas"] == "H2"


def test_matrix_yaml_structure_and_schema():
    matrix_file = project_root / "cases" / "method_comparison.yaml"
    assert matrix_file.exists()

    # Test via ScanMatrixConfig
    matrix_cfg = ScanMatrixConfig.from_yaml(matrix_file)
    assert matrix_cfg.matrix_name == "plasma_column_method_comparison"
    assert len(matrix_cfg.cases) >= 9
    assert matrix_cfg.cases[0].case_name == "vacuum_reference"
    assert matrix_cfg.cases[0].method == "vacuum"


if __name__ == "__main__":
    pytest.main([__file__])
