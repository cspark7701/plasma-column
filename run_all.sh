#!/usr/bin/env bash
# ==============================================================================
# Plasma Column Simulation - Batch Production Launcher for All Matrices
# ==============================================================================
# Executes all three production matrices sequentially using the consolidated
# production pipeline (scripts/run_production.sh):
#   1. Method Scan Baseline : cases/method_scan_baseline.yaml -> results/method_scan/
#   2. Pressure Scan H2/Kr  : cases/pressure_scan_h2_kr.yaml  -> results/pressure_scan/
#   3. Method Comparison    : cases/method_comparison.yaml    -> results/method_comparison/
#
# Usage:
#   ./run_all.sh                          # High profile, fresh run across all matrices
#   ./run_all.sh high                     # High profile explicitly
#   ./run_all.sh medium                   # Medium profile
#   ./run_all.sh light                    # Light profile (fast, time-series only)
#   ./run_all.sh dry-run                  # Validate all pipelines without full PIC execution
#   ./run_all.sh high --cores 8 --gpu 0   # Custom hardware options
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRODUCTION_SCRIPT="$SCRIPT_DIR/scripts/run_production.sh"

if [ ! -f "$PRODUCTION_SCRIPT" ]; then
  echo "Error: Production pipeline script not found at $PRODUCTION_SCRIPT" >&2
  exit 1
fi

# If no arguments provided, default to 'high all'
if [ $# -eq 0 ]; then
  exec "$PRODUCTION_SCRIPT" high all
fi

# Check if user asked for help
for arg in "$@"; do
  if [ "$arg" = "-h" ] || [ "$arg" = "--help" ]; then
    exec "$PRODUCTION_SCRIPT" --help
  fi
done

# Check if a matrix was already specified
has_matrix=false
for arg in "$@"; do
  case "$arg" in
    method_scan|method-scan|mathod_scan|pressure_scan|pressure-scan|method_comparison|method-comparison|all|*.yaml|*.yml)
      has_matrix=true
      break
      ;;
  esac
done

if [ "$has_matrix" = true ]; then
  exec "$PRODUCTION_SCRIPT" "$@"
else
  exec "$PRODUCTION_SCRIPT" "$@" all
fi
