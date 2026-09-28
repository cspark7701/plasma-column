#!/usr/bin/env bash
# ==============================================================================
# Plasma Column Simulation - Consolidated Production & Analysis Pipeline
# ==============================================================================
# Consolidated simulation launcher combining storage profiles, scan matrix targets,
# multi-matrix batch processing, and full 8-step production pipeline verification.
#
# Profiles:
#   high               : 80 snapshots/case (~365 GB footprint, for >= 1.2 TB disks)
#   medium             : 15 snapshots/case (~69 GB footprint, for >= 200 GB disks) [default]
#   light              : 0 snapshots/case  (< 250 MB footprint, reduced diags only)
#   dry-run            : Validation only   (0 MB footprint, dry run)
#
# Matrices:
#   method_scan        : cases/method_scan_baseline.yaml -> results/method_scan/
#   pressure_scan      : cases/pressure_scan_h2_kr.yaml  -> results/pressure_scan/
#   method_comparison  : cases/method_comparison.yaml    -> results/method_comparison/
#   all                : Sequentially runs method_scan, pressure_scan, method_comparison
#   <path/to/file.yaml>: Custom YAML matrix configuration file
#
# Usage:
#   ./scripts/run_production.sh [PROFILE] [MATRIX] [OPTIONS]
#   bash scripts/run_production.sh high all
#   bash scripts/run_production.sh high method_scan
#   bash scripts/run_production.sh medium pressure_scan --gpu 0
#   bash scripts/run_production.sh light method_comparison --cores 8
#   bash scripts/run_production.sh dry-run all
#   bash scripts/run_production.sh  (interactive menu)
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default Configuration
PROFILE=""
MATRIX_TARGET=""
USER_OUTPUT_DIR=""
USER_LOG_DIR=""
CORES=8
GPU="auto"
AUTO_RESUME=true
USER_SPECIFIED_RESUME=false
DRY_RUN=false
VERBOSE=false
USE_COLOR=true
MAX_STEPS=""
SNAPSHOTS=""
DIAG_PERIOD=""
CHECKPOINT_PERIOD=""
RESTART_FROM=""

# ------------------------------------------------------------------------------
# Argument Parsing Helper
# ------------------------------------------------------------------------------
is_profile() {
  case "$1" in
    high|medium|light|ultra-light|dry-run|dry_run) return 0 ;;
    *) return 1 ;;
  esac
}

is_matrix() {
  case "$1" in
    method_scan|method-scan|mathod_scan|mathod-scan|method|methods|method_scan_baseline) return 0 ;;
    pressure_scan|pressure-scan|pressure|pressures|pressure_scan_h2_kr) return 0 ;;
    method_comparison|method-comparison|comparison|compare) return 0 ;;
    all|run_all|run-all|batch|matrices) return 0 ;;
    *.yaml|*.yml) return 0 ;;
    *) return 1 ;;
  esac
}

