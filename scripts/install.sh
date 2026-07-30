#!/usr/bin/env bash
# ==============================================================================
# Plasma Column Neutralizer Simulation - Environment Setup & Installation Script
# ==============================================================================
# This script sets up a Python environment, installs the plasma_column package
# in editable mode, and verifies the setup by running pytest.
#
# Target environment: New setup on a local or remote Linux/macOS machine.
#
# Usage:
#   bash scripts/install.sh [OPTIONS]
#
# Options:
#   --dry_run         Print all setup steps without modifying system state.
#   --use-venv        Force using Python venv instead of Conda/Mamba.
#   --env-name NAME   Conda environment name (default: warpx-dev).
#   --clone-dir DIR   Target directory to clone repository if not inside repo.
#   --help            Display this help message.
# ==============================================================================

set -e

# Default configuration
DRY_RUN=false
USE_VENV=false
ENV_NAME="warpx-dev"
REPO_URL="https://github.com/cspark7701/plasma_column.git"
CLONE_DIR="plasma_column"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry_run)
      DRY_RUN=true
      shift
      ;;
    --use-venv)
      USE_VENV=true
      shift
      ;;
    --env-name)
      ENV_NAME="$2"
      shift 2
      ;;
    --clone-dir)
      CLONE_DIR="$2"
      shift 2
      ;;
    --help)
      echo "Usage: bash scripts/install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --dry_run         Print installation steps without running them."
      echo "  --use-venv        Use Python standard venv instead of Conda."
      echo "  --env-name NAME   Conda environment name (default: warpx-dev)."
      echo "  --clone-dir DIR   Directory to clone repo into if running outside repo."
      echo "  --help            Show this help message."
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help to view available options."
      exit 1
      ;;
  esac
done

echo "======================================================================"
echo " Plasma Column Neutralizer Simulation - Setup & Installation Script"
echo "======================================================================"

# Function to execute or print commands
run_step() {
  local description="$1"
  shift
  echo ""
  echo "=> $description"
  echo "   Command: $*"
  if [ "$DRY_RUN" = true ]; then
    echo "   [DRY RUN] Step skipped."
  else
    "$@"
  fi
}

# 1. Repository Check / Clone
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
  echo "-> Running inside plasma_column repository at: $PROJECT_ROOT"
  cd "$PROJECT_ROOT"
else
  echo "-> plasma_column repository not found in current path."
  run_step "Cloning repository from GitHub" git clone "$REPO_URL" "$CLONE_DIR"
  if [ "$DRY_RUN" = false ]; then
    cd "$CLONE_DIR"
    PROJECT_ROOT="$(pwd)"
  fi
fi

# 2. Environment Setup
if [ "$USE_VENV" = true ] || ! command -v conda &> /dev/null; then
  echo "-> Environment mode: Python venv"
  if [ ! -d "$PROJECT_ROOT/venv" ]; then
    run_step "Creating Python virtual environment in ./venv" python3 -m venv "$PROJECT_ROOT/venv"
  fi
  run_step "Activating Python virtual environment" source "$PROJECT_ROOT/venv/bin/activate"
  PIP_CMD="$PROJECT_ROOT/venv/bin/pip"
  PYTEST_CMD="$PROJECT_ROOT/venv/bin/pytest"
  PYTHON_CMD="$PROJECT_ROOT/venv/bin/python"
else
  echo "-> Environment mode: Conda ($ENV_NAME)"
  if conda info --envs | grep -q "$ENV_NAME"; then
    echo "   Conda environment '$ENV_NAME' already exists."
  else
    if [ -f "$PROJECT_ROOT/environment.yml" ]; then
      run_step "Creating Conda environment from environment.yml" conda env create -f "$PROJECT_ROOT/environment.yml" -n "$ENV_NAME"
    else
      run_step "Creating Conda environment with Python 3.10" conda create -y -n "$ENV_NAME" python=3.10
    fi
  fi
  run_step "Activating Conda environment" conda activate "$ENV_NAME" || true
  PIP_CMD="pip"
  PYTEST_CMD="pytest"
  PYTHON_CMD="python"
fi

# 3. Dependency & Package Installation
run_step "Upgrading pip" $PIP_CMD install --upgrade pip
run_step "Installing development dependencies" $PIP_CMD install -r "$PROJECT_ROOT/requirements-dev.txt"
run_step "Installing plasma_column package in editable mode" $PIP_CMD install -e "$PROJECT_ROOT"

# 4. Verification via Pytest and Dry-Run
run_step "Running unit test suite (pytest)" $PYTEST_CMD -q
run_step "Running verification dry-run (run_case.py)" $PYTHON_CMD "$PROJECT_ROOT/scripts/run_case.py" --case "$PROJECT_ROOT/cases/baseline_h2.yaml" --dry_run

echo ""
echo "======================================================================"
if [ "$DRY_RUN" = true ]; then
  echo " [DRY RUN COMPLETED] All installation steps validated successfully."
else
  echo " [SUCCESS] Plasma Column simulation package installed and verified!"
fi
echo "======================================================================"
