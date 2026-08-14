# 47 — RT-06: Add `method` Field to `SimulationCaseConfig` Schema

**Date:** 2026-08-14  
**Branch:** `main`  
**Commit:** `6edad2c`  
**Task file:** `docs/04_refactor_tasks/RT-06_add_method_field_to_schema.md`

---

## Summary

Fixed a latent `AttributeError` in `scripts/run_case.py:177` where
`config.method` was accessed but `SimulationCaseConfig` had no `method` field.
Also consolidated the method→CLI-flag translation as a prerequisite for RT-02.

## Changes Made

### `src/plasma_column/schema.py`
- Added `ALLOWED_METHODS: frozenset[str]` containing the four canonical
  simulation method strings: `vacuum`, `seeded_compensation`,
  `python_callback`, `cxx_mcc_custom`.
- Added `METHOD_ALIASES: dict[str, str]` mapping short-form YAML strings
  (`seeded` → `seeded_compensation`, `callback` → `python_callback`).
- Added `_normalise_method(raw)` — resolves alias, raises `ValueError` for
  unknown strings.
- Added `build_warpx_cmd_flags(method) -> list[str]` — single canonical source
  of truth for the method→WarpX CLI flag mapping.
- Added `method: str = "vacuum"` field to `SimulationCaseConfig`.
- Updated `from_dict()` to call `_normalise_method()` on the top-level
  `method:` key before construction.
- Extended `validate()` with:
  - Check that `self.method in ALLOWED_METHODS`.
  - Cross-field `UserWarning` when `method='vacuum'` but `numerics.mcc` is
    non-none (MCC has no effect in vacuum runs).

### `scripts/run_case.py`
- Added `build_warpx_cmd_flags` to the import.
- Replaced the 8-line duplicated `if/elif` method dispatch block with a
  single call: `cmd += build_warpx_cmd_flags(config.method)`.

### `cases/vacuum.yaml`
- Added `method: vacuum`.

### `cases/baseline_h2.yaml`
- Added `method: seeded_compensation`.

### `cases/baseline_kr.yaml`
- Added `method: seeded_compensation`.

### `tests/test_schema.py`
- Added 13 RT-06 acceptance tests covering:
  - `ALLOWED_METHODS` and `METHOD_ALIASES` importability
  - `method` field default (`"vacuum"`)
  - YAML parsing for `vacuum.yaml` and `baseline_h2.yaml`
  - Alias normalisation for `"seeded"` and `"callback"`
  - `ValueError` on unknown method string
  - `ValueError` in `validate()` for non-canonical direct construction
  - `build_warpx_cmd_flags` for all four canonical methods and one alias
  - `ValueError` in `build_warpx_cmd_flags` for unknown input
  - `UserWarning` when `method='vacuum'` + `mcc='electron_impact'`
  - No warning when `method='vacuum'` + `mcc='none'`

## Acceptance Criteria — All Met

- [x] `SimulationCaseConfig.method` is a validated field.
- [x] `ALLOWED_METHODS` frozenset is importable.
- [x] `SimulationCaseConfig.from_yaml("cases/vacuum.yaml").method == "vacuum"`.
- [x] Unknown method string raises `ValueError`.
- [x] `pytest -q tests/test_schema.py` — 21 passed.
- [x] Full suite `pytest -q` — 85 passed.
- [x] `run_case.py --dry_run` passes for all three baseline YAML files.
- [x] `run_scan.py --dry_run` passes for `cases/method_comparison.yaml`.

## Physics Limitations

None introduced. This is a schema/infrastructure change only; no simulation
physics or numerical parameters were altered.

## Follow-on

RT-02 (`deduplicate_method_dispatch`) can now proceed: `run_scan.py` still
contains the duplicate if/elif block and should be updated to call
`build_warpx_cmd_flags` exactly as `run_case.py` now does.
