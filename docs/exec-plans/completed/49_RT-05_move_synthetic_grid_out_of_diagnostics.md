# 49 — RT-05: Move `generate_synthetic_3d_grid` Out of `diagnostics.py`

**Date:** 2026-08-15  
**Task file:** `docs/04_refactor_tasks/RT-05_move_generate_synthetic_grid_out_of_diagnostics.md`

---

## Summary

Decoupled the non-operational test/illustration helper `generate_synthetic_3d_grid()` from the production diagnostics module [`src/plasma_column/diagnostics.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/diagnostics.py) into [`src/plasma_column/_testing.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/_testing.py) and created [`tests/conftest.py`](file:///home/cspark/Work/projects/plasma-column/tests/conftest.py). In [`scripts/postprocess_case.py`](file:///home/cspark/Work/projects/plasma-column/scripts/postprocess_case.py), fixed the bug where synthetic data was silently substituted when plotfiles were available or missing, replacing it with actual 3D field loading via `load_plotfile_densities()` and explicit domain warnings when spatial data is absent.

## Changes Made

### `src/plasma_column/_testing.py`
- Created private testing/illustration module containing `generate_synthetic_3d_grid()`.

### `src/plasma_column/diagnostics.py`
- Removed `generate_synthetic_3d_grid()` from operational diagnostics to keep the public API clean and fast.

### `tests/conftest.py` & `tests/test_local_neutralization_masks.py`
- Created `tests/conftest.py` with pytest fixture `synthetic_3d_grid`.
- Updated test imports to load `generate_synthetic_3d_grid` from `plasma_column._testing`.

### `src/plasma_column/warpx_io.py`
- Enhanced `load_plotfile_densities()` to extract 3D species density grids and spatial coordinates using `yt` covering grid.

### `scripts/postprocess_case.py`
- Removed `generate_synthetic_3d_grid` import.
- Integrated `load_plotfile_densities()` to read real spatial grids when plotfiles are present.
- When spatial plotfiles are absent, issues `warn_global_count_limitation()` and does not fabricate fake Gaussian profiles.

### `scripts/make_plots.py`, `scripts/make_paper_figures.py`, `scripts/_gen_notebooks.py`, and notebooks
- Updated imports to reference `plasma_column._testing.generate_synthetic_3d_grid`.

## Acceptance Criteria — All Met

- [x] `generate_synthetic_3d_grid` is removed from `diagnostics.py`.
- [x] `postprocess_case.py` does not silently substitute synthetic data when real plotfiles exist or when plotfiles are absent.
- [x] `postprocess_case.py --case-dir results/seeded_H2_baseline --dry_run` passes cleanly.
- [x] `pytest -q` — 86 passed.

## Physics Limitations

No simulation physics changed. Prevents deceptive synthetic spatial compensation data from being written as real simulation output.