# Parse Arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile|-p)
      PROFILE="$2"
      shift 2
      ;;
    --matrix|-m)
      MATRIX_TARGET="$2"
      shift 2
      ;;
    --all)
      MATRIX_TARGET="all"
      shift
      ;;
    --output_dir|--output-dir)
      USER_OUTPUT_DIR="$2"
      shift 2
      ;;
    --output_dir=*|--output-dir=*)
      USER_OUTPUT_DIR="${1#*=}"
      shift
      ;;
    --log_dir|--log-dir)
      USER_LOG_DIR="$2"
      shift 2
      ;;
    --log_dir=*|--log-dir=*)
      USER_LOG_DIR="${1#*=}"
      shift
      ;;
    --cores|-c)
      CORES="$2"
      shift 2
      ;;
    --gpu)
      GPU="$2"
      shift 2
      ;;
    --resume)
      AUTO_RESUME=true
      USER_SPECIFIED_RESUME=true
      shift
      ;;
    --fresh|--no-resume)
      AUTO_RESUME=false
      USER_SPECIFIED_RESUME=true
      shift
      ;;
    --dry_run|--dry-run|-d)
      DRY_RUN=true
      shift
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --max_steps|--steps)
      MAX_STEPS="$2"
      shift 2
      ;;
    --snapshots|--plotfiles)
      SNAPSHOTS="$2"
      shift 2
      ;;
    --diag_period)
      DIAG_PERIOD="$2"
      shift 2
      ;;
    --checkpoint_period)
      CHECKPOINT_PERIOD="$2"
      shift 2
      ;;
    --restart_from)
      RESTART_FROM="$2"
      shift 2
      ;;
    --color)
      USE_COLOR=true
      shift
      ;;
    --no-color)
      USE_COLOR=false
      shift
      ;;
    --help|-h)
      echo "Usage: ./scripts/run_production.sh [PROFILE] [MATRIX] [OPTIONS]"
      echo ""
      echo "Integrated Profiles:"
      echo "  high               80 snapshots/case (~365 GB footprint, for >= 1.2 TB disks)"
      echo "  medium             15 snapshots/case (~69 GB footprint, for >= 200 GB disks) [default]"
      echo "  light              0 snapshots/case  (< 250 MB footprint, reduced diags only)"
      echo "  dry-run            Parameter validation only (0 MB footprint, dry run)"
      echo ""
      echo "Integrated Scan Matrices:"
      echo "  method_scan        cases/method_scan_baseline.yaml -> results/method_scan/"
      echo "  pressure_scan      cases/pressure_scan_h2_kr.yaml  -> results/pressure_scan/"
      echo "  method_comparison  cases/method_comparison.yaml    -> results/method_comparison/ [default]"
      echo "  all                Run all three matrix pipelines in sequential order"
      echo "  <path/to/file>     Path to custom YAML matrix configuration file"
      echo ""
      echo "Options:"
      echo "  --profile, -p <P>                  Select storage profile (high, medium, light, dry-run)."
      echo "  --matrix, -m <M>                   Select scan matrix (method_scan, pressure_scan, method_comparison, all)."
      echo "  --all                              Run all three matrix scans sequentially."
      echo "  --output_dir <path>                Override root output directory."
      echo "  --log_dir <path>                   Override directory for step execution logs."
      echo "  --cores, -c <N>                    CPU worker cores / OpenMP threads (default: 8)."
      echo "  --gpu [ID|auto]                    GPU device ID (e.g. 0) or 'auto' (default: auto)."
      echo "  --resume                           Auto-resume from existing case checkpoints."
      echo "  --fresh                            Start fresh from step 0 (disables auto-resume)."
      echo "  --dry_run, --dry-run               Dry run parameter validation without heavy PIC execution."
      echo "  --verbose, -v                      Print full subprocess logs to screen."
      echo "  --max_steps, --steps <N>           Override total simulation steps across all cases."
      echo "  --snapshots, --plotfiles <N>       Override target snapshots across the run."
      echo "  --diag_period <N>                  Diagnostic dump interval in steps."
      echo "  --checkpoint_period <N>            AMReX checkpoint dump interval (chk<step>/)."
      echo "  --restart_from <path>              Restart specifically from this checkpoint directory."
      echo "  --color / --no-color               Enable/disable colorized terminal output."
      echo "  --help, -h                         Display this help message."
      exit 0
      ;;
    *)
      if [ -z "$PROFILE" ] && is_profile "$1"; then
        PROFILE="$1"
      elif [ -z "$MATRIX_TARGET" ] && is_matrix "$1"; then
        MATRIX_TARGET="$1"
      elif [ -f "$1" ] || [[ "$1" == *.yaml ]] || [[ "$1" == *.yml ]]; then
        MATRIX_TARGET="$1"
      else
        echo "Error: Unknown argument '$1'"
        echo "Run with --help to view available options."
        exit 1
      fi
      shift
      ;;
  esac
done

# ------------------------------------------------------------------------------
# Interactive Selection Menu (when invoked without arguments in terminal)
# ------------------------------------------------------------------------------
if [ -z "$PROFILE" ] && [ -t 0 ] && [ "$DRY_RUN" = false ]; then
  echo ""
  echo "======================================================================"
  echo " Plasma Column Production Pipeline - Interactive Setup"
  echo "======================================================================"
  echo " [1] High Profile   : ~365 GB (80 snapshots/case, for >= 1.2 TB disks)"
  echo " [2] Medium Profile : ~69 GB  (15 snapshots/case, for >= 200 GB disks) [default]"
  echo " [3] Light Profile  : < 250 MB (0 plotfiles, time-series + tables only)"
  echo " [4] Dry Run        : 0 MB (Parameter validation only)"
  echo ""
  read -r -p "Select storage profile [1-4] (default: 2 - Medium): " P_CHOICE
  case "$P_CHOICE" in
    1|high|High) PROFILE="high" ;;
    3|light|Light) PROFILE="light" ;;
    4|dry-run|dry_run) PROFILE="dry-run" ;;
    2|medium|Medium|"") PROFILE="medium" ;;
    *) echo "Defaulting to 'medium'."; PROFILE="medium" ;;
  esac
