# Execution Plan Summary: Clean Schema Checkpoint Test Warning

**Task Index**: 74  
**Date**: 2026-09-03  
**Subject**: Eliminate UserWarning in `test_schema_checkpoint_options` by explicitly configuring method='seeded_compensation'.

---

## 1. Description

In [`tests/test_schema.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_schema.py), `test_schema_checkpoint_options` parsed a dictionary via `SimulationCaseConfig.from_dict({"case_name": "test_chk2", ...})`. Because `method` was omitted, it defaulted to `"vacuum"`, while `numerics.mcc` defaulted to `"electron_impact"`.
The schema's cross-field consistency validator correctly emitted a `UserWarning: method='vacuum' but numerics.mcc='electron_impact'. MCC collisions have no effect in vacuum runs.`

---

## 2. Solution

Updated `test_schema_checkpoint_options` in [`tests/test_schema.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_schema.py) to explicitly specify `"method": "seeded_compensation"` in the test configuration dictionary, matching its intended non-vacuum context.

---

## 3. Verification

- Ran `python3 -m pytest -W error -v tests/test_schema.py`: All 24 tests passed with 0 warnings.
- Ran `python3 scripts/audit_repo.py --root .`: Audit passed cleanly with 105 passed tests (0 warnings, 0 failures).
