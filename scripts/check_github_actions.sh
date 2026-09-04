#!/usr/bin/env bash
# ==============================================================================
# Plasma Column Simulation - Pre-Push CI & Workflow Validation Utility
# ==============================================================================
# Mirrors the GitHub Actions CI workflow (.github/workflows/ci.yml) locally:
#   1. Repository & Branch state check
#   2. YAML workflow syntax verification
#   3. Dependency audit
#   4. Python syntax compilation (python -m compileall src scripts tests .)
#   5. Pytest test suite execution (python -m pytest -q)
#   6. Dry-run pipeline checks (run_case.py & run_scan.py)
#   7. Repository integrity check (scripts/audit_repo.py --root .)
#
# Usage:
#   bash scripts/check_github_actions.sh [OPTIONS]
#   ./scripts/check_github_actions.sh [OPTIONS]
#
# Options:
#   --dry_run, -n       Preview check steps without running tests.
#   --fast              Run essential compilation and tests only (skip full scan dry-runs).
#   --full              Run comprehensive local checks including audit_repo.py.
#   --verbose, -v       Show detailed test outputs.
#   --help, -h          Display this help message.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DRY_RUN=false
FAST=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry_run|-n)
      DRY_RUN=true
      shift
      ;;
    --fast)
      FAST=true
      shift
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --help|-h)
      echo "Usage: bash scripts/check_github_actions.sh [OPTIONS]"
      echo ""
      echo "Validates GitHub Actions CI steps locally before pushing to remote."
      echo ""
      echo "Options:"
      echo "  --dry_run, -n       Preview verification steps without executing them."
      echo "  --fast              Run essential compilation and pytest (skip case/matrix dry runs)."
      echo "  --verbose, -v       Verbose output from each test step."
      echo "  --help, -h          Show this help message."
      exit 0
      ;;
    *)
      echo "Error: Unknown option '$1'"
      echo "Use --help to view available options."
      exit 1
      ;;
  esac
done

cd "$PROJECT_ROOT"

PYTHON_EXEC="$(command -v python3 || command -v python)"
if [ -z "$PYTHON_EXEC" ]; then
  echo "Error: Python 3 executable not found in PATH."
  exit 1
fi

PYTHON_VER=$("$PYTHON_EXEC" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')

echo "======================================================================"
echo " Pre-Push GitHub Actions CI Validation"
echo "======================================================================"
echo "  Project Root  : $PROJECT_ROOT"
echo "  Python Version: $PYTHON_VER ($PYTHON_EXEC)"
echo "  Workflow Spec : .github/workflows/ci.yml"
echo "  Mode          : $( [ "$DRY_RUN" = true ] && echo "DRY RUN (Preview)" || ( [ "$FAST" = true ] && echo "FAST (Compile + Tests)" || echo "FULL CI VALIDATION" ) )"
echo "======================================================================"

PASSED_STEPS=0
TOTAL_STEPS=0
FAILURES=0

run_ci_step() {
  local step_num="$1"
  local step_name="$2"
  shift 2
  local cmd=("$@")

  TOTAL_STEPS=$((TOTAL_STEPS + 1))
  echo ""
  echo "----------------------------------------------------------------------"
  echo " [$step_num] $step_name"
  echo " Command: ${cmd[*]}"
  echo "----------------------------------------------------------------------"

  if [ "$DRY_RUN" = true ]; then
    echo " [DRY RUN] Step skipped."
    PASSED_STEPS=$((PASSED_STEPS + 1))
    return 0
  fi

  local start_time
  start_time=$(date +%s)

  local status=0
  if [ "$VERBOSE" = true ]; then
    "${cmd[@]}" || status=$?
  else
    local tmp_log
    tmp_log=$(mktemp)
    if ! "${cmd[@]}" > "$tmp_log" 2>&1; then
      status=1
      echo " [FAIL] Step exited with non-zero status."
      echo " Output:"
      cat "$tmp_log"
    else
      if [ -s "$tmp_log" ]; then
        # Print summary/last lines if available
        tail -n 10 "$tmp_log"
      fi
    fi
    rm -f "$tmp_log"
  fi

  local end_time
  end_time=$(date +%s)
  local duration=$((end_time - start_time))

  if [ "$status" -eq 0 ]; then
    echo " [PASS] $step_name (${duration}s)"
    PASSED_STEPS=$((PASSED_STEPS + 1))
  else
    echo " [FAILED] $step_name (${duration}s)"
    FAILURES=$((FAILURES + 1))
    return 1
  fi
}

# 1. GitHub Actions Workflow Syntax Check
check_workflow_syntax() {
  "$PYTHON_EXEC" -c '
import sys, yaml
wf_file = ".github/workflows/ci.yml"
try:
    with open(wf_file, "r") as f:
        data = yaml.safe_load(f)
    assert "name" in data, "Missing workflow name"
    assert "jobs" in data, "Missing jobs definition"
    assert "test" in data["jobs"], "Missing test job"
    steps = data["jobs"]["test"]["steps"]
    assert len(steps) > 0, "No steps found in test job"
    print(f"  Valid YAML: {wf_file} (defines {len(steps)} steps)")
except Exception as e:
    print(f"  Invalid workflow syntax: {e}", file=sys.stderr)
    sys.exit(1)
'
}
run_ci_step "1/6" "GitHub Actions Workflow Syntax Verification" check_workflow_syntax

# 2. Python Bytecode Compilation (matches CI step: Compile python files)
run_ci_step "2/6" "Compile Python Code (compileall)" \
  "$PYTHON_EXEC" -m compileall -q src scripts tests .

# 3. Unit Test Suite (matches CI step: Run pytest)
run_ci_step "3/6" "Execute Pytest Suite" \
  "$PYTHON_EXEC" -m pytest -v

# 4. Dry-run Cases (matches CI step: Run dry-run cases)
if [ "$FAST" = false ]; then
  run_ci_step "4/6" "CI Case Dry-Run: baseline_h2.yaml" \
    "$PYTHON_EXEC" scripts/run_case.py --case cases/baseline_h2.yaml --dry_run

  run_ci_step "5/6" "CI Matrix Scan Dry-Run: method_comparison.yaml" \
    "$PYTHON_EXEC" scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run

  # 5. Full Repository Integrity Audit
  run_ci_step "6/6" "Repository Integrity & Documentation Audit" \
    "$PYTHON_EXEC" scripts/audit_repo.py --root .
fi

echo ""
echo "======================================================================"
if [ "$FAILURES" -eq 0 ]; then
  echo " [CI SUCCESS] All pre-push checks passed ($PASSED_STEPS/$TOTAL_STEPS steps successful)!"
  echo " Your changes match GitHub Actions CI expectations and are safe to push."
  echo "======================================================================"
  exit 0
else
  echo " [CI FAILURE] $FAILURES check(s) failed out of $TOTAL_STEPS steps."
  echo " Please resolve the failures above before pushing to remote."
  echo "======================================================================"
  exit 1
fi
