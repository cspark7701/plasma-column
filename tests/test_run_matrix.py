"""
tests/test_run_matrix.py

Unit tests for run_matrix.py ScanMatrix builder, dry-run dispatch, and result collection.
"""

import tempfile
import shutil
from pathlib import Path
import pytest
import pandas as pd

from plasma_column.run_matrix import (
    ScanParameter,
    ScanMatrix,
    build_scan_dataframe,
    run_scan_matrix,
    collect_scan_results,
    save_scan_summary,
    load_scan_summary,
)


def test_build_scan_dataframe():
    matrix = ScanMatrix(
        scan_name="test_sweep",
        script=None,
        parameters=[
            ScanParameter("pressure_torr", [1.0e-5, 2.0e-5]),
        ],
        gases=["H2", "Kr"],
        methods=["seeded_compensation", "vacuum"],
        fixed={"max_steps": 100},
    )

    df = build_scan_dataframe(matrix)
    # 2 gases * 2 methods * 2 pressures = 8 cases
    assert len(df) == 8
    assert "case_name" in df.columns
    assert "pressure_torr" in df.columns
    assert "gas" in df.columns
    assert "method" in df.columns
    assert "max_steps" in df.columns


def test_run_scan_matrix_dry_run():
    td = Path(tempfile.mkdtemp())
    try:
        matrix = ScanMatrix(
            scan_name="dry_sweep",
            script=None,
            parameters=[ScanParameter("pressure_torr", [1.0e-5])],
            gases=["H2"],
            methods=["vacuum"],
            dry_run=True,
            runs_root=td,
        )

        scan_df = build_scan_dataframe(matrix)
        results = run_scan_matrix(scan_df, matrix, cores=2, gpu="auto")

        assert len(results) == 1
        assert results[0]["returncode"] == "dry_run"
        out_dir = results[0]["out_dir"]
        assert (out_dir / "scan_metadata.json").exists()
    finally:
        shutil.rmtree(td)


def test_collect_scan_results():
    td = Path(tempfile.mkdtemp())
    try:
        matrix = ScanMatrix(
            scan_name="collect_sweep",
            parameters=[ScanParameter("pressure_torr", [1.0e-5])],
            gases=["H2"],
            methods=["seeded"],
            runs_root=td,
        )
        scan_df = build_scan_dataframe(matrix)
        case_name = scan_df["case_name"].iloc[0]
        case_dir = td / case_name
        rdir = case_dir / "reducedfiles"
        rdir.mkdir(parents=True)

        pn_file = rdir / "particle_number.txt"
        pn_file.write_text(
            "#[0]step() [1]time(s) [2]tot_macro [3]p_macro [4]e_macro [5]p_phys [6]e_phys [7]i_phys\n"
            "0 0.0 10 10 0 1000 0 0\n"
            "100 1e-9 10 10 0 1000 900 100\n"
        )

        res_df = collect_scan_results(scan_df, td)
        assert len(res_df) == 1
        assert res_df.loc[0, "status"] == "ok"
        assert res_df.loc[0, "n_steps"] == 2
        assert res_df.loc[0, "final_eta_electron_only"] == pytest.approx(0.9)
        assert res_df.loc[0, "final_eta_net"] == pytest.approx(0.8)

        # Test save and load
        summary_csv = td / "summary.csv"
        save_scan_summary(res_df, summary_csv)
        assert summary_csv.exists()
        loaded_df = load_scan_summary(summary_csv)
        assert len(loaded_df) == 1
    finally:
        shutil.rmtree(td)


if __name__ == "__main__":
    pytest.main([__file__])
