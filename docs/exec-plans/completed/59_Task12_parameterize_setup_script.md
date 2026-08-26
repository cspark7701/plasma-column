# 59 — Parameterize `setup.sh` for Machine Portability

**Date:** 2026-08-15  

---

## Summary

Removed hardcoded user paths (`/home/cspark/...`) from [`setup.sh`](file:///home/cspark/Work/projects/plasma-column/setup.sh). Replaced them with portable environment variable expansions (`$HOME`, `$SIMULATION_CODES_DIR`, `$WARPX_INSTALL_DIR`, `$WARPX_DATA_DIR`, `$CONDA_ENV_NAME`) and directory existence guards.

## Changes Made

### `setup.sh`
- Replaced hardcoded paths with configurable defaults:
  - `SIMULATION_CODES_DIR="${SIMULATION_CODES_DIR:-$HOME/Work/simulation_codes-working}"`
  - `WARPX_INSTALL_DIR="${WARPX_INSTALL_DIR:-$SIMULATION_CODES_DIR/warpx/install}"`
  - `WARPX_DATA_DIR="${WARPX_DATA_DIR:-$SIMULATION_CODES_DIR/warpx-data}"`
  - `ENV_NAME="${CONDA_ENV_NAME:-warpx-dev}"`
- Added directory existence guards before prepending to `PATH` or `LD_LIBRARY_PATH`.
- Safely activated conda environment if not already active.
- Added environment summary logging.

## Acceptance Criteria — All Met

- [x] No personal absolute username paths hardcoded in `setup.sh`.
- [x] `bash setup.sh` executes cleanly and configures paths.
- [x] `python scripts/audit_repo.py --root .` passes all checks.
- [x] `pytest -q` — 92 passed.

## Physics Limitations

None. Shell configuration portability update.