fi

if [ -z "$MATRIX_TARGET" ] && [ -t 0 ] && [ "$DRY_RUN" = false ]; then
  echo ""
  echo "Select Scan Matrix Target:"
  echo " [1] Method Scan Baseline : cases/method_scan_baseline.yaml"
  echo " [2] Pressure Scan H2/Kr  : cases/pressure_scan_h2_kr.yaml"
  echo " [3] Method Comparison    : cases/method_comparison.yaml [default]"
  echo " [4] All Matrices (Batch) : Sequentially run all three matrices"
  echo ""
  read -r -p "Select scan matrix [1-4] (default: 3 - Method Comparison): " M_CHOICE
  case "$M_CHOICE" in
    1|method_scan|method) MATRIX_TARGET="method_scan" ;;
    2|pressure_scan|pressure) MATRIX_TARGET="pressure_scan" ;;
    4|all|batch) MATRIX_TARGET="all" ;;
    3|method_comparison|comparison|"") MATRIX_TARGET="method_comparison" ;;
    *) echo "Defaulting to 'method_comparison'."; MATRIX_TARGET="method_comparison" ;;
  esac
fi

# Fallback Defaults
PROFILE="${PROFILE:-medium}"
MATRIX_TARGET="${MATRIX_TARGET:-method_comparison}"

# Normalize Profile Settings
case "$PROFILE" in
  high)
    SNAPSHOTS="${SNAPSHOTS:-80}"
    CHECKPOINT_PERIOD="${CHECKPOINT_PERIOD:-0}"
    ;;
  medium)
    SNAPSHOTS="${SNAPSHOTS:-15}"
    CHECKPOINT_PERIOD="${CHECKPOINT_PERIOD:-0}"
    ;;
  light|ultra-light)
    SNAPSHOTS="${SNAPSHOTS:-0}"
    CHECKPOINT_PERIOD="${CHECKPOINT_PERIOD:-0}"
    ;;
  dry-run|dry_run)
    DRY_RUN=true
    ;;
  *)
    echo "Error: Unknown profile '$PROFILE'. Allowed: high, medium, light, dry-run."
    exit 1
    ;;
esac

# ------------------------------------------------------------------------------
# ANSI Color Codes
# ------------------------------------------------------------------------------
if [ "$USE_COLOR" = true ]; then
  C_RESET=$'\033[0m'
  C_BOLD=$'\033[1m'
  C_CYAN=$'\033[1;36m'
  C_GREEN=$'\033[1;32m'
  C_YELLOW=$'\033[1;33m'
  C_BLUE=$'\033[1;34m'
  C_MAGENTA=$'\033[1;35m'
  C_RED=$'\033[1;31m'
else
  C_RESET=""
  C_BOLD=""
  C_CYAN=""
  C_GREEN=""
  C_YELLOW=""
  C_BLUE=""
  C_MAGENTA=""
  C_RED=""
fi

# ------------------------------------------------------------------------------
# Hardware Configuration (CPU Cores & GPU)
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

