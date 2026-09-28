# Execution Plan Summary: Consolidate Production Pipeline into Unified run_full_production.sh

**Task Index**: 86  
**Date**: 2026-09-28  
**Subject**: Consolidate production pipeline launchers into a single unified script [`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_full_production.sh) with integrated storage profiles (`high`, `medium`, `light`, `dry-run`) and scan matrices (`method_scan`, `pressure_scan`, `method_comparison`, `all`), and remove obsolete scripts (`run_all.sh` and `scripts/run_production_profile.sh`).

---

## 1. Motivation & User Request

- **User Request**:
  - "Create a consolidated shell script for scripts/run_full_production.sh, scripts/run_production_profile.sh and run_all.sh. So use integrated options for (high, medium, light) and (mathod_scan, pressure_scan, method_comparison)"
  - "With scripts/run_production.sh, I think run_all.sh, scripts/run_full_production.sh, and scripts/run_production_profile.sh are obsolete. Please remove them and rename scripts/run_production.sh to scripts/run_full_production.sh."
- **Context**:
  Previously, simulation execution was fragmented across three separate scripts:
  1. `scripts/run_full_production.sh`: Handled the 8-step production pipeline.
  2. `scripts/run_production_profile.sh`: Handled storage profiles and snapshot frequencies.
  3. `run_all.sh`: Chained execution of all 3 matrices.

  By unifying all profiles, matrices, batch execution, log isolation, output redirection, and hardware management into a single script—and retaining the established name `scripts/run_full_production.sh`—we eliminate script proliferation and simplify maintenance.

---

## 2. Changes Implemented

1. **Unified Production Script ([`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_full_production.sh))**:
   - **Integrated Storage Profiles**:
     - `high`: 80 snapshots/case (~365 GB disk footprint, for $\ge$ 1.2 TB storage).
     - `medium`: 15 snapshots/case (~69 GB disk footprint, for $\ge$ 200 GB storage) [default].
     - `light`: 0 snapshots/case ($<$ 250 MB disk footprint, time-series and figures/tables only).
     - `dry-run`: Parameter check and pipeline verification without heavy PIC execution.
   - **Integrated Scan Matrices**:
     - `method_scan` (with `mathod_scan` alias): `cases/method_scan_baseline.yaml` $\rightarrow$ `results/method_scan/`.
     - `pressure_scan`: `cases/pressure_scan_h2_kr.yaml` $\rightarrow$ `results/pressure_scan/`.
     - `method_comparison`: `cases/method_comparison.yaml` $\rightarrow$ `results/method_comparison/` [default].
     - `all`: Sequentially runs all three matrices (`method_scan` $\rightarrow$ `pressure_scan` $\rightarrow$ `method_comparison`), with separated outputs (`results/<matrix>/`), step logs (`logs/<matrix>/`), and master logs (`logs/<matrix>.log`) captured via `tee`.
     - `<path/to/custom.yaml>`: Path to any custom YAML matrix file.
   - **Flexible CLI Arguments**: Accepts options positionally or via flags:
     - `./scripts/run_full_production.sh high all`
     - `./scripts/run_full_production.sh high method_scan`
     - `./scripts/run_full_production.sh medium pressure_scan --gpu 0`
     - `./scripts/run_full_production.sh light method_comparison --cores 8`
     - `./scripts/run_full_production.sh dry-run all`
   - **CLI Flags**: `--output_dir`, `--log_dir`, `--cores`, `--gpu`, `--resume`, `--fresh`, `--dry_run`, `--verbose`, `--max_steps`, `--snapshots`, `--diag_period`, `--checkpoint_period`, `--restart_from`, `--help`.
   - **Interactive Menu**: Prompts for storage profile and matrix target when executed with no arguments in a terminal.
   - **Log Protection**: Dry runs redirect to `dry_run_step_*.log` to prevent overwriting production logs. Pipeline errors dump the last 40 lines of the traceback log directly to screen.

2. **Removed Obsolete Scripts**:
   - Removed `run_all.sh` (subsumed by `./scripts/run_full_production.sh high all` or any profile with `all`).
   - Removed `scripts/run_production_profile.sh` (subsumed by profile options in `scripts/run_full_production.sh`).
   - Removed temporary root wrapper `run_production.sh`.

---

## 3. Verification

1. **CLI Help Verification**:
   - Ran `bash scripts/run_full_production.sh --help` and verified all integrated profiles, matrices, and CLI options are documented.
2. **Dry Run Testing**:
   - Tested single matrix execution: `bash scripts/run_full_production.sh dry-run mathod_scan` (all 8 pipeline steps passed with exit code 0).
   - Tested batch execution: `bash scripts/run_full_production.sh dry-run all` (all 24 pipeline steps across the 3 matrices passed with exit code 0).
3. **Automated CI Validation**:
   - Ran `bash scripts/check_github_actions.sh --fast`:
     - GitHub Actions YAML syntax check: PASS
     - Python `compileall` check: PASS
     - Pytest test suite: 122 passed, 1 skipped (0 failures).
