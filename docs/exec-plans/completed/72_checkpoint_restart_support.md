# Execution Plan Summary: Add Simulation Checkpoint & Resume/Restart Support

**Task Index**: 72  
**Date**: 2026-09-03  
**Subject**: Enable full AMReX checkpoint dumping, CLI restart flags, ParticleNumber continuity, and scan auto-resume.

---

## 1. Overview of Work

Implemented checkpoint and resume/restart capabilities across the WarpX/PICMI workflow:

1. **CLI Flags & Diagnostic Configuration**:
   - Added `--checkpoint_period <N>` and `--restart_from <path_or_auto>` arguments to:
     - [`scripts/plasma_column_mcc_picmi_v7.py`](file:///home/cspark/Work/projects/plasma-column/scripts/plasma_column_mcc_picmi_v7.py)
     - [`scripts/plasma_column_callback_source_picmi_v3.py`](file:///home/cspark/Work/projects/plasma-column/scripts/plasma_column_callback_source_picmi_v3.py)
     - [`scripts/run_case.py`](file:///home/cspark/Work/projects/plasma-column/scripts/run_case.py)
     - [`scripts/run_scan.py`](file:///home/cspark/Work/projects/plasma-column/scripts/run_scan.py)
   - When `--checkpoint_period > 0`, a `picmi.Checkpoint` diagnostic is registered to dump `chk<step>/` AMReX checkpoints.
   - When `--restart_from` is specified, `amr.restart = <chk_path>` is passed to pywarpx before `sim.step()`.

2. **Checkpoint Auto-Discovery**:
   - Added `find_checkpoints(case_dir)` in [`src/plasma_column/warpx_io.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/warpx_io.py) which scans `case_dir` (and subdirectories `diags/`, `checkpoints/`) for directories matching `chk*` containing `WarpXHeader`, sorting them numerically by step index.

3. **Postprocessing Continuity**:
   - Updated `postprocess_particle_number()` in runner scripts to deduplicate and sort steps.
   - Updated `load_particle_number_diagnostic()` in [`src/plasma_column/diagnostics.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/diagnostics.py) to automatically sort and drop duplicate step records if restarts appended to or resumed from earlier steps.

4. **Scan Integration (`run_scan.py`)**:
   - Added `--resume` flag to `run_scan.py`: when present, scans inspect `results/<case_name>/` and resume from the latest checkpoint (`chk*`) automatically.

---

## 2. Verification

1. **Unit Tests**:
   - Added `test_find_checkpoints()` in [`tests/test_warpx_patch_tracking.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_warpx_patch_tracking.py).
   - Added `test_schema_checkpoint_options()` in [`tests/test_schema.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_schema.py).
   - Added `test_load_particle_number_diagnostic_restart_deduplication()` in [`tests/test_diagnostics_particle_number.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_diagnostics_particle_number.py).
   - Entire test suite: 105 passed, 0 failures.

2. **Repository Audit**:
   - `python3 scripts/audit_repo.py --root .` passed cleanly with 105 passed tests.