# ------------------------------------------------------------------------------
# Resolve Matrix Configuration Details
# ------------------------------------------------------------------------------
resolve_matrix() {
  local target="$1"
  case "$target" in
    method_scan|method-scan|mathod_scan|mathod-scan|method|methods|method_scan_baseline)
      echo "$PROJECT_ROOT/cases/method_scan_baseline.yaml:method_scan:Method Scan Baseline"
      ;;
    pressure_scan|pressure-scan|pressure|pressures|pressure_scan_h2_kr)
      echo "$PROJECT_ROOT/cases/pressure_scan_h2_kr.yaml:pressure_scan:Pressure Scan H2/Kr"
      ;;
    method_comparison|method-comparison|comparison|compare)
      echo "$PROJECT_ROOT/cases/method_comparison.yaml:method_comparison:Method Comparison"
      ;;
    *)
      if [ -f "$target" ]; then
        local base_name
        base_name="$(basename "$target" | sed 's/\.[^.]*$//')"
        echo "$(cd "$(dirname "$target")" && pwd)/$(basename "$target"):${base_name}:${base_name}"
      elif [ -f "$PROJECT_ROOT/$target" ]; then
        local base_name
        base_name="$(basename "$target" | sed 's/\.[^.]*$//')"
        echo "$PROJECT_ROOT/$target:${base_name}:${base_name}"
      elif [ -f "$PROJECT_ROOT/cases/$target" ]; then
        local base_name
        base_name="$(basename "$target" | sed 's/\.[^.]*$//')"
        echo "$PROJECT_ROOT/cases/$target:${base_name}:${base_name}"
      else
        echo "ERROR"
      fi
      ;;
  esac
}

