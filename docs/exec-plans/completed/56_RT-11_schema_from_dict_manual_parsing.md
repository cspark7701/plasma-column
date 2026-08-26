# 56 — RT-11: Streamline `SimulationCaseConfig.from_dict` via Generic Typed Dataclass Helper

**Date:** 2026-08-15  
**Task file:** `docs/04_refactor_tasks/RT-11_schema_from_dict_manual_parsing.md`

---

## Summary

Replaced the manual 50+ line sub-field dictionary extraction in `SimulationCaseConfig.from_dict()` with a generic, recursive `_dataclass_from_dict(cls, data)` constructor helper in [`src/plasma_column/schema.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/schema.py). The helper uses `dataclasses.fields()` and `typing.get_type_hints()` to automatically instantiate and cast nested dataclasses (`BeamConfig`, `PlasmaConfig`, `SolenoidConfig`, `NumericsConfig`).

## Changes Made

### `src/plasma_column/schema.py`
- Implemented `_dataclass_from_dict(cls: type, data: dict[str, Any] | None) -> Any` with recursive support for nested dataclasses and primitive type casting (`int`, `float`, `str`).
- Refactored `SimulationCaseConfig.from_dict(cls, data)` to just 9 lines:
  - Normalizes `method` aliases.
  - Passes dictionary to `_dataclass_from_dict`.
  - Executes `validate()`.

### `tests/test_schema.py`
- Added `test_all_yaml_cases_roundtrip()` testing `from_yaml` -> `to_dict` -> `from_dict` lossless round-trips across all YAML files in `cases/`.

## Acceptance Criteria — All Met

- [x] `SimulationCaseConfig.from_dict` is ≤10 lines in length.
- [x] All existing YAML case files parse cleanly.
- [x] Round-trip `SimulationCaseConfig.from_dict(config.to_dict()) == config` passes losslessly.
- [x] `pytest -q tests/test_schema.py` — 23 passed.
- [x] Full test suite `pytest -q` — 91 passed.
- [x] `python scripts/audit_repo.py --root .` passes cleanly.

## Physics Limitations

None. Internal schema parsing and validation refactoring.
