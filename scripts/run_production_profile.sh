#!/usr/bin/env bash
# ==============================================================================
# Plasma Column Production Launcher — Preset Storage Profiles
# ==============================================================================
# Convenient profile wrapper for scripts/run_full_production.sh:
#
#   1. high    : ~365 GB disk usage (80 snapshots/case, ideal for >= 1.2 TB storage)
#   2. medium  : ~69 GB disk usage  (15 snapshots/case, ideal for >= 200 GB storage)
#   3. light   : < 250 MB disk usage (0 3D snapshots, time-series + figures/tables only)
#
# Usage:
#   bash scripts/run_production_profile.sh [high|medium|light|dry-run] [EXTRA_ARGS]
#   bash scripts/run_production_profile.sh --profile medium --cores 8 --gpu auto
#   bash scripts/run_production_profile.sh  (interactive menu)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ANSI Color Codes
C_RESET=$'\033[0m'
C_BOLD=$'\033[1m'
C_CYAN=$'\033[1;36m'
C_GREEN=$'\033[1;32m'
C_YELLOW=$'\033[1;33m'
C_BLUE=$'\033[1;34m'

PROFILE=""
AUTO_RESUME=true
USER_SPECIFIED_RESUME=false
USER_OUTPUT_DIR=""
EXTRA_ARGS=()

# Parse first positional argument or flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    high|medium|light|ultra-light|dry-run)
      PROFILE="$1"
      shift
      ;;
    --profile|-p)
      PROFILE="$2"
      shift 2
      ;;
    --output_dir|--output-dir)
      USER_OUTPUT_DIR="$2"
      EXTRA_ARGS+=("$1" "$2")
      shift 2
      ;;
    --output_dir=*|--output-dir=*)
      USER_OUTPUT_DIR="${1#*=}"
      EXTRA_ARGS+=("$1")
      shift
      ;;
    --log_dir|--log-dir)
      EXTRA_ARGS+=("$1" "$2")
      shift 2
      ;;
    --log_dir=*|--log-dir=*)
      EXTRA_ARGS+=("$1")
      shift
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
    --help|-h)
      echo "Usage: bash scripts/run_production_profile.sh [PROFILE] [OPTIONS]"
      echo ""
      echo "Profiles:"
      echo "  high        80 snapshots/case (~365 GB footprint, for >= 1.2 TB disks)"
      echo "  medium      15 snapshots/case (~69 GB footprint, for >= 200 GB disks)"
      echo "  light       0 snapshots/case  (< 250 MB footprint, reduced diags only)"
      echo "  dry-run     Validation only   (0 MB footprint, dry run)"
      echo ""
      echo "Options:"
      echo "  --output_dir <path> Root directory to store case outputs (default: results/)."
      echo "  --log_dir <path>    Directory to store step execution logs (default: logs/)."
      echo "  --resume          Force resume from previous run output/checkpoints."
      echo "  --fresh           Start fresh from step 0 (disables auto-resume)."
      echo ""
      echo "Any additional options (e.g. --cores 8, --gpu auto, --matrix <file>, --verbose)"
      echo "are forwarded directly to scripts/run_full_production.sh."
      exit 0
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

USER_OUTPUT_DIR="${USER_OUTPUT_DIR%/}"

# If no profile provided via CLI, prompt interactively
if [ -z "$PROFILE" ]; then
  echo "${C_CYAN}${C_BOLD}======================================================================${C_RESET}"
  echo "${C_CYAN}${C_BOLD} Select Simulation Storage & Output Profile${C_RESET}"
  echo "${C_CYAN}${C_BOLD}======================================================================${C_RESET}"
  echo "  ${C_GREEN}${C_BOLD}[1] High Profile${C_RESET}    : ~365 GB (80 snapshots/case, for >= 1.2 TB disks)"
  echo "  ${C_BLUE}${C_BOLD}[2] Medium Profile${C_RESET}  : ~69 GB  (15 snapshots/case, for >= 200 GB disks)"
  echo "  ${C_YELLOW}${C_BOLD}[3] Light Profile${C_RESET}   : < 250 MB (0 plotfiles, time-series + tables only)"
  echo "  [4] Dry Run         : 0 MB (Parameter validation only)"
  echo ""
  read -r -p "Enter choice [1-4] (default: 2 - Medium): " CHOICE
  case "$CHOICE" in
    1|high|High)
      PROFILE="high"
      ;;
    3|light|Light)
      PROFILE="light"
      ;;
    4|dry-run|dry_run)
      PROFILE="dry-run"
      ;;
    2|medium|Medium|"")
      PROFILE="medium"
      ;;
    *)
      echo "Invalid selection. Defaulting to 'medium'."
      PROFILE="medium"
      ;;
  esac