# ------------------------------------------------------------------------------
# Core Pipeline Execution Function
# ------------------------------------------------------------------------------
run_matrix_pipeline() {
  local matrix_file="$1"
  local matrix_key="$2"
  local matrix_label="$3"

  # Directory configuration
  local out_dir
  if [ -n "$USER_OUTPUT_DIR" ]; then
    if [ "$MATRIX_TARGET" = "all" ]; then
      out_dir="${USER_OUTPUT_DIR%/}/$matrix_key"
    else
      out_dir="${USER_OUTPUT_DIR%/}"
    fi
  else
    out_dir="$PROJECT_ROOT/results/$matrix_key"
  fi

  local log_dir
  if [ -n "$USER_LOG_DIR" ]; then
    if [ "$MATRIX_TARGET" = "all" ]; then
      log_dir="${USER_LOG_DIR%/}/$matrix_key"
    else
      log_dir="${USER_LOG_DIR%/}"
    fi
  else
    log_dir="$PROJECT_ROOT/logs/$matrix_key"
  fi

  cd "$PROJECT_ROOT"
  mkdir -p "$out_dir" "$log_dir"

  # Auto-resume detection for this matrix output directory
  local resume_active=false
  local resume_mode_str="Fresh Run"
  if [ "$DRY_RUN" = false ] && [ "$AUTO_RESUME" = true ]; then
    if [ -n "$(find "$out_dir" -maxdepth 3 \( -name "particle_number.txt" -o -name "ParticleNumber_red.txt" -o -name "chk*" \) 2>/dev/null)" ]; then
      resume_active=true
      resume_mode_str="Auto-Resume (Existing Run Detected)"
    elif [ "$USER_SPECIFIED_RESUME" = true ]; then
      resume_active=true
      resume_mode_str="Resume (User Requested)"
    fi
  fi
  if [ "$AUTO_RESUME" = false ]; then
    resume_mode_str="Fresh Run (Auto-Resume Disabled)"
  fi

  # Header Banner
  echo ""
  echo "${C_CYAN}${C_BOLD}======================================================================${C_RESET}"
  echo "${C_CYAN}${C_BOLD} Plasma Column Production Pipeline: ${matrix_label}${C_RESET}"
  echo "${C_CYAN}${C_BOLD}======================================================================${C_RESET}"
  echo "  Project Root  : $PROJECT_ROOT"
  echo "  Matrix Target : $matrix_label ($matrix_key)"
  echo "  Matrix File   : $matrix_file"
  echo "  Profile       : $(echo "$PROFILE" | tr '[:lower:]' '[:upper:]')"
  echo "  Output Root   : $out_dir"
  echo "  Log Directory : $log_dir"
  echo "  Master Log    : ${log_dir%/}.log"
  echo "  Execution Mode: $( [ "$DRY_RUN" = true ] && echo "DRY RUN (Validation Only)" || echo "FULL PRODUCTION" )"
  echo "  Verbose Output: $( [ "$VERBOSE" = true ] && echo "ON" || echo "OFF (Quiet Step Logs)" )"
  echo "  CPU Cores Used: $TARGET_CORES"
  echo "  GPU Status    : $GPU_STATUS"
  echo "  Total Steps   : $( [ -n "$MAX_STEPS" ] && echo "$MAX_STEPS steps (CLI override)" || echo "Per-case defaults" )"
  echo "  Plotfile Diags: $( [ -n "$SNAPSHOTS" ] && echo "$SNAPSHOTS target snapshots" || ( [ -n "$DIAG_PERIOD" ] && echo "Every $DIAG_PERIOD steps" || echo "Per-case defaults" ) )"
  echo "  Checkpoint Int: $( [ "${CHECKPOINT_PERIOD:-0}" -gt 0 ] && echo "$CHECKPOINT_PERIOD steps" || echo "Disabled (0)" )"
  echo "  Resume Mode   : $resume_mode_str"
  echo "${C_CYAN}${C_BOLD}======================================================================${C_RESET}"

  # Step execution helper
  run_step() {
    local step_num="$1"
    local title="$2"
    shift 2

    local clean_step=$(echo "$step_num" | tr '/ ' '__')
    local log_prefix="step"
    if [ "$DRY_RUN" = true ]; then
      log_prefix="dry_run_step"
    fi
    local step_log="$log_dir/${log_prefix}_${clean_step}.log"

    echo ""
    echo "${C_CYAN}${C_BOLD}======================================================================${C_RESET}"
    echo "${C_CYAN}${C_BOLD} >>> STEP [${step_num}] : ${title}${C_RESET}"
    echo "${C_CYAN}${C_BOLD}======================================================================${C_RESET}"
    echo "    ${C_BLUE}${C_BOLD}Command:${C_RESET} $*"
    echo "    ${C_YELLOW}${C_BOLD}[RUNNING]${C_RESET} Executing step $step_num: $title..."

    if [ "$VERBOSE" = true ]; then
      if ! "$@" 2>&1 | tee "$step_log"; then
        echo ""
        echo "${C_RED}${C_BOLD}======================================================================${C_RESET}"
        echo "${C_RED}${C_BOLD} ERROR DETECTED IN STEP $step_num: $title${C_RESET}"
        echo "${C_RED}${C_BOLD}======================================================================${C_RESET}"
        echo " ${C_RED}Command:${C_RESET} $*"
        echo " ${C_RED}Detailed Log File:${C_RESET} $step_log"
        echo "${C_RED}======================================================================${C_RESET}"
        exit 1
      fi
    else
      if ! "$@" > "$step_log" 2>&1; then
        echo ""
        echo "${C_RED}${C_BOLD}======================================================================${C_RESET}"
        echo "${C_RED}${C_BOLD} ERROR DETECTED IN STEP $step_num: $title${C_RESET}"
        echo "${C_RED}${C_BOLD}======================================================================${C_RESET}"
        echo " ${C_RED}Command:${C_RESET} $*"
        echo " ${C_RED}Log File:${C_RESET} $step_log"
        echo "${C_RED}----------------------------------------------------------------------${C_RESET}"
        echo " Error Traceback Output (Tail of $step_log):"
        echo "${C_RED}----------------------------------------------------------------------${C_RESET}"
        tail -n 40 "$step_log"
        echo "${C_RED}${C_BOLD}======================================================================${C_RESET}"
        exit 1
      fi
    fi

    local display_log="$step_log"
    if [[ "$display_log" == "$PROJECT_ROOT/"* ]]; then
      display_log="${display_log#"$PROJECT_ROOT/"}"
    fi
    echo "    ${C_GREEN}${C_BOLD}[SUCCESS]${C_RESET} Finished step $step_num (Log: $display_log)"
  }

  # Build extra arguments for run_scan.py and run_case.py
  local scan_args=(--output_dir "$out_dir")
  local case_args=()

  if [ -n "$MAX_STEPS" ]; then
    scan_args+=(--max_steps "$MAX_STEPS")
    case_args+=(--max_steps "$MAX_STEPS")
  fi
  if [ -n "$SNAPSHOTS" ]; then
    scan_args+=(--snapshots "$SNAPSHOTS")
    case_args+=(--snapshots "$SNAPSHOTS")
  fi
  if [ -n "$DIAG_PERIOD" ]; then
    scan_args+=(--diag_period "$DIAG_PERIOD")
    case_args+=(--diag_period "$DIAG_PERIOD")
  fi
  if [ -n "$CHECKPOINT_PERIOD" ] && [ "$CHECKPOINT_PERIOD" -gt 0 ]; then
    scan_args+=(--checkpoint_period "$CHECKPOINT_PERIOD")
    case_args+=(--checkpoint_period "$CHECKPOINT_PERIOD")
  fi
  if [ "$resume_active" = true ]; then
    scan_args+=(--resume)
    case_args+=(--resume)
  fi
  if [ -n "$RESTART_FROM" ]; then
    case_args+=(--restart_from "$RESTART_FROM")
  fi

  # STEP 1: Environment Audit & Repository Validation
  run_step "1/8" "Environment Audit & Repository Validation" \
    python3 scripts/print_environment.py

  # STEP 2: Matrix Scan Execution / Validation
  if [ "$DRY_RUN" = true ]; then
    run_step "2/8" "Matrix Scan Setup & Parameter Validation (Dry Run)" \
      python3 scripts/run_scan.py --matrix "$matrix_file" --cores "$TARGET_CORES" --gpu "$GPU" --dry_run "${scan_args[@]}"
  else
    run_step "2/8" "Matrix Scan Execution (${matrix_label})" \
      python3 scripts/run_scan.py --matrix "$matrix_file" --cores "$TARGET_CORES" --gpu "$GPU" --run "${scan_args[@]}"
  fi

  # STEP 3: Baseline Single-Case Verification (H2 & Kr)
  run_step "3/8" "Baseline Simulation Case Verification (H2: cases/baseline_h2.yaml)" \
    python3 scripts/run_case.py --case cases/baseline_h2.yaml --output_dir "$out_dir/seeded_H2_baseline" --cores "$TARGET_CORES" --gpu "$GPU" $( [ "$DRY_RUN" = true ] && echo "--dry_run" ) "${case_args[@]}"

  run_step "3b/8" "Baseline Simulation Case Verification (Kr: cases/baseline_kr.yaml)" \
    python3 scripts/run_case.py --case cases/baseline_kr.yaml --output_dir "$out_dir/seeded_Kr_baseline" --cores "$TARGET_CORES" --gpu "$GPU" $( [ "$DRY_RUN" = true ] && echo "--dry_run" ) "${case_args[@]}"

  # STEP 4: Postprocessing & Core Diagnostics Extraction
  local postproc_h2="$out_dir/seeded_H2_baseline"
  if [ ! -d "$postproc_h2" ] && [ -d "results/seeded_H2_baseline" ]; then
    postproc_h2="results/seeded_H2_baseline"
  elif [ ! -d "$postproc_h2" ] && [ -d "runs/seeded_H2_baseline" ]; then
    postproc_h2="runs/seeded_H2_baseline"
  fi

  local postproc_kr="$out_dir/seeded_Kr_baseline"
  if [ ! -d "$postproc_kr" ] && [ -d "results/seeded_Kr_baseline" ]; then
    postproc_kr="results/seeded_Kr_baseline"
  elif [ ! -d "$postproc_kr" ] && [ -d "runs/seeded_Kr_baseline" ]; then
    postproc_kr="runs/seeded_Kr_baseline"
  fi
  if [ ! -d "$postproc_kr" ] && [ -d "$out_dir/seeded_Kr_1e-6Torr" ]; then
    postproc_kr="$out_dir/seeded_Kr_1e-6Torr"
  elif [ ! -d "$postproc_kr" ] && [ -d "results/seeded_Kr_1e-6Torr" ]; then
    postproc_kr="results/seeded_Kr_1e-6Torr"
  fi

  run_step "4/8" "Postprocessing & Local Core Neutralization Diagnostics (H2 Baseline)" \
    python3 scripts/postprocess_case.py --case-dir "$postproc_h2" $( [ "$DRY_RUN" = true ] && echo "--dry_run" )

  run_step "4b/8" "Postprocessing & Local Core Neutralization Diagnostics (Kr Baseline)" \
    python3 scripts/postprocess_case.py --case-dir "$postproc_kr" $( [ "$DRY_RUN" = true ] && echo "--dry_run" )

  # STEP 5: Publication Plotting & Cross-Section Figures
  run_step "5/8" "Generating Publication Figures & Cross-Section Plots" \
    python3 scripts/make_plots.py

  run_step "5b/8" "Generating Dedicated Paper Figures (paper/figures/)" \
    python3 scripts/make_paper_figures.py

  # STEP 6: Paper Summary Tables & Dataset Freezing
  run_step "6/8" "Generating Paper Summary Tables (paper/tables/)" \
    python3 scripts/make_paper_tables.py

  run_step "6b/8" "Freezing Publication Dataset Manifest (paper/data/)" \
    python3 scripts/freeze_publication_dataset.py

  # STEP 7: RF-Bunched Beam & Downstream Optics Transport
  run_step "7/8" "Analyzing RF-Bunched Beam Perveance & Peak Space Charge" \
    python3 scripts/analyze_bunched_beam_neutralization.py

  run_step "7b/8" "Simulating Transverse Beam Transport to Spiral Inflector" \
    python3 scripts/transport_to_inflector.py

  # STEP 8: Final Repository Integrity Audit
  run_step "8/8" "Repository Audit & Integrity Verification" \
    python3 scripts/audit_repo.py --root .

  echo ""
  echo "${C_GREEN}${C_BOLD}======================================================================${C_RESET}"
  echo "${C_GREEN}${C_BOLD} [SUCCESS] Matrix Production Completed: ${matrix_label}${C_RESET}"
  echo "  Outputs : $out_dir"
  echo "  Logs    : $log_dir"
  echo "${C_GREEN}${C_BOLD}======================================================================${C_RESET}"
}

