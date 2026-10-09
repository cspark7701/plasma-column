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

# Activate Conda environment if available and not already active
ENV_NAME="${CONDA_ENV_NAME:-warpx-dev}"
if command -v conda &> /dev/null; then
    if [ "$CONDA_DEFAULT_ENV" != "$ENV_NAME" ]; then
        conda activate "$ENV_NAME" 2>/dev/null || true
    fi
fi

# Do NOT add $CONDA_PREFIX/lib to LD_LIBRARY_PATH: conda binaries locate their
# libraries through RPATH, and exporting the conda lib directory makes system
# programs (evince, gedit, eog, ...) load conda's GLib/GObject and fail with
# "libgobject-2.0.so.0: failed to map segment from shared object".
# Remove an entry left over from an earlier version of this script, plus
# duplicate and empty entries (an empty entry means "current directory").
if [ -n "$LD_LIBRARY_PATH" ]; then
    LD_LIBRARY_PATH=$(printf '%s' "$LD_LIBRARY_PATH" | tr ':' '\n' \
        | awk -v drop="${CONDA_PREFIX:+$CONDA_PREFIX/lib}" 'NF && $0 != drop && !seen[$0]++' \
        | paste -sd ':' -)
    if [ -n "$LD_LIBRARY_PATH" ]; then export LD_LIBRARY_PATH; else unset LD_LIBRARY_PATH; fi
fi

# Add WarpX libraries to LD_LIBRARY_PATH (once). Done after conda activation because the
# warpx-dev activation hook (etc/conda/activate.d/env_vars.sh) may already add it.
if [ -d "$WARPX_INSTALL_DIR/lib" ]; then
    case ":${LD_LIBRARY_PATH}:" in
        *":$WARPX_INSTALL_DIR/lib:"*) ;;
        *) export LD_LIBRARY_PATH="$WARPX_INSTALL_DIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ;;
    esac
fi

# ==============================================================================
# Hardware Auto-Detection & Threading / Accelerator Configuration
# ==============================================================================
# Auto-detect maximum available logical CPU threads
MAX_CPUS=$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-$MAX_CPUS}"
export OPENMP_NUM_THREADS="$OMP_NUM_THREADS"
export MKL_NUM_THREADS="$OMP_NUM_THREADS"
export NUMEXPR_NUM_THREADS="$OMP_NUM_THREADS"

# Thread binding and placement (pin threads to cores to prevent migration)
export OMP_PROC_BIND="${OMP_PROC_BIND:-true}"
export OMP_PLACES="${OMP_PLACES:-threads}"

# Auto-detect GPU accelerator
if command -v nvidia-smi &>/dev/null && nvidia-smi -L &>/dev/null; then
    export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
    export WARPX_ACCELERATOR="${WARPX_ACCELERATOR:-CUDA}"
    GPU_INFO="NVIDIA GPU (CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES)"
elif [ -e /dev/nvidia0 ]; then
    export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
    export WARPX_ACCELERATOR="${WARPX_ACCELERATOR:-CUDA}"
    GPU_INFO="NVIDIA GPU via /dev/nvidia0 (CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES)"
else
    export WARPX_ACCELERATOR="${WARPX_ACCELERATOR:-CPU}"
    unset CUDA_VISIBLE_DEVICES
    GPU_INFO="CPU-only execution (No NVIDIA GPU detected)"
fi

echo "Plasma column simulation environment configured:"
echo "  Conda env     : ${CONDA_DEFAULT_ENV:-none}"
echo "  WARPX_DATA_DIR: ${WARPX_DATA_DIR:-not set}"
if [ -d "$WARPX_INSTALL_DIR" ]; then
    echo "  WarpX install : $WARPX_INSTALL_DIR"
fi
echo "  CPU threads   : $OMP_NUM_THREADS (max available: $MAX_CPUS, OMP_PROC_BIND=$OMP_PROC_BIND)"
echo "  Accelerator   : $WARPX_ACCELERATOR ($GPU_INFO)"

