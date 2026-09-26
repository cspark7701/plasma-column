# Execution Plan Summary: Add Output Directory Option to Production Pipeline and Profile Launcher

**Task Index**: 83  
**Date**: 2026-09-26  
**Subject**: Add `--output_dir` / `--output-dir` option to `scripts/run_production_profile.sh`, `scripts/run_full_production.sh`, `scripts/run_scan.py`, and `scripts/run_case.py`.

---

## 1. Motivation & User Request

- **User Request**: "Is there an output directory option?" -> "Yes add the option"
- **Context**: When running multiple scans (such as `method_scan_baseline.yaml`, `pressure_scan_h2_kr.yaml`, `method_comparison.yaml`), users need to separate case outputs into specific directories (e.g., `results/method_scan/`, `results/pressure_scan/`, `results/method_comparison/`) without mixing or clobbering case runs under the default `results/` folder.

---

## 2. Changes Implemented

1. **[`scripts/run_scan.py`](file:///home/cspark/Work/projects/plasma-column/scripts/run_scan.py)**:
   - Added `--output_dir` and `--output-dir` CLI argument (default: `Path("results")`).
   - Dynamic case directory creation: `output_dir = Path(args.output_dir) / case_name`.
   - Propagates `--output_dir <case_dir>` to individual simulation runners (`plasma_column_mcc_picmi_v7.py`, etc.).
   - Passes `--case-dir <case_dir>` to `scripts/postprocess_case.py`.
   - Updated dry-run completion log to report the exact configured output directory.

2. **[`scripts/run_case.py`](file:///home/cspark/Work/projects/plasma-column/scripts/run_case.py)**:
   - Added `--output-dir` alias alongside `--output_dir`.

3. **[`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_full_production.sh)**:
   - Added `OUTPUT_DIR="$PROJECT_ROOT/results"` as default.
   - Added CLI parsing for `--output_dir <path>`, `--output-dir <path>`, `--output_dir=<path>`, and `--output-dir=<path>`.
   - Strips trailing slashes via `OUTPUT_DIR="${OUTPUT_DIR%/}"` for clean subpath construction.
   - Displayed `Output Root   : $OUTPUT_DIR` in the pipeline configuration banner.
   - Step 2: Injected `--output_dir "$OUTPUT_DIR"` into `SCAN_EXTRA_ARGS` for `scripts/run_scan.py`.
   - Steps 3 & 3b: Passed `--output_dir "$OUTPUT_DIR/seeded_H2_baseline"` and `--output_dir "$OUTPUT_DIR/seeded_Kr_baseline"` to `scripts/run_case.py`.
   - Steps 4 & 4b: Configured postprocessing paths (`$POSTPROC_H2`, `$POSTPROC_KR`) to inspect `$OUTPUT_DIR` first before falling back to `results/` or `runs/`.

4. **[`scripts/run_production_profile.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_production_profile.sh)**:
   - Added CLI parsing for `--output_dir <path>`, `--output-dir <path>`, `--output_dir=<path>`, and `--output-dir=<path>`.
   - Forwarded `--output_dir` in `EXTRA_ARGS` to `scripts/run_full_production.sh`.
   - Updated auto-resume check (`HAS_PREV_RUN`) to inspect `TARGET_CHECK_DIR="${USER_OUTPUT_DIR:-$PROJECT_ROOT/results}"` so resuming checks the user-specified output folder.
   - Updated CLI help documentation (`--help`).

---

## 3. Verification

1. **End-to-End Pipeline Dry-Run**:
   - Executed `bash scripts/run_production_profile.sh dry-run --output_dir test_results_dir/`.
   - Verified banner displayed `Output Root : test_results_dir`.
   - Verified all 8 pipeline steps executed cleanly and populated case folders under `test_results_dir/` (`vacuum_reference`, `seeded_H2_baseline`, `seeded_Kr_baseline`, `callback_*`, etc.).
   - Cleaned up `test_results_dir/` after test.
2. **CLI Documentation**:
   - Verified `--help` output for both `scripts/run_full_production.sh` and `scripts/run_production_profile.sh`.
3. **Automated Testing & CI**:
   - Ran `pytest -q`: 122 passed, 1 skipped.
   - Ran `scripts/check_github_actions.sh --fast`: All steps passed (workflow syntax, `compileall`, and pytest).
