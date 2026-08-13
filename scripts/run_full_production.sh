#!/usr/bin/env bash
# ==============================================================================
# Plasma Column Neutralizer Simulation - Full Production & Analysis Pipeline
# ==============================================================================
# This shell script executes the complete production workflow for the plasma-assisted
# space-charge neutralizer study:
#   1. System & environment audit
#   2. Matrix scan configuration & PIC simulation execution
#   3. Postprocessing & local core diagnostic extraction
#   4. Publication plotting, paper figures, & paper summary tables
#   5. Dataset freezing & downstream transport optics modeling
#
# Parallel Execution: Automatically detects system CPU cores and uses ~90% of cores.
# Token Conservation: Default quiet mode redirects detailed step logs to logs/
#                    to avoid context token exhaustion during AI/CLI execution.
#
# Usage:
#   bash scripts/run_full_production.sh [OPTIONS]
#
# Options:
#   --dry_run         Validate case matrices & metadata without running heavy PIC steps.
#   --verbose, -v     Print detailed execution logs directly to screen (default: quiet mode).
#   -w, --workers W   Number of parallel CPU worker cores (default: 90% of available cores).
#   --matrix FILE     Path to matrix YAML configuration (default: cases/method_comparison.yaml).
#   --help, -h        Show this help message.
# ==============================================================================

set -e

# Script directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default settings
DRY_RUN=false
VERBOSE=false
WORKERS=0  # 0 means "auto" (90% of available cores)
MATRIX_FILE="$PROJECT_ROOT/cases/method_comparison.yaml"
LOG_DIR="$PROJECT_ROOT/logs"

# Parse CLI options
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry_run)
      DRY_RUN=true
      shift
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    -w|--workers)
      WORKERS="$2"
      shift 2
      ;;
    --matrix)
      MATRIX_FILE="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: bash scripts/run_full_production.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --dry_run        Validate matrix & metadata without running heavy PIC steps."
      echo "  --verbose, -v    Print full execution logs to screen (default: quiet mode)."
      echo "  -w, --workers W  Number of parallel CPU worker cores (default: 90% of available cores)."
      echo "  --matrix FILE    Matrix configuration file (default: cases/method_comparison.yaml)."
      echo "  --help, -h       Display this help message."
      exit 0
      ;;
    *)
      echo "Error: Unknown option $1"
      echo "Use --help to view available options."
      exit 1
      ;;
  esac
done

cd "$PROJECT_ROOT"
mkdir -p "$LOG_DIR"

# ------------------------------------------------------------------------------
# Parallel Core Calculation
# ------------------------------------------------------------------------------
TOTAL_CORES=$(nproc 2>/dev/null || python3 -c "import os; print(os.cpu_count() or 1)")
if [ "$WORKERS" -gt 0 ] 2>/dev/null; then
  TARGET_CORES=$WORKERS
else
  TARGET_CORES=$(( TOTAL_CORES * 90 / 100 ))
fi
if [ "$TARGET_CORES" -lt 1 ]; then
  TARGET_CORES=1
fi

export OMP_NUM_THREADS=$TARGET_CORES
export OPENMP_NUM_THREADS=$TARGET_CORES
export MKL_NUM_THREADS=$TARGET_CORES
export NUMEXPR_NUM_THREADS=$TARGET_CORES

echo "======================================================================"
echo " Plasma Column Simulation - Full Production & Analysis Pipeline"
echo "======================================================================"
echo "  Project Root  : $PROJECT_ROOT"
echo "  Matrix File   : $MATRIX_FILE"
echo "  Execution Mode: $( [ "$DRY_RUN" = true ] && echo "DRY RUN" || echo "FULL PRODUCTION" )"
echo "  Verbose Output: $( [ "$VERBOSE" = true ] && echo "ON" || echo "OFF (Quiet Token-Conservation Mode)" )"
echo "  CPU Cores Used: $TARGET_CORES / $TOTAL_CORES"
echo "  Log File Path : $LOG_DIR/full_production.log"
echo "======================================================================"