# ------------------------------------------------------------------------------
# Dispatch Execution
# ------------------------------------------------------------------------------
cd "$PROJECT_ROOT"

if [ "$MATRIX_TARGET" = "all" ]; then
  echo ""
  echo "${C_MAGENTA}${C_BOLD}======================================================================${C_RESET}"
  echo "${C_MAGENTA}${C_BOLD} Starting Multi-Matrix Batch Production Pipeline${C_RESET}"
  echo "  Profile  : $(echo "$PROFILE" | tr '[:lower:]' '[:upper:]')"
  echo "  Matrices : 1. Method Scan  2. Pressure Scan  3. Method Comparison"
  echo "${C_MAGENTA}${C_BOLD}======================================================================${C_RESET}"

  ALL_MATRICES=("method_scan" "pressure_scan" "method_comparison")
  for m in "${ALL_MATRICES[@]}"; do
    res="$(resolve_matrix "$m")"
    IFS=":" read -r m_file m_key m_label <<< "$res"
    mkdir -p "$PROJECT_ROOT/logs"
    master_log="$PROJECT_ROOT/logs/${m_key}.log"
    if [ -n "$USER_LOG_DIR" ]; then
      mkdir -p "${USER_LOG_DIR%/}"
      master_log="${USER_LOG_DIR%/}/${m_key}.log"
    fi

    # Run matrix pipeline and tee to its dedicated master log
    run_matrix_pipeline "$m_file" "$m_key" "$m_label" 2>&1 | tee "$master_log"
  done

  echo ""
  echo "${C_GREEN}${C_BOLD}======================================================================${C_RESET}"
  echo "${C_GREEN}${C_BOLD} [BATCH SUCCESS] All 3 Matrix Production Pipelines Completed!${C_RESET}"
  echo "  1. Method Scan Baseline : ${USER_OUTPUT_DIR:-results}/method_scan"
  echo "  2. Pressure Scan H2/Kr  : ${USER_OUTPUT_DIR:-results}/pressure_scan"
  echo "  3. Method Comparison    : ${USER_OUTPUT_DIR:-results}/method_comparison"
  echo "${C_GREEN}${C_BOLD}======================================================================${C_RESET}"

else
  res="$(resolve_matrix "$MATRIX_TARGET")"
  if [ "$res" = "ERROR" ]; then
    echo "Error: Matrix file or target '$MATRIX_TARGET' not found."
    echo "Available named matrices: method_scan, pressure_scan, method_comparison, all"
    exit 1
  fi

  IFS=":" read -r m_file m_key m_label <<< "$res"
  mkdir -p "$PROJECT_ROOT/logs"
  master_log="$PROJECT_ROOT/logs/${m_key}.log"
  if [ -n "$USER_LOG_DIR" ]; then
    mkdir -p "${USER_LOG_DIR%/}"
    master_log="${USER_LOG_DIR%/}/${m_key}.log"
  fi

  # Run matrix pipeline and tee to its master log
  run_matrix_pipeline "$m_file" "$m_key" "$m_label" 2>&1 | tee "$master_log"
fi
