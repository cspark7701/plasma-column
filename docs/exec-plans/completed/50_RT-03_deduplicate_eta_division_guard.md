# 50 — RT-03: Deduplicate Repeated `eta / (np + eps)` Safe-Division into a Helper

**Date:** 2026-08-15  
**Task file:** `docs/04_refactor_tasks/RT-03_deduplicate_eta_division_guard.md`

---

## Summary

Extracted the repeated safe-division pattern for computing neutralization fractions $\eta_e$ and $\eta_{\text{net}}$ into a single reusable helper function `safe_eta(ne, ni, np_val, eps=1e-30)` in [`src/plasma_column/diagnostics.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/diagnostics.py). Unified calculation across `compute_particle_number_metrics`, `compute_local_core_neutralization`, and `compute_local_neutralization_vs_z`, and removed duplicate-meaning dictionary keys (`_core` vs `_local`) from `compute_local_core_neutralization`.

## Changes Made

### `src/plasma_column/diagnostics.py`
- Defined `safe_eta(ne, ni, np_val, eps=1e-30) -> tuple[Any, Any]` supporting both scalar and vector inputs.
- Refactored `compute_particle_number_metrics` to use `safe_eta`.
- Refactored `compute_local_core_neutralization` to use `safe_eta` and removed duplicate keys (`eta_electron_only_core`, `eta_net_core`, `keff_over_k0_core`).
- Refactored `compute_local_neutralization_vs_z` to use `safe_eta` and unified $K_{\text{eff}}/K_0$ definition.

### `scripts/postprocess_case.py`
- Cleaned duplicate fallback keys in `core_info` dict.

### `tests/test_diagnostics_particle_number.py`
- Added unit test `test_safe_eta_scalar_and_vector` testing scalar, zero-proton, and NumPy vector inputs.

## Acceptance Criteria — All Met

- [x] A single `safe_eta` function is used across all three computation sites in `diagnostics.py`.
- [x] `compute_local_core_neutralization` returns a dict with clean canonical keys.
- [x] `pytest -q tests/test_diagnostics_particle_number.py tests/test_local_neutralization_masks.py` passed (9/9).
- [x] Full test suite `pytest -q` passed (87/87).

## Physics Limitations

None. Calculations are mathematically equivalent with unified zero-division guards.
