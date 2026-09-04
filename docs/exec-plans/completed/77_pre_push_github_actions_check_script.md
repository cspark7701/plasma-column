# Execution Plan Summary: Pre-Push GitHub Actions CI Check Script (`check_github_actions.sh`)

**Task Index**: 77  
**Date**: 2026-09-04  
**Subject**: Create a local validation script (`scripts/check_github_actions.sh`) to mirror and verify GitHub Actions CI workflow checks before pushing code to remote.

---

## 1. Overview of Work

Implemented [`scripts/check_github_actions.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/check_github_actions.sh) in the `scripts/` directory to allow developers to verify all continuous integration gates locally prior to pushing commits.

### Check Pipeline (Mirrors `.github/workflows/ci.yml`):
1. **Workflow Syntax & Schema Verification**:
   - Parses [`.github/workflows/ci.yml`](file:///home/cspark/Work/projects/plasma-column/.github/workflows/ci.yml) to ensure valid YAML structure, job keys, and step definitions.
2. **Python Bytecode Compilation**:
   - Runs `python -m compileall -q src scripts tests .` to catch syntax errors, import mismatches, and typing formatting issues.
3. **Pytest Test Suite Execution**:
   - Executes `python -m pytest -q` covering all 122 tests across physics, optics, schema, and runner modules.
4. **Simulation Case Dry-Run**:
   - Executes `python scripts/run_case.py --case cases/baseline_h2.yaml --dry_run` to test configuration loading, PICMI parameter hydration, and metadata generation.
5. **Matrix Scan Dry-Run**:
   - Executes `python scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run` across all 9 matrix simulation configurations.
6. **Repository Structure & Integrity Audit**:
   - Executes `python scripts/audit_repo.py --root .` to verify directory layout, documentation presence, and compilation status.

### CLI Options:
- `--dry_run, -n`: Displays the check stages without executing commands.
- `--fast`: Runs compilation and pytest only (bypassing case and matrix dry runs for fast iterations).
- `--verbose, -v`: Streams detailed execution output in real time.
- `--help, -h`: Displays help documentation and usage examples.

---

## 2. Verification

1. **Dry-run validation**:
   - Ran `bash scripts/check_github_actions.sh --dry_run` verifying all 6 stages are listed and skipped cleanly.
2. **Full CI validation**:
   - Ran `bash scripts/check_github_actions.sh` executing all 6 steps with a clean pass (`121 passed, 1 skipped`, all dry-runs and repo audit passing).
3. **Execution summary**:
   - All tests, YAML schema checks, and dry runs completed in ~35 seconds with return code 0.
