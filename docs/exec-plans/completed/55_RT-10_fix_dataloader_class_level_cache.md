# 55 — RT-10: Fix Class-Level Mutable Cache in `DataLoader` for Thread-Safety and Test Isolation

**Date:** 2026-08-15  
**Task file:** `docs/04_refactor_tasks/RT-10_fix_dataloader_class_level_cache.md`

---

## Summary

Refactored [`DataLoader`](file:///home/cspark/Work/projects/plasma_column/src/plasma_column/diagnostics.py) to ensure thread-safe caching using a `threading.Lock` across all cache lookups, insertions, clearing, and inspect methods. Streamlined the delegation between `DataLoader.load_particle_number` and `load_particle_number_diagnostic`, and added an automatic test teardown fixture in [`tests/conftest.py`](file:///home/cspark/Work/projects/plasma_column/tests/conftest.py) to guarantee clean test isolation.

## Changes Made

### `src/plasma_column/diagnostics.py`
- Added `_lock = threading.Lock()` to `DataLoader`.
- Wrapped all `_cache` accesses (`load_particle_number`, `load_local_neutralization`, `load_case_metadata`, `clear_cache`, `cache_info`) within `with cls._lock:`.
- Clarified delegation: `DataLoader.load_particle_number` calls `load_particle_number_diagnostic(path, use_cache=False)` directly, avoiding circular caching logic.

### `tests/conftest.py`
- Added `autouse=True` fixture `clear_dataloader_cache` to clear the cache before and after every test invocation.

### `tests/test_dataloader.py`
- Created unit tests covering:
  - Cache hit and `st_mtime` invalidation when underlying files are modified.
  - Metadata caching.
  - ThreadPoolExecutor concurrent access across 8 parallel worker threads.

## Acceptance Criteria — All Met

- [x] `DataLoader._cache` is protected by `threading.Lock` and thread-safe.
- [x] No circular double-caching code path between `DataLoader` and `load_particle_number_diagnostic`.
- [x] `pytest -q tests/test_dataloader.py` passes (3/3).
- [x] Full test suite `pytest -q` passes without stale-cache leakage (90/90).
- [x] `python scripts/audit_repo.py --root .` passes cleanly.

## Physics Limitations

None. Internal I/O caching refactoring.
