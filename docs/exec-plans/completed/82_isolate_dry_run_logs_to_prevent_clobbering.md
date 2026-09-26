# Execution Plan Summary: Isolate Dry-Run Logs to Prevent Overwriting Active Production Logs

**Task Index**: 82  
**Date**: 2026-09-26  
**Subject**: Isolate dry-run log output to `logs/dry_run_step_*.log` in `scripts/run_full_production.sh` so executing dry-runs never clobbers active or past production simulation logs.

---

## 1. Problem Diagnosis & User Inquiry

- **User Inquiry**: "After running dry-run, it overrides current running logs. Do I need this log file?"
- **Analysis**:
  1. **Do simulation workflows require `logs/step_*.log`?**:
     - **No**. All scientific data, particle time-series (`particle_number.txt`), phase space dumps, checkpoints (`chk<step>/`), OpenPMD plotfiles (`diags/`), and case metadata/config are saved inside `results/<case_name>/`.
     - Downstream postprocessing (`scripts/postprocess_case.py`), plotting (`scripts/make_plots.py`, `scripts/make_paper_figures.py`), summary tables (`scripts/make_paper_tables.py`), and optics modeling read exclusively from `results/`, never from `logs/`.
  2. **Role of `logs/step_*.log`**:
     - It captures standard console `stdout` and `stderr` generated during WarpX execution for screen quietness and live monitoring (`tail -f`).
  3. **Root Cause of Log Clobbering**:
     - When `scripts/run_full_production.sh` ran with `--dry_run`, `run_step()` redirected to `logs/step_${clean_step}.log` using standard truncation (`>`), which overwrote existing logs of ongoing or past production runs.

---

## 2. Changes Implemented

1. **[`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_full_production.sh)**:
   - Updated `run_step()` to dynamically select the log filename prefix based on the execution mode:
     - Production runs: `logs/step_${clean_step}.log`
     - Dry runs (`--dry_run`): `logs/dry_run_step_${clean_step}.log`
   - Updated the step success message to report the exact log path used (`logs/${log_prefix}_${clean_step}.log`).

---

## 3. Verification

1. **Dry-Run Log Isolation Verification**:
   - Ran `bash scripts/run_full_production.sh --dry_run`.
   - Verified all dry-run steps output to `logs/dry_run_step_*.log`.
   - Verified that active production logs (`logs/step_2_8.log`, actively written by the ongoing simulation PID 499394) were untouched and continued logging without interruption.
