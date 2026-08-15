# 57 — RT-12: Fix `RESULTS_DIR` / `RUNS_DIR` Alias Confusion in `notebook_utils.py`

**Date:** 2026-08-15  
**Task file:** `docs/04_refactor_tasks/RT-12_notebook_utils_RESULTS_RUNS_alias.md`

---

## Summary

Corrected `RUNS_DIR` definition in `COMMON_IMPORTS` inside [`src/plasma_column/notebook_utils.py`](file:///home/cspark/Work/projects/plasma_column/src/plasma_column/notebook_utils.py) to point to `_ROOT / 'runs'` (raw simulation outputs) rather than duplicating `_ROOT / 'results'` (processed diagnostic tables). Clarified directory roles with comments and re-generated all notebooks via [`scripts/_gen_notebooks.py`](file:///home/cspark/Work/projects/plasma_column/scripts/_gen_notebooks.py).

## Changes Made

### `src/plasma_column/notebook_utils.py`
- Updated `COMMON_IMPORTS`:
  - `RESULTS_DIR = _ROOT / 'results'  # Processed diagnostic CSV/JSON results`
  - `RUNS_DIR    = _ROOT / 'runs'     # Raw simulation output directories (gitignored)`
  - Added `RUNS_DIR.mkdir(exist_ok=True)`.

### Notebook Generation
- Executed `scripts/_gen_notebooks.py` to regenerate all 11 modular run and analysis notebooks with the updated path definitions.

### `tests/test_plotting.py`
- Added unit test `test_notebook_utils_common_imports` verifying distinct `RESULTS_DIR`, `RUNS_DIR`, and `PLOTS_DIR` in `COMMON_IMPORTS`.

## Acceptance Criteria — All Met

- [x] `RESULTS_DIR` (`results/`) and `RUNS_DIR` (`runs/`) reference distinct paths.
- [x] `scripts/_gen_notebooks.py` runs cleanly.
- [x] Generated notebooks load `RUNS_DIR` as `runs/`.
- [x] `pytest -q` — 92 passed.
- [x] `python scripts/audit_repo.py --root .` passes cleanly.

## Physics Limitations

None. Internal notebook path constant refactoring.
