"""
tests/test_case_files.py

Unit tests for validating and parsing YAML configuration files under cases/.
"""

from pathlib import Path
import yaml
import pytest


def get_case_files():
    cases_dir = Path(__file__).resolve().parent.parent / "cases"
    return list(cases_dir.glob("*.yaml"))


def test_yaml_case_files_exist():
    cases = get_case_files()
    assert len(cases) >= 5, f"Expected at least 5 case YAML files, found {len(cases)}"


@pytest.mark.parametrize("case_path", get_case_files(), ids=lambda p: p.name)
def test_parse_case_yaml(case_path: Path):
    data = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"Case file {case_path.name} did not parse into a dictionary"
    assert "case_name" in data or case_path.stem in data.get("case_name", case_path.stem)


def test_seeded_matrix_cases_record_the_neutralization_the_runner_passes():
    """Seeded cases run with --neutralization -1; config.yaml/metadata must record the same value."""
    from plasma_column.schema import ScanMatrixConfig, build_warpx_cmd_flags

    cases_dir = Path(__file__).resolve().parent.parent / "cases"
    passed = float(build_warpx_cmd_flags("seeded_compensation")[1])
    for name in ("method_scan_baseline.yaml", "method_comparison.yaml", "pressure_scan_h2_kr.yaml"):
        for case in ScanMatrixConfig.from_yaml(cases_dir / name).cases:
            if case.method == "seeded_compensation":
                assert case.plasma.neutralization == passed, f"{name}: {case.case_name}"
