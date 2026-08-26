# Execution Summary: Task 09 — Connect Full Production PIC Simulation Execution

- **Date**: 2026-08-04
- **Author**: Chong Shik Park
- **Affiliation**: Department of Accelerator Science and Center for Accelerator Research, Korea University, Sejong, 30019 Republic of Korea
- **Task Source**: User Request — Connect actual production PIC simulation execution in `run_scan.py` and `run_case.py` when `--run` is specified

## Summary of Accomplishments

1. **Connected Subprocess PIC Simulation Runner in `scripts/run_case.py`**:
   - Updated [`scripts/run_case.py`](file:///home/cspark/Work/projects/plasma-column/scripts/run_case.py) to launch `plasma_column_mcc_picmi_v7.py` via `subprocess.run()` with appropriate physics flags (`--neutralization -1` for seeded, `--mcc electron_impact` for C++ MCC, `--neutralization 0.0` for vacuum reference) when `--run` (not `--dry_run`) is passed.
   - Automatically executes [`scripts/postprocess_case.py`](file:///home/cspark/Work/projects/plasma-column/scripts/postprocess_case.py) after simulation completion to extract particle numbers and core neutralization profiles.

2. **Connected Matrix Batch Execution in `scripts/run_scan.py`**:
   - Updated [`scripts/run_scan.py`](file:///home/cspark/Work/projects/plasma-column/scripts/run_scan.py) to iterate over all cases in [`cases/method_comparison.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/method_comparison.yaml) and execute the actual PIC simulations and postprocessing when `--run` is passed.

3. **Verification**:
   - `python -m compileall scripts src tests` -> All scripts compiled cleanly.
   - `bash scripts/run_full_production.sh --dry_run` -> Successfully validated dry-run pipeline execution across all 8 stages.
   - `pytest -q` -> All **68 unit tests passed** in 1.31s.

4. **Deliverables Summary**:
   - [`scripts/run_case.py`](file:///home/cspark/Work/projects/plasma-column/scripts/run_case.py)
   - [`scripts/run_scan.py`](file:///home/cspark/Work/projects/plasma-column/scripts/run_scan.py)
   - [`docs/exec-plans/completed/34_Task09_connect_full_pic_simulation_execution.md`](file:///home/cspark/Work/projects/plasma-column/docs/exec-plans/completed/34_Task09_connect_full_pic_simulation_execution.md)
