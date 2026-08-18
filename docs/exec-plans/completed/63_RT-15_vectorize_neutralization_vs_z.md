# 63 — RT-15: Vectorize `compute_local_neutralization_vs_z` in `diagnostics.py`

**Date:** 2026-08-18  
**Task file:** `docs/04_refactor_tasks/RT-15_vectorize_neutralization_vs_z.md`

---

## Summary

Replaced the $O(N_z)$ Python slice loop in [`compute_local_neutralization_vs_z`](file:///home/cspark/Work/projects/plasma_column/src/plasma_column/diagnostics.py) with a vectorized 2D masked NumPy array reduction across spatial axes `(0, 1)`.

## Changes Made

### `src/plasma_column/diagnostics.py`
- Vectorized `compute_local_neutralization_vs_z`:
  - Applied 2D boolean mask `transverse_mask` across 3D arrays: `np_3d[transverse_mask, :]`, `ne_3d[transverse_mask, :]`, and `ni_3d[transverse_mask, :]`.
  - Computed transverse mean simultaneously across all $N_z$ slices using `np.mean(..., axis=0)`.
  - Vectorized division and guard through `safe_eta(ne_z_avg, ni_z_avg, np_z_avg)`.
  - Handled edge cases with 0 active masked cells gracefully.

### `tests/test_local_neutralization_masks.py`
- Added unit test `test_vectorized_neutralization_vs_z_equivalence` testing standard $N_z=128$ 3D grids and empty mask edge cases ($r_{\text{core}}=0$).

## Acceptance Criteria — All Met

- [x] `compute_local_neutralization_vs_z` uses no Python `for` loops over $N_z$.
- [x] Output values match loop baseline exactly.
- [x] `pytest -q tests/test_local_neutralization_masks.py` passes (7/7).
- [x] Full test suite `pytest -q` passes (97/97).
- [x] `python scripts/audit_repo.py --root .` passes all checks.

## Physics Limitations

None. Array reduction optimization.
