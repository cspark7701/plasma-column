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
#   --workers, -w     Number of parallel CPU worker cores (default: 90% of available cores).
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
CORES=8  # Default: 8 cores
GPU="auto"  # Default: auto-detect GPU; if available make it default
MATRIX_FILE="$PROJECT_ROOT/cases/method_comparison.yaml"
LOG_DIR="$PROJECT_ROOT/logs"
CHECKPOINT_PERIOD=0
RESUME=false
RESTART_FROM=""

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
    --cores|-c|--workers|-w)
      CORES="$2"
      shift 2
      ;;
    --gpu)
      GPU="$2"
      shift 2
      ;;
    --matrix)
      MATRIX_FILE="$2"
      shift 2
      ;;
    --checkpoint_period)
      CHECKPOINT_PERIOD="$2"
      shift 2
      ;;
    --resume)
      RESUME=true
      shift
      ;;
    --restart_from)
      RESTART_FROM="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: bash scripts/run_full_production.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --dry_run                 Validate matrix & metadata without running heavy PIC steps."
      echo "  --verbose, -v             Print full execution logs to screen (default: quiet mode)."
      echo "  --cores, -c               Number of CPU worker cores / OpenMP threads (default: 8)."
      echo "  --gpu [ID|auto]           GPU device ID (e.g. 0) or 'auto' (checks GPU and makes default if available, default: auto)."
      echo "  --matrix FILE             Matrix configuration file (default: cases/method_comparison.yaml)."
      echo "  --checkpoint_period <N>   Dump full AMReX checkpoint directory every N steps (chk<step>/)."
      echo "  --resume                  Automatically detect existing checkpoints and resume interrupted scans."
      echo "  --restart_from <path>     Path to specific checkpoint directory to resume from."
      echo "  --help, -h                Display this help message."
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
# CPU Core & GPU Hardware Configuration
# ------------------------------------------------------------------------------
TARGET_CORES=${CORES:-8}
if [ "$TARGET_CORES" -lt 1 ] 2>/dev/null; then
  TARGET_CORES=8
fi

export OMP_NUM_THREADS=$TARGET_CORES
export OPENMP_NUM_THREADS=$TARGET_CORES
export MKL_NUM_THREADS=$TARGET_CORES
export NUMEXPR_NUM_THREADS=$TARGET_CORES

GPU_STATUS="None (CPU only)"
if [ "$GPU" = "auto" ]; then
  if command -v nvidia-smi &>/dev/null && nvidia-smi -L &>/dev/null; then
    export CUDA_VISIBLE_DEVICES=0
    export HIP_VISIBLE_DEVICES=0
    GPU_STATUS="GPU 0 (auto-detected via nvidia-smi)"
  elif [ -e /dev/nvidia0 ]; then
    export CUDA_VISIBLE_DEVICES=0
    export HIP_VISIBLE_DEVICES=0
    GPU_STATUS="GPU 0 (auto-detected via /dev/nvidia0)"
  fi
elif [ -n "$GPU" ] && [ "$GPU" != "none" ] && [ "$GPU" != "cpu" ] && [ "$GPU" != "false" ]; then
  export CUDA_VISIBLE_DEVICES="$GPU"
  export HIP_VISIBLE_DEVICES="$GPU"
  GPU_STATUS="GPU $GPU (user specified)"
fi

echo "======================================================================"
echo " Plasma Column Simulation - Full Production & Analysis Pipeline"
echo "======================================================================"
echo "  Project Root  : $PROJECT_ROOT"
echo "  Matrix File   : $MATRIX_FILE"
echo "  Execution Mode: $( [ "$DRY_RUN" = true ] && echo "DRY RUN" || echo "FULL PRODUCTION" )"
echo "  Verbose Output: $( [ "$VERBOSE" = true ] && echo "ON" || echo "OFF (Quiet Token-Conservation Mode)" )"
echo "  CPU Cores Used: $TARGET_CORES (default: 8)"
echo "  GPU Status    : $GPU_STATUS"
echo "  Checkpoint Int: $( [ "$CHECKPOINT_PERIOD" -gt 0 ] && echo "$CHECKPOINT_PERIOD steps (CLI override)" || echo "Per-case defaults (2k seeded/vacuum, 10k callback/MCC)" )"
echo "  Resume Mode   : $( [ "$RESUME" = true ] && echo "Auto-Resume Enabled" || ( [ -n "$RESTART_FROM" ] && echo "Restart from $RESTART_FROM" || echo "Fresh Run" ) )"
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
SCAN_EXTRA_ARGS=()
if [ "$CHECKPOINT_PERIOD" -gt 0 ]; then
  SCAN_EXTRA_ARGS+=(--checkpoint_period "$CHECKPOINT_PERIOD")
fi
if [ "$RESUME" = true ]; then
  SCAN_EXTRA_ARGS+=(--resume)
fi

if [ "$DRY_RUN" = true ]; then
  run_step "2/8" "Matrix Scan Setup & Parameter Validation (Dry Run)" \
    python3 scripts/run_scan.py --matrix "$MATRIX_FILE" --cores "$TARGET_CORES" --gpu "$GPU" --dry_run "${SCAN_EXTRA_ARGS[@]}"
else
  run_step "2/8" "Matrix Scan Setup & Parameter Validation" \
    python3 scripts/run_scan.py --matrix "$MATRIX_FILE" --cores "$TARGET_CORES" --gpu "$GPU" --run "${SCAN_EXTRA_ARGS[@]}"
fi

# ==============================================================================
# STEP 3: Individual Case Execution Verification
# ==============================================================================
# Runs baseline H2 case dry-run/execution validation to ensure single-case runner works
CASE_EXTRA_ARGS=()
if [ "$CHECKPOINT_PERIOD" -gt 0 ]; then
  CASE_EXTRA_ARGS+=(--checkpoint_period "$CHECKPOINT_PERIOD")
fi
if [ -n "$RESTART_FROM" ]; then
  CASE_EXTRA_ARGS+=(--restart_from "$RESTART_FROM")
fi

run_step "3/8" "Baseline Simulation Case Verification (cases/baseline_h2.yaml)" \
  python3 scripts/run_case.py --case cases/baseline_h2.yaml --cores "$TARGET_CORES" --gpu "$GPU" $( [ "$DRY_RUN" = true ] && echo "--dry_run" ) "${CASE_EXTRA_ARGS[@]}"

# ==============================================================================
# STEP 4: Post-Processing & Core Diagnostics Extraction
# ==============================================================================
# Evaluates particle-number metrics, volume-averaged core density, and spatial masks
POSTPROC_CASE="results/seeded_H2_baseline"
if [ ! -d "$POSTPROC_CASE" ] && [ -d "runs/seeded_H2_baseline" ]; then
  POSTPROC_CASE="runs/seeded_H2_baseline"
fi

run_step "4/8" "Postprocessing & Local Core Neutralization Diagnostics" \
  python3 scripts/postprocess_case.py --case-dir "$POSTPROC_CASE" $( [ "$DRY_RUN" = true ] && echo "--dry_run" )

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
