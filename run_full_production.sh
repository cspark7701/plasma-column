#!/usr/bin/env bash
# ==============================================================================
# Plasma Column Simulation - Root Production Execution Wrapper
# ==============================================================================
# Executable wrapper launching scripts/run_full_production.sh from root.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/scripts/run_full_production.sh" "$@"
