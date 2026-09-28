#!/usr/bin/env bash
# ==============================================================================
# Plasma Column Simulation - Full Production Pipeline (Wrapper)
# ==============================================================================
# Preserved for backward compatibility. Delegates directly to scripts/run_production.sh.
#
# Usage:
#   bash scripts/run_full_production.sh [OPTIONS]
#   bash scripts/run_full_production.sh --dry_run
#   bash scripts/run_full_production.sh --matrix cases/pressure_scan_h2_kr.yaml
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/run_production.sh" "$@"
