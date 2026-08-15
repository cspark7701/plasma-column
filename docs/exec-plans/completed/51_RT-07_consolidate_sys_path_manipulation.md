# 51 — RT-07: Consolidate Boilerplate `sys.path.insert` Across Scripts

**Date:** 2026-08-15  
**Task file:** `docs/04_refactor_tasks/RT-07_consolidate_sys_path_manipulation.md`

---

## Summary

Consolidated repetitive multi-line `sys.path.insert` path setup boilerplate from 17 standalone scripts into a single centralized [`scripts/_path_setup.py`](file:///home/cspark/Work/projects/plasma_column/scripts/_path_setup.py) module. Standardized path setup imports using a robust `try...except` pattern that supports both direct command-line execution from any working directory and package-style module imports.

## Changes Made

### `scripts/_path_setup.py`
- Created the authoritative path setup module defining `PROJECT_ROOT` and `SRC_DIR` and safely adding `src/` to `sys.path` if not already present.

### `scripts/*.py`
- Replaced redundant `sys.path.insert` boilerplate across all scripts with:
  ```python
  try:
      from _path_setup import PROJECT_ROOT
  except ImportError:
      from scripts._path_setup import PROJECT_ROOT
  ```
  or `import _path_setup  # noqa: F401`.

### `tests/test_warpx_patch_tracking.py`
- Updated test import to load `get_git_info` directly from `plasma_column.warpx_io`.

## Acceptance Criteria — All Met

- [x] No script duplicates `sys.path.insert` boilerplate for path setup.
- [x] `python scripts/run_case.py --case cases/vacuum.yaml --dry_run` runs cleanly from any working directory (e.g. `/tmp`).
- [x] `python scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run` runs cleanly.
- [x] `python -m compileall scripts src tests` clean.
- [x] `pytest -q` — 87 passed.

## Physics Limitations

None. Pure refactoring of path setup and script imports.
