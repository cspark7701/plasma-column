# Execution Summary: Task 08 — Fix `make_plots.py` Attribute Error & Screen Error Logging

- **Date**: 2026-08-04
- **Author**: Chong Shik Park
- **Affiliation**: Department of Accelerator Science and Center for Accelerator Research, Korea University, Sejong, 30019 Republic of Korea
- **Task Source**: User Request — Fix step 5 failure in `make_plots.py` and print error tracebacks to screen on step failures

## Summary of Accomplishments

1. **Fixed `AttributeError` in `scripts/make_plots.py`**:
   - Resolved `AttributeError: 'CrossSectionDatabase' object has no attribute 'h2_table'` in `run_cross_section_plots()`.
   - Updated `run_cross_section_plots()` to load $\text{H}_2$ and $\text{Kr}$ cross-section tables via `load_cross_section_table()`.

2. **Added Screen Error Logging to `scripts/run_full_production.sh`**:
   - Updated `run_step()` in `scripts/run_full_production.sh` to trap failure exit codes in both quiet and verbose modes.
   - On step failure, the script now displays a prominent `ERROR DETECTED IN STEP [N]` header, prints the command and log file location, and prints the error traceback (`tail -n 40 "$log_file"`) directly to the screen before exiting.

3. **Verification**:
   - Ran `python scripts/make_plots.py --all` -> Cleanly generated all publication figures, paper figures, and `plots/manifest.csv`.
   - Executed `bash scripts/run_full_production.sh --dry_run` -> Successfully executed all 8 production pipeline steps.
   - Executed `pytest -q` -> All **68 unit tests passed** in 1.36s.

4. **Deliverables Summary**:
   - [`scripts/make_plots.py`](file:///home/cspark/Work/projects/plasma_column/scripts/make_plots.py)
   - [`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/plasma_column/scripts/run_full_production.sh)
   - [`docs/exec-plans/completed/33_Task08_fix_make_plots_error_and_screen_logging.md`](file:///home/cspark/Work/projects/plasma_column/docs/exec-plans/completed/33_Task08_fix_make_plots_error_and_screen_logging.md)
