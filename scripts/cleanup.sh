#!/usr/bin/env bash
# ==============================================================================
# Plasma Column Simulation - Workspace & Output Clean-up Utility
# ==============================================================================
# Safely removes generated simulation outputs, logs, diagnostic plotfiles,
# checkpoints, and build/test artifacts while preserving core directory structure,
# configuration files, source code, and version-controlled documents.
#
# Usage:
#   bash scripts/cleanup.sh [OPTIONS]
#   ./scripts/cleanup.sh [OPTIONS]
#
# Options:
#   --dry_run, -n       List files and directories that would be removed without deleting.
#   --all, -a           Clean all generated outputs (runs, results, logs, data, plots, paper/figures, paper/data, caches).
#   --runs              Clean runs/ and results/ output directories.
#   --logs              Clean logs/ directory and root *.log files.
#   --data              Clean generated CSV/data files in data/ and paper/data/.
#   --plots             Clean generated figures in plots/ and paper/figures/ (preserves tracked assets).
#   --checkpoints       Clean only AMReX checkpoint directories (chk*/) across the workspace.
#   --cache             Clean Python bytecode (__pycache__), pytest caches, and build artifacts.
#   --force, -f         Skip interactive confirmation prompt.
#   --help, -h          Display this help message.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Modes
DRY_RUN=false
FORCE=false
CLEAN_ALL=false
CLEAN_RUNS=false
CLEAN_LOGS=false
CLEAN_DATA=false
CLEAN_PLOTS=false
CLEAN_CHECKPOINTS=false
CLEAN_CACHE=false

# If no specific target flag is provided, default will be CLEAN_ALL after confirmation
SPECIFIC_TARGET=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry_run|-n)
      DRY_RUN=true
      shift
      ;;
    --force|-f)
      FORCE=true
      shift
      ;;
    --all|-a)
      CLEAN_ALL=true
      SPECIFIC_TARGET=true
      shift
      ;;
    --runs)
      CLEAN_RUNS=true
      SPECIFIC_TARGET=true
      shift
      ;;
    --logs)
      CLEAN_LOGS=true
      SPECIFIC_TARGET=true
      shift
      ;;
    --data)
      CLEAN_DATA=true
      SPECIFIC_TARGET=true
      shift
      ;;
    --plots)
      CLEAN_PLOTS=true
      SPECIFIC_TARGET=true
      shift
      ;;
    --checkpoints)
      CLEAN_CHECKPOINTS=true
      SPECIFIC_TARGET=true
      shift
      ;;
    --cache)
      CLEAN_CACHE=true
      SPECIFIC_TARGET=true
      shift
      ;;
    --help|-h)
      echo "Usage: bash scripts/cleanup.sh [OPTIONS]"
      echo ""
      echo "Safely removes generated outputs, logs, plotfiles, and caches."
      echo ""
      echo "Target selection flags:"
      echo "  --all, -a           Clean all generated outputs (runs, results, logs, data, plots, cache)."
      echo "  --runs              Clean simulation output directories (runs/, results/)."
      echo "  --logs              Clean logs/ and root *.log files."
      echo "  --data              Clean generated CSV summaries (data/, paper/data/)."
      echo "  --plots             Clean generated figures (plots/, paper/figures/) while keeping tracked templates."
      echo "  --checkpoints       Clean AMReX checkpoint directories (chk*/) without deleting other metrics."
      echo "  --cache             Clean __pycache__, .pytest_cache, *.egg-info, and temporary files."
      echo ""
      echo "Control flags:"
      echo "  --dry_run, -n       Preview files to delete without modifying anything."
      echo "  --force, -f         Do not prompt for confirmation."
      echo "  --help, -h          Show this help message."
      echo ""
      echo "Default behavior: If no target is specified, prompts to clean standard generated outputs (--all)."
      exit 0
      ;;
    *)
      echo "Error: Unknown option '$1'"
      echo "Use --help to view available options."
      exit 1
      ;;
  esac
done

# If no specific targets selected, default to all
if [ "$SPECIFIC_TARGET" = false ]; then
  CLEAN_ALL=true
fi

if [ "$CLEAN_ALL" = true ]; then
  CLEAN_RUNS=true
  CLEAN_LOGS=true
  CLEAN_DATA=true
  CLEAN_PLOTS=true
  CLEAN_CACHE=true
fi

cd "$PROJECT_ROOT"

echo "======================================================================"
echo " Plasma Column Simulation - Output & Workspace Clean-up"
echo "======================================================================"
echo "  Project Root  : $PROJECT_ROOT"
echo "  Execution Mode: $( [ "$DRY_RUN" = true ] && echo "DRY RUN (preview only)" || echo "ACTIVE DELETION" )"
echo "  Targets Selected:"
[ "$CLEAN_RUNS" = true ] && echo "    • Simulation runs & results (runs/*, results/*)"
[ "$CLEAN_LOGS" = true ] && echo "    • Execution logs (logs/*, *.log)"
[ "$CLEAN_DATA" = true ] && echo "    • Generated datasets (data/*, paper/data/*)"
[ "$CLEAN_PLOTS" = true ] && echo "    • Generated plots & figures (plots/*, paper/figures/*)"
[ "$CLEAN_CHECKPOINTS" = true ] && echo "    • AMReX checkpoint dumps (chk*/)"
[ "$CLEAN_CACHE" = true ] && echo "    • Python cache & pytest artifacts (__pycache__, .pytest_cache)"
echo "======================================================================"

