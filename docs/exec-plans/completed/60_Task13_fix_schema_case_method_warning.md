# 60 — Fix Root-Cause Warning in `test_all_yaml_cases_roundtrip`

**Date:** 2026-08-15  

---

## Summary

Resolved the root-cause configuration discrepancy triggering `UserWarning: method='vacuum' but numerics.mcc='electron_impact'`. Explicitly set `method: seeded_compensation` in [`cases/bunched_h2.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/bunched_h2.yaml) and [`cases/bunched_kr.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/bunched_kr.yaml), and updated [`tests/test_schema.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_schema.py) to dynamically skip multi-case scan matrix files.

## Changes Made

### Configuration Files
- [`cases/bunched_h2.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/bunched_h2.yaml): Added `method: seeded_compensation`.
- [`cases/bunched_kr.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/bunched_kr.yaml): Added `method: seeded_compensation`.

### `tests/test_schema.py`
- Updated `test_all_yaml_cases_roundtrip` to check if a YAML file is a multi-case matrix scan configuration (`"matrix_name" in content`) before attempting single-case schema parsing.

## Acceptance Criteria — All Met

- [x] Zero pytest warnings emitted during test run.
- [x] `cases/bunched_h2.yaml` and `cases/bunched_kr.yaml` properly specify their simulation method.
- [x] `pytest -q` — 92 passed with 0 warnings.
- [x] `python scripts/audit_repo.py --root .` passes all checks cleanly.

## Physics Limitations

None. Case YAML schema compliance.
