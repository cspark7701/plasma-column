# 53 — RT-08: Archive Root-Level Legacy Scripts and Remove Stale Notebook Versions

**Date:** 2026-08-15  
**Task file:** `docs/04_refactor_tasks/RT-08_archive_root_level_legacy_scripts.md`

---

## Summary

Archived root-level legacy standalone scripts and intermediary notebook revisions into [`archives/`](file:///home/cspark/Work/projects/plasma-column/archives/). Clarified canonical CLI and notebook entry points in [`README.md`](file:///home/cspark/Work/projects/plasma-column/README.md), and added automated verification in [`scripts/audit_repo.py`](file:///home/cspark/Work/projects/plasma-column/scripts/audit_repo.py).

## Changes Made

### File Archiving
- Moved superseded legacy scripts to `archives/`:
  - `particle_number_diagnostics.py`
  - `particle_number_diagnostics_v2.py`
  - `particle_number_diagnostics_compare.py`
  - `plasma_column_analysis_plots_v2.py`
  - `plasma_column_analysis_plots_v2--1.ipynb`

### Root-Level Runners
- Retained canonical WarpX/PICMI kernels `plasma_column_mcc_picmi_v7.py` and `plasma_column_callback_source_picmi_v3.py` at the project root for subprocess execution dispatched by `scripts/run_case.py` and `scripts/run_scan.py`.

### Documentation and Auditing
- Updated [`README.md`](file:///home/cspark/Work/projects/plasma-column/README.md) workflow summary to point directly to `scripts/run_case.py` and modular `notebooks/`.
- Added section `[3. Legacy Root Files Check]` to [`scripts/audit_repo.py`](file:///home/cspark/Work/projects/plasma-column/scripts/audit_repo.py) to guard against unarchived root legacy scripts.

## Acceptance Criteria — All Met

- [x] Legacy root-level standalone diagnostics and plots scripts moved to `archives/`.
- [x] `python scripts/run_case.py --case cases/vacuum.yaml --dry_run` runs cleanly.
- [x] `.ipynb_checkpoints` entries are present in `.gitignore`.
- [x] `scripts/audit_repo.py --root .` passes all 5 checks with OK status.
- [x] `pytest -q` — 88/88 passed.

## Physics Limitations

None. Archiving non-canonical legacy utilities.
