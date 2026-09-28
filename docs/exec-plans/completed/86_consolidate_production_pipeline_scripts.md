# Execution Plan Summary: Consolidate Production Pipeline Launchers and Matrix Runners

**Task Index**: 86  
**Date**: 2026-09-28  
**Subject**: Create a consolidated shell script unifying `scripts/run_full_production.sh`, `scripts/run_production_profile.sh`, and `run_all.sh` with integrated options for storage profiles (`high`, `medium`, `light`, `dry-run`) and scan matrices (`method_scan`, `pressure_scan`, `method_comparison`, `all`).

---

## 1. Motivation & User Request

- **User Request**: "Create a consolidated shell script for scripts/run_full_production.sh, scripts/run_production_profile.sh and run_all.sh. So use integrated options for (high, medium, light) and (mathod_scan, pressure_scan, method_comparison)"
- **Context**:
  Previously, executing production simulations involved managing multiple distinct scripts with overlapping responsibilities:
  1. [`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_full_production.sh): Managed the 8-step pipeline execution (audit, run_scan, baseline cases, postproc, plotting, paper figures, paper tables, dataset freezing, bunched beam & transport, audit).
  2. [`scripts/run_production_profile.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_production_profile.sh): Set storage profiles (`high`, `medium`, `light`, `dry-run`) and forwarded them to `run_full_production.sh`.
  3. [`run_all.sh`](file:///home/cspark/Work/projects/plasma-column/run_all.sh): Chained 3 individual matrix invocations with hardcoded pipeline parameters and redirection to `tee`.

  A unified, first-class launcher was required to consolidate profile selection, matrix targeting, multi-matrix batch processing, log/output isolation, and interactive selection while maintaining 100% backward compatibility.

---

## 2. Changes Implemented

1. **[`scripts/run_production.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_production.sh)**:
   - **Consolidated CLI Parser**: Seamlessly accepts positional tokens or explicit flags in any order:
     - Storage Profiles: `high`, `medium` (default), `light`, `dry-run` (or `-p`, `--profile`).
     - Scan Matrices: `method_scan` (with `mathod_scan` alias), `pressure_scan`, `method_comparison`, `all` (multi-matrix batch), or any custom `.yaml` path (or `-m`, `--matrix`).
     - Options: `--output_dir`, `--log_dir`, `--cores`, `--gpu`, `--resume`, `--fresh`, `--verbose`, `--dry_run`, `--max-steps`, `--snapshots`, etc.
   - **Multi-Matrix Batch Engine (`all`)**: Iterates through all three production matrices (`method_scan`, `pressure_scan`, `method_comparison`) sequentially:
     - Automatically routes outputs into `results/<matrix_key>/` and step logs into `logs/<matrix_key>/`.
     - Directs combined stdout/stderr for each matrix to its master log (`logs/<matrix_key>.log`) via `tee`.
     - Independently performs auto-resume inspection and executes the full 8-stage verification pipeline.
   - **Interactive Prompt**: If launched with no arguments in an interactive terminal, presents friendly numeric menus for storage profile and matrix selection.
   - **Error Handling & Log Isolation**: Dry runs write to `dry_run_step_*.log` to prevent clobbering production logs; pipeline failures immediately capture and display the last 40 lines of the step log trace.

2. **Root Entrypoint**:
   - **[`run_all.sh`](file:///home/cspark/Work/projects/plasma-column/run_all.sh)**: Updated to delegate to `./scripts/run_production.sh high all "$@"`, automatically running all 3 matrices under the high-fidelity storage profile with master logging.

3. **Backward Compatibility Wrappers**:
   - **[`scripts/run_production_profile.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_production_profile.sh)**: Streamlined to delegate to `scripts/run_production.sh "$@"`.
   - **[`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_full_production.sh)**: Streamlined to delegate to `scripts/run_production.sh "$@"`.

---

## 3. Verification

1. **CLI Help & Flag Verification**:
   - Checked `--help` across all entrypoint paths:
     - `./run_all.sh --help`
     - `scripts/run_production.sh --help`
     - `scripts/run_production_profile.sh --help`
     - `scripts/run_full_production.sh --help`
2. **Single Matrix Dry Run (with `mathod_scan` alias)**:
   - Executed `scripts/run_production.sh dry-run mathod_scan`.
   - Successfully executed all 8 pipeline steps with code 0; isolated logs saved to `logs/method_scan/dry_run_step_*.log`.
3. **Multi-Matrix Batch Dry Run (`all`)**:
   - Executed `scripts/run_production.sh dry-run all`.
   - Successfully executed all 3 matrices (24 total pipeline steps) sequentially with code 0 and captured logs in `logs/method_scan.log`, `logs/pressure_scan.log`, and `logs/method_comparison.log`.
4. **Automated CI Validation**:
   - Executed `bash scripts/check_github_actions.sh --fast`.
   - All 3 check stages passed: Workflow syntax check passed, Python compilation clean, and all 122 Pytest tests passed (1 skipped).
