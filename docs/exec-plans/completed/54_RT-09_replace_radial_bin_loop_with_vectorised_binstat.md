# 54 — RT-09: Replace $O(N_{\text{bins}})$ Python Loop in `compute_radial_density_profiles` with Vectorized `binned_statistic`

**Date:** 2026-08-15  
**Task file:** `docs/04_refactor_tasks/RT-09_replace_radial_bin_loop_with_vectorised_binstat.md`

---

## Summary

Replaced the $O(N_{\text{bins}})$ Python `for`-loop in `compute_radial_density_profiles()` with vectorized calls to `scipy.stats.binned_statistic(statistic="mean")`. This eliminates repeated boolean indexing masks across thousands of spatial grid points in postprocessing large 3D WarpX plotfile grids.

## Changes Made

### `src/plasma_column/diagnostics.py`
- Imported `from scipy.stats import binned_statistic`.
- Refactored `compute_radial_density_profiles` to compute `np_r`, `ne_r`, and `ni_r` via `binned_statistic` with `np.nan_to_num(..., nan=0.0)`.

### `tests/test_local_neutralization_masks.py`
- Added unit test `test_radial_density_profile_vectorization` verifying non-NaN DataFrame structure, peak on-axis values, and monotonic radial decay.

## Acceptance Criteria — All Met

- [x] No pure-Python bin iteration loop remains in `compute_radial_density_profiles`.
- [x] Vectorized output matches expected physics behavior and produces non-NaN DataFrames.
- [x] `pytest -q` — 89/89 passed.
- [x] `python scripts/audit_repo.py --root .` passes all checks cleanly.

## Physics Limitations

None. Vectorized binned averaging produces numerically identical mean densities within radial bins.
