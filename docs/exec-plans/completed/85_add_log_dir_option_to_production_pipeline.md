# Execution Plan Summary: Add Log Directory Option to Production Pipeline and Profile Launcher

**Task Index**: 85  
**Date**: 2026-09-26  
**Subject**: Add `--log_dir` / `--log-dir` option to `scripts/run_production_profile.sh` and `scripts/run_full_production.sh`.

---

## 1. Motivation & User Request

- **User Request**: "also add setting log dir"
- **Context**: Complementing the recently added `--output_dir` option, users executing multiple matrices or batch production workflows (such as in `run_all.sh`) need the ability to redirect step execution logs to a custom directory (e.g. `--log_dir logs/method_scan/`, `--log_dir logs/pressure_scan/`) instead of accumulating or overwriting logs in the default `logs/` directory.

---

## 2. Changes Implemented

1. **[`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_full_production.sh)**:
   - Added CLI parsing for `--log_dir <path>`, `--log-dir <path>`, `--log_dir=<path>`, and `--log-dir=<path>`.
   - Path normalization via `LOG_DIR="${LOG_DIR%/}"` and directory creation via `mkdir -p "$LOG_DIR"`.
   - Displayed `Log Directory : $LOG_DIR` in the pipeline configuration header banner.
   - Updated `run_step()` completion status message to dynamically display the log path relative to project root (`${log_file#"$PROJECT_ROOT/"}`) or absolute if outside.
   - Documented `--log_dir <path>` in `--help`.

2. **[`scripts/run_production_profile.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_production_profile.sh)**:
   - Added CLI parsing for `--log_dir` and `--log-dir` (both space-separated and equals-separated).
   - Forwards `--log_dir` argument in `EXTRA_ARGS` to `run_full_production.sh`.
   - Documented `--log_dir <path>` in `--help`.

---

## 3. Verification

1. **End-to-End Dry Run**:
   - Executed `bash scripts/run_production_profile.sh dry-run --output_dir test_out/ --log_dir test_logs/`.
   - Verified header banner displayed `Output Root : test_out` and `Log Directory : test_logs`.
   - Verified that all 8 steps completed with exit code 0 and wrote logs to `test_logs/dry_run_step_*.log`.
   - Cleaned up temporary `test_out/` and `test_logs/` directories.
2. **Help Documentation Verification**:
   - Verified `--help` on both `run_full_production.sh` and `run_production_profile.sh`.
3. **Automated CI Validation**:
   - Ran `bash scripts/check_github_actions.sh --fast`: All steps passed (workflow syntax, compileall, and 122 unit tests passed).