fi

cd "$PROJECT_ROOT"

# Check for existing simulation runs/checkpoints in target output directory or fallback
HAS_PREV_RUN=false
TARGET_CHECK_DIR="${USER_OUTPUT_DIR:-$PROJECT_ROOT/results}"
if [ -d "$TARGET_CHECK_DIR" ] && [ -n "$(find "$TARGET_CHECK_DIR" -maxdepth 3 \( -name "particle_number.txt" -o -name "ParticleNumber_red.txt" -o -name "chk*" \) 2>/dev/null)" ]; then
  HAS_PREV_RUN=true
elif [ -d "$PROJECT_ROOT/runs" ] && [ -n "$(find "$PROJECT_ROOT/runs" -maxdepth 3 \( -name "particle_number.txt" -o -name "ParticleNumber_red.txt" -o -name "chk*" \) 2>/dev/null)" ]; then
  HAS_PREV_RUN=true
fi

echo ""
if [ "$PROFILE" != "dry-run" ] && [ "$AUTO_RESUME" = true ] && ( [ "$HAS_PREV_RUN" = true ] || [ "$USER_SPECIFIED_RESUME" = true ] ); then
  echo "${C_GREEN}${C_BOLD}[AUTO-RESUME ACTIVE]${C_RESET} Previous simulation runs/checkpoints detected in output directory."
  echo "                     Skipping already completed cases and resuming partially finished cases."
  # Avoid duplicate --resume flag
  if [[ ! " ${EXTRA_ARGS[*]} " =~ " --resume " ]]; then
    EXTRA_ARGS=(--resume "${EXTRA_ARGS[@]}")
  fi
elif [ "$AUTO_RESUME" = false ]; then
  echo "${C_YELLOW}${C_BOLD}[FRESH RUN]${C_RESET} Auto-resume disabled. Simulation cases will run from step 0."
  if [[ ! " ${EXTRA_ARGS[*]} " =~ " --fresh " ]] && [[ ! " ${EXTRA_ARGS[*]} " =~ " --no-resume " ]]; then
    EXTRA_ARGS=(--fresh "${EXTRA_ARGS[@]}")
  fi
fi

case "$PROFILE" in
  high)
    echo "${C_GREEN}${C_BOLD}[PROFILE: HIGH]${C_RESET} 80 snapshots/case, no checkpoints (~365 GB footprint)"
    exec bash scripts/run_full_production.sh --snapshots 80 --checkpoint_period 0 "${EXTRA_ARGS[@]}"
    ;;
  medium)
    echo "${C_BLUE}${C_BOLD}[PROFILE: MEDIUM]${C_RESET} 15 snapshots/case, no checkpoints (~69 GB footprint)"
    exec bash scripts/run_full_production.sh --snapshots 15 --checkpoint_period 0 "${EXTRA_ARGS[@]}"
    ;;
  light|ultra-light)
    echo "${C_YELLOW}${C_BOLD}[PROFILE: LIGHT]${C_RESET} 0 snapshots, no checkpoints (< 250 MB footprint)"
    exec bash scripts/run_full_production.sh --snapshots 0 --checkpoint_period 0 "${EXTRA_ARGS[@]}"
    ;;
  dry-run|dry_run)
    echo "${C_CYAN}${C_BOLD}[PROFILE: DRY RUN]${C_RESET} Parameter validation only (0 MB footprint)"
    exec bash scripts/run_full_production.sh --dry_run "${EXTRA_ARGS[@]}"
    ;;
  *)
    echo "Unknown profile: $PROFILE. Allowed: high, medium, light, dry-run"
    exit 1
    ;;
esac
