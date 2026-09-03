# Execution Plan Summary: Add Checkpoint and Resume to Full Production Script

**Task Index**: 73  
**Date**: 2026-09-03  
**Subject**: Integrate `--checkpoint_period`, `--resume`, and `--restart_from` options into `run_full_production.sh` and production pipeline documentation.

---

## 1. Overview of Work

1. **Production Pipeline Script Updates**:
   In [`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_full_production.sh) (and its wrapper [`run_full_production.sh`](file:///home/cspark/Work/projects/plasma-column/run_full_production.sh)):
   - Added CLI arguments:
     - `--checkpoint_period <N>`: Dumps AMReX checkpoint directory (`chk<step>/`) every $N$ steps.
     - `--resume`: Enables auto-detection of existing checkpoints in `results/<case_name>/` to resume interrupted matrix scans.
     - `--restart_from <path>`: Specifies a specific checkpoint directory to resume from.
   - Updated startup banner to report Checkpoint Interval and Resume Mode.
   - Propagated `--checkpoint_period` and `--resume` to Step 2 (`run_scan.py`).
   - Propagated `--checkpoint_period` and `--restart_from` to Step 3 (`run_case.py`).
   - Updated Step 4 postprocessing directory resolution to check `results/` before fallback.

2. **Documentation**:
   - Updated [`docs/full_production_pipeline.md`](file:///home/cspark/Work/projects/plasma-column/docs/full_production_pipeline.md) with usage instructions for checkpoint and resume options.

---

## 2. Verification

- Executed `./run_full_production.sh --dry_run --checkpoint_period 500 --resume`.
- All 8 production pipeline steps completed cleanly with status `[SUCCESS]`.
- All 105 unit tests passed.