# Helper function to run commands with quiet/verbose option logging
run_step() {
  local step_num="$1"
  local title="$2"
  shift 2

  local clean_step=$(echo "$step_num" | tr '/ ' '__')
  local log_file="$LOG_DIR/step_${clean_step}.log"

  echo ""
  echo "[$step_num] $title"
  echo "    Command: $*"
  echo "    [RUNNING] Executing step $step_num: $title..."

  if [ "$VERBOSE" = true ]; then
    if ! "$@" 2>&1 | tee "$log_file"; then
      echo ""
      echo "======================================================================"
      echo " ERROR DETECTED IN STEP $step_num: $title"
      echo "======================================================================"
      echo " Command: $*"
      echo " Detailed Log File: $log_file"
      echo "======================================================================"
      exit 1
    fi
  else
    if ! "$@" > "$log_file" 2>&1; then
      echo ""
      echo "======================================================================"
      echo " ERROR DETECTED IN STEP $step_num: $title"
      echo "======================================================================"
      echo " Command: $*"
      echo " Log File: $log_file"
      echo "----------------------------------------------------------------------"
      echo " Error Traceback Output (Tail of $log_file):"
      echo "----------------------------------------------------------------------"
      tail -n 40 "$log_file"
      echo "======================================================================"
      exit 1
    fi
  fi
  echo "    [SUCCESS] Finished step $step_num (Log: logs/step_${clean_step}.log)"
}

# ==============================================================================
# STEP 1: Environment & Repository Audit
# ==============================================================================
# Audits python packages, pywarpx import status, git commit hash, and WarpX patch diff
run_step "1/8" "Environment Audit & Repository Validation" \
  python3 scripts/print_environment.py

# ==============================================================================
# STEP 2: Simulation Case & Matrix Setup
# ==============================================================================
# Validates case configs, creates case directories in runs/, and logs metadata.json
if [ "$DRY_RUN" = true ]; then
  run_step "2/8" "Matrix Scan Setup & Parameter Validation (Dry Run)" \
    python3 scripts/run_scan.py --matrix "$MATRIX_FILE" --dry_run
else
  run_step "2/8" "Matrix Scan Setup & Parameter Validation" \
    python3 scripts/run_scan.py --matrix "$MATRIX_FILE" --run
fi

# ==============================================================================
# STEP 3: Individual Case Execution Verification
# ==============================================================================
# Runs baseline H2 case dry-run/execution validation to ensure single-case runner works
run_step "3/8" "Baseline Simulation Case Verification (cases/baseline_h2.yaml)" \
  python3 scripts/run_case.py --case cases/baseline_h2.yaml $( [ "$DRY_RUN" = true ] && echo "--dry_run" )

# ==============================================================================
# STEP 4: Post-Processing & Core Diagnostics Extraction
# ==============================================================================
# Evaluates particle-number metrics, volume-averaged core density, and spatial masks
run_step "4/8" "Postprocessing & Local Core Neutralization Diagnostics" \
  python3 scripts/postprocess_case.py --case-dir runs/seeded_H2_baseline $( [ "$DRY_RUN" = true ] && echo "--dry_run" )

# ==============================================================================
# STEP 5: Publication Plotting & Cross-Section Figures
# ==============================================================================
# Generates publication-ready figures (H2 vs Kr cross sections, buildup curves, Keff/K0)
run_step "5/8" "Generating Publication Figures & Cross-Section Plots" \
  python3 scripts/make_plots.py

run_step "5b/8" "Generating Dedicated Paper Figures (paper/figures/)" \
  python3 scripts/make_paper_figures.py

# ==============================================================================
# STEP 6: Paper Summary Tables & Dataset Freezing
# ==============================================================================
# Generates CSV tables (beam/gas parameters, validation summary) and freezes dataset
run_step "6/8" "Generating Paper Summary Tables (paper/tables/)" \
  python3 scripts/make_paper_tables.py

run_step "6b/8" "Freezing Publication Dataset Manifest (paper/data/)" \
  python3 scripts/freeze_publication_dataset.py

# ==============================================================================
# STEP 7: RF-Bunched Beam & Downstream Optics Transport
# ==============================================================================
# Models RF-bunched peak perveance reduction and beam transport through solenoid & inflector
run_step "7/8" "Analyzing RF-Bunched Beam Perveance & Peak Space Charge" \
  python3 scripts/analyze_bunched_beam_neutralization.py

run_step "7b/8" "Simulating Transverse Beam Transport to Spiral Inflector" \
  python3 scripts/transport_to_inflector.py

# ==============================================================================
# STEP 8: Final Repository Integrity Audit
# ==============================================================================
# Ensures all project structure, documentation, compilation, and tests pass cleanly
run_step "8/8" "Repository Audit & Integrity Verification" \
  python3 scripts/audit_repo.py --root .

echo ""
echo "======================================================================"
echo " [SUCCESS] Full Production Simulation & Analysis Pipeline Completed!"
echo "======================================================================"
