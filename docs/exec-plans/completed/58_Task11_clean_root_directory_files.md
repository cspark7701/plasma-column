# 58 — Clean Root Directory: Relocate Python Scripts and Notebooks

**Date:** 2026-08-15  

---

## Summary

Relocated all legacy notebooks and WarpX/PICMI Python simulation runner scripts from the repository root directory into their appropriate homes (`scripts/` for active simulation kernels and `archives/` for legacy analysis notebooks). The project root directory is now completely clean of `.py` and `.ipynb` files.

## Changes Made

### File Relocations
- Moved WarpX PICMI runner scripts to `scripts/`:
  - `plasma_column_mcc_picmi_v7.py` -> `scripts/plasma_column_mcc_picmi_v7.py`
  - `plasma_column_callback_source_picmi_v3.py` -> `scripts/plasma_column_callback_source_picmi_v3.py`
- Moved legacy root notebooks to `archives/`:
  - `plasma_column_analysis_plots.ipynb`
  - `plasma_column_analysis_plots_v2.ipynb`
  - `run_plasma_column_method_comparison.ipynb`
  - `run_python_callback_source_diagnostics_v2.ipynb`
  - `run_seeded_full_transport_diagnostics.ipynb`

### Schema and Runner Path Updates
- Updated `get_runner_script` in [`src/plasma_column/schema.py`](file:///home/cspark/Work/projects/plasma_column/src/plasma_column/schema.py) to resolve runner scripts inside `scripts/`.
- Updated [`scripts/_gen_notebooks.py`](file:///home/cspark/Work/projects/plasma_column/scripts/_gen_notebooks.py) and regenerated all modular run notebooks to target `scripts/plasma_column_mcc_picmi_v7.py` and `scripts/plasma_column_callback_source_picmi_v3.py`.
- Updated unit test assertions in [`tests/test_schema.py`](file:///home/cspark/Work/projects/plasma_column/tests/test_schema.py).
- Updated repository audit in [`scripts/audit_repo.py`](file:///home/cspark/Work/projects/plasma_column/scripts/audit_repo.py) to verify that the root directory remains free of `.py` and `.ipynb` files.

## Acceptance Criteria — All Met

- [x] Zero `.py` or `.ipynb` files in repository root.
- [x] `python scripts/run_case.py --case cases/vacuum.yaml --dry_run` passes.
- [x] `python scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run` passes.
- [x] `python scripts/audit_repo.py --root .` passes all 5 checks cleanly with OK status.
- [x] Full test suite `pytest -q` — 92 passed.

## Physics Limitations

None. Directory structure and path resolution modernization.
