"""
tests/test_run_matrix.py

Unit tests for ScanParameter, ScanMatrix dataclasses, matrix DataFrame building, and scan result aggregation.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from plasma_column.run_matrix import (
    ScanParameter,
    ScanMatrix,
    build_scan_dataframe,
    collect_scan_results,
)


def test_scan_parameter_and_matrix_defaults():
    param = ScanParameter(name="pressure_torr", values=[1e-6, 1e-5])
    matrix = ScanMatrix(
        scan_name="test_scan",
        script=Path("scripts/run_case.py"),
        parameters=[param],
        gases=["H2", "Kr"],
        methods=["seeded"],
    )
    assert len(matrix.parameters) == 1
    assert matrix.gases == ["H2", "Kr"]


def test_build_scan_dataframe():
    param = ScanParameter(name="pressure_torr", values=[1e-6, 1e-5])
    matrix = ScanMatrix(
        scan_name="method_comp",
        script=Path("scripts/run_case.py"),
        parameters=[param],
        gases=["H2", "Kr"],
        methods=["seeded", "callback"],
    )
    # 2 gases * 2 methods * 2 pressures = 8 combinations
    df = build_scan_dataframe(matrix)
    assert len(df) == 8
    assert "case_name" in df.columns
    assert "gas" in df.columns
    assert "method" in df.columns
    assert "pressure_torr" in df.columns

    # Verify case naming convention
    first_case = df.iloc[0]["case_name"]
    assert first_case.startswith("method_comp_H2_seeded_")


def test_collect_scan_results_empty(tmp_path: Path):
    param = ScanParameter(name="pressure_torr", values=[1e-5])
    matrix = ScanMatrix(
        scan_name="empty_test",
        script=Path("scripts/run_case.py"),
        parameters=[param],
        gases=["H2"],
        methods=["seeded"],
        runs_root=tmp_path,
    )
    df_scan = build_scan_dataframe(matrix)
    # No actual runs exist in tmp_path -> gracefully fills with NaN/fallback values
    df_res = collect_scan_results(df_scan, runs_root=tmp_path)
    assert len(df_res) == 1
    assert "case_name" in df_res.columns
