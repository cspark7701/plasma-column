# Execution Plan Summary: Output Folders Cleanup Script (`cleanup.sh`)

**Task Index**: 76  
**Date**: 2026-09-04  
**Subject**: Create a robust, safe workspace cleanup shell script (`scripts/cleanup.sh`) for managing simulation outputs, logs, plotfiles, and build artifacts.

---

## 1. Overview of Work

Implemented [`scripts/cleanup.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/cleanup.sh) to provide a standardized utility for cleaning temporary and generated outputs across simulation runs.

### Key Capabilities & Features:
1. **Target Selection Flags**:
   - `--all, -a`: Cleans all generated artifacts (`runs/`, `results/`, `logs/`, `data/`, unversioned `plots/`, unversioned `paper/figures/`, `paper/data/`, `__pycache__`, `.pytest_cache`).
   - `--runs`: Cleans simulation case runs and results (`runs/*`, `results/*`, root `inputs_*`, `Backtrace*`).
   - `--logs`: Cleans runtime logs (`logs/*`, root `*.log`).
   - `--data`: Cleans generated dataset summaries (`data/*`, `paper/data/*`).
   - `--plots`: Cleans unversioned plots and figures while preserving git-tracked templates and baseline documentation plots.
   - `--checkpoints`: Selectively purges large AMReX checkpoint dumps (`chk*/`) across the workspace without deleting final CSV metrics or metadata.
   - `--cache`: Cleans Python bytecode caches (`__pycache__`, `*.pyc`), pytest caches (`.pytest_cache`), and build artifacts (`*.egg-info`).

2. **Safety & Non-Destructive Operation**:
   - **Interactive confirmation prompt**: Prompts `[y/N]` before performing active deletions (can be bypassed with `--force` or `-f`).
   - **Dry Run Support (`--dry_run`, `-n`)**: Previews every target file and directory that would be removed without making modifications.
   - **Preservation of Tracked Assets**: Uses `git ls-files` to protect tracked figure templates and manifests.
   - **Directory Structure Re-Creation**: Ensures key directory stubs (`runs`, `results`, `logs`, `data`, `plots`, `paper/figures`, `paper/data`) exist after cleanup so pipeline scripts execute smoothly without missing-directory errors.

---

## 2. Verification

1. **Help Output**:
   - Executed `bash scripts/cleanup.sh --help` confirming argument parsing and option explanations.
2. **Dry Run Testing**:
   - Executed `bash scripts/cleanup.sh --dry_run` confirming correct detection of generated figures, data files, logs, and caches.
   - Executed `bash scripts/cleanup.sh --dry_run --runs` and `bash scripts/cleanup.sh --dry_run --plots` validating selective target filtering.
3. **Repository Integrity**:
   - Tested pytest test suite and `audit_repo.py` verifying full pass without errors or warnings.
