#!/usr/bin/env bash
# ==============================================================================
# Plasma Column Production Launcher — Preset Storage Profiles (Wrapper)
# ==============================================================================
# Preserved for backward compatibility. Delegates directly to scripts/run_production.sh.
#
# Profiles:
#   high    : ~365 GB disk usage (80 snapshots/case, ideal for >= 1.2 TB storage)
#   medium  : ~69 GB disk usage  (15 snapshots/case, ideal for >= 200 GB storage)
#   light   : < 250 MB disk usage (0 3D snapshots, time-series + figures/tables only)
#   dry-run : Validation only    (0 MB disk usage, parameter check)
#
# Matrices:
#   method_scan, pressure_scan, method_comparison, all
#
# Usage:
#   bash scripts/run_production_profile.sh [high|medium|light|dry-run] [MATRIX] [OPTIONS]
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/run_production.sh" "$@"
