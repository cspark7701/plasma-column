#!/usr/bin/env bash
# ==============================================================================
# setup.sh — Environment setup for Plasma Column simulation workflows
# ==============================================================================

# Disable CUDA support for OpenMPI if building/running CPU-only
export OMPI_MC_opal_cuda_support="false"

# Base directory for external simulation codes and WarpX dependencies (override via env var)
SIMULATION_CODES_DIR="${SIMULATION_CODES_DIR:-$HOME/Work/simulation_codes-working}"
WARPX_INSTALL_DIR="${WARPX_INSTALL_DIR:-$SIMULATION_CODES_DIR/warpx/install}"
WARPX_DATA_DIR="${WARPX_DATA_DIR:-$SIMULATION_CODES_DIR/warpx-data}"

# Export WarpX data directory for MCC cross sections
if [ -d "$WARPX_DATA_DIR" ]; then
    export WARPX_DATA_DIR="$WARPX_DATA_DIR"
fi

# Add WarpX binaries to PATH if installed
if [ -d "$WARPX_INSTALL_DIR/bin" ]; then
    export PATH="$WARPX_INSTALL_DIR/bin:$PATH"
fi

# Add WarpX libraries to LD_LIBRARY_PATH
if [ -d "$WARPX_INSTALL_DIR/lib" ]; then
    if [ -z "$LD_LIBRARY_PATH" ]; then
        export LD_LIBRARY_PATH="$WARPX_INSTALL_DIR/lib"
    else
        export LD_LIBRARY_PATH="$WARPX_INSTALL_DIR/lib:$LD_LIBRARY_PATH"
    fi
fi

# Activate Conda environment if available and not already active
ENV_NAME="${CONDA_ENV_NAME:-warpx-dev}"
if command -v conda &> /dev/null; then
    if [ "$CONDA_DEFAULT_ENV" != "$ENV_NAME" ]; then
        conda activate "$ENV_NAME" 2>/dev/null || true
    fi
fi

# Include Conda environment library directory in LD_LIBRARY_PATH if active
if [ -n "$CONDA_PREFIX" ] && [ -d "$CONDA_PREFIX/lib" ]; then
    export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

echo "Plasma column simulation environment configured:"
echo "  Conda env     : ${CONDA_DEFAULT_ENV:-none}"
echo "  WARPX_DATA_DIR: ${WARPX_DATA_DIR:-not set}"
if [ -d "$WARPX_INSTALL_DIR" ]; then
    echo "  WarpX install : $WARPX_INSTALL_DIR"
fi

