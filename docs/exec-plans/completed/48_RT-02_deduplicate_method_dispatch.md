# 48 — RT-02: Deduplicate Method-to-CLI-Flag Dispatch Logic

**Date:** 2026-08-14  
**Branch:** `main`  
**Commit:** `c35470c`  
**Task file:** `docs/04_refactor_tasks/RT-02_deduplicate_method_dispatch.md` (and `RT-01_extract_git_utility_to_warpx_io.md`)

---

## Summary

Deduplicated the method-to-CLI-flag mapping between `scripts/run_case.py` and `scripts/run_scan.py` by centralizing command-line flag creation into `build_warpx_cmd_flags()` in `src/plasma_column/schema.py`. Concurrently resolved RT-01 by moving `get_git_info()` and `collect_metadata()` into `src/plasma_column/warpx_io.py`, eliminating the fragile cross-script import in `scripts/run_scan.py`.

## Changes Made

### `src/plasma_column/warpx_io.py`
- Implemented `get_git_info(path: Path) -> dict[str, str]` and `collect_metadata(...) -> dict[str, Any]`.
- Exported them in `__all__` for clean package-level consumption.

### `scripts/run_case.py`
- Removed redundant local definitions of `get_git_info()` and `collect_metadata()`.
- Imported `get_git_info` and `collect_metadata` from `plasma_column.warpx_io`.
- Imported `build_warpx_cmd_flags` from `plasma_column.schema`.
- Replaced the duplicate `if/elif` method dispatch block with `cmd += build_warpx_cmd_flags(config.method)`.

### `scripts/run_scan.py`
- Removed the cross-script import `from scripts.run_case import collect_metadata`.
- Imported `collect_metadata` from `plasma_column.warpx_io`.
- Imported `build_warpx_cmd_flags` from `plasma_column.schema`.
- Replaced the duplicate `if/elif` method dispatch block with `cmd += build_warpx_cmd_flags(config.method)`.
- Cleaned up unnecessary root `sys.path.insert`.

## Acceptance Criteria — All Met

- [x] `build_warpx_cmd_flags(method)` is the single canonical source of truth for WarpX CLI flags across all runner scripts.
- [x] Cross-script imports between `run_scan.py` and `run_case.py` are eliminated.
- [x] `python scripts/run_case.py --case cases/vacuum.yaml --dry_run` passes cleanly.
- [x] `python scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run` passes cleanly.
- [x] `pytest -q` — 85 passed.

## Physics Limitations

None. This is purely a refactoring and code deduplication task.