# Prompt for confirmation if not forced and not dry-run
if [ "$DRY_RUN" = false ] && [ "$FORCE" = false ]; then
  read -r -p "Are you sure you want to clean selected outputs? [y/N] " response
  case "$response" in
    [yY][eE][sS]|[yY])
      echo "Proceeding with clean-up..."
      ;;
    *)
      echo "Operation cancelled by user."
      exit 0
      ;;
  esac
fi

TOTAL_ITEMS=0

# Helper to remove path or contents safely
remove_item() {
  local target="$1"
  if [ -e "$target" ] || [ -L "$target" ]; then
    TOTAL_ITEMS=$((TOTAL_ITEMS + 1))
    if [ "$DRY_RUN" = true ]; then
      echo "  [DRY RUN] Would remove: $target"
    else
      echo "  Removing: $target"
      rm -rf "$target"
    fi
  fi
}

# 1. Checkpoints
if [ "$CLEAN_CHECKPOINTS" = true ] && [ "$CLEAN_RUNS" = false ]; then
  echo ""
  echo "=> Cleaning AMReX checkpoint directories (chk*)..."
  while IFS= read -r -d '' chk_dir; do
    remove_item "$chk_dir"
  done < <(find "$PROJECT_ROOT" -type d -name "chk*" -not -path "*/.git/*" -print0 2>/dev/null)
fi

# 2. Simulation Runs & Results
if [ "$CLEAN_RUNS" = true ]; then
  echo ""
  echo "=> Cleaning simulation runs & results..."
  for dir in "runs" "results"; do
    if [ -d "$dir" ]; then
      while IFS= read -r -d '' item; do
        remove_item "$item"
      done < <(find "$dir" -mindepth 1 -maxdepth 1 -not -name ".gitkeep" -print0 2>/dev/null)
    fi
  done

  # Also clean any stray AMReX backtrace or input files in project root
  while IFS= read -r -d '' item; do
    remove_item "$item"
  done < <(find . -maxdepth 1 \( -name "Backtrace*" -o -name "inputs_*" \) -print0 2>/dev/null)
fi

# 3. Logs
if [ "$CLEAN_LOGS" = true ]; then
  echo ""
  echo "=> Cleaning log directories..."
  if [ -d "logs" ]; then
    while IFS= read -r -d '' item; do
      remove_item "$item"
    done < <(find logs -mindepth 1 -maxdepth 1 -not -name ".gitkeep" -print0 2>/dev/null)
  fi

  # Root log files
  while IFS= read -r -d '' item; do
    remove_item "$item"
  done < <(find . -maxdepth 1 -name "*.log" -print0 2>/dev/null)
fi

# 4. Data
if [ "$CLEAN_DATA" = true ]; then
  echo ""
  echo "=> Cleaning generated data & summaries..."
  if [ -d "data" ]; then
    while IFS= read -r -d '' item; do
      remove_item "$item"
    done < <(find data -mindepth 1 -maxdepth 1 -not -name ".gitkeep" -print0 2>/dev/null)
  fi
  if [ -d "paper/data" ]; then
    while IFS= read -r -d '' item; do
      remove_item "$item"
    done < <(find paper/data -mindepth 1 -maxdepth 1 -not -name ".gitkeep" -print0 2>/dev/null)
  fi
fi

# 5. Plots & Figures
if [ "$CLEAN_PLOTS" = true ]; then
  echo ""
  echo "=> Cleaning generated plots and figures..."
  # Clean unversioned files in plots/ while respecting tracked files
  if [ -d "plots" ]; then
    while IFS= read -r -d '' item; do
      # Only delete if git does not track the file
      if ! git ls-files --error-unmatch "$item" >/dev/null 2>&1; then
        remove_item "$item"
      fi
    done < <(find plots -mindepth 1 -maxdepth 1 -not -name ".gitkeep" -print0 2>/dev/null)
  fi

  if [ -d "paper/figures" ]; then
    while IFS= read -r -d '' item; do
      if ! git ls-files --error-unmatch "$item" >/dev/null 2>&1; then
        remove_item "$item"
      fi
    done < <(find paper/figures -mindepth 1 -maxdepth 1 -not -name ".gitkeep" -print0 2>/dev/null)
  fi
fi

# 6. Caches & Build Artifacts
if [ "$CLEAN_CACHE" = true ]; then
  echo ""
  echo "=> Cleaning cache and build artifacts..."
  for cdir in ".pytest_cache" "build" "dist" "src/plasma_column.egg-info"; do
    remove_item "$cdir"
  done

  # Python __pycache__ and *.pyc
  while IFS= read -r -d '' pydir; do
    remove_item "$pydir"
  done < <(find . -type d -name "__pycache__" -not -path "*/.git/*" -print0 2>/dev/null)

  while IFS= read -r -d '' pycfile; do
    remove_item "$pycfile"
  done < <(find . -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*~" \) -not -path "*/.git/*" -print0 2>/dev/null)
fi

# Ensure essential directories still exist for subsequent runs
mkdir -p runs results logs data plots paper/figures paper/data

echo ""
echo "======================================================================"
if [ "$DRY_RUN" = true ]; then
  echo " [DRY RUN COMPLETE] Total items that would be removed: $TOTAL_ITEMS"
else
  echo " [CLEAN-UP COMPLETE] Successfully cleaned $TOTAL_ITEMS item(s)."
  echo " Essential directory structure maintained (runs, results, logs, data, plots)."
fi
echo "======================================================================"
