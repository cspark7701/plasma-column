# Installation & Environment Setup Guide

This document provides step-by-step instructions for installing and setting up the **Plasma Column Neutralizer Simulation** package on a new machine or for a new user.

---

## 1. Overview & Requirements

- **Supported OS**: Linux (Ubuntu 20.04+, RHEL/CentOS 8+, Debian), macOS 12+
- **Python Version**: Python 3.10 or higher
- **Core Dependencies**:
  - `numpy`, `scipy`, `matplotlib`, `pandas`, `pyyaml`, `pytest`
- **Optional Dependencies**:
  - `pywarpx` / `picmi` (for full PIC simulations with WarpX)

> [!NOTE]
> All theoretical, analytical compensation, python-callback, and plotting modules operate independently of WarpX. Full WarpX integration is required only for C++ PIC code execution.

---

## 2. Quickstart (Automated Installation)

For an automated setup that creates/activates the environment, installs all dependencies, installs `plasma_column` in editable mode, and runs unit tests:

```bash
# 1. Clone the repository
git clone https://github.com/cspark7701/plasma_column.git
cd plasma_column

# 2. Run the automated installation script
bash scripts/install.sh
```

### Script Usage & Options

The installation script supports custom flags (including `--dry_run` for validation):

```bash
# Dry-run mode (inspect actions without modifying environment)
bash scripts/install.sh --dry_run

# Force Python venv instead of Conda
bash scripts/install.sh --use-venv

# Specify custom Conda environment name
bash scripts/install.sh --env-name my-plasma-env
```

---

## 3. Manual Installation (Step-by-Step)

If you prefer to configure your environment manually, follow these steps:

### Step 1: Clone the Repository

```bash
git clone https://github.com/cspark7701/plasma_column.git
cd plasma_column
```

### Step 2: Set Up Python Environment

#### Option A: Using Conda / Mamba (Recommended)

```bash
# Create environment from environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate warpx-dev
```

#### Option B: Using Python `venv`

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Step 3: Install Package & Dependencies

Install development requirements and the `plasma_column` package in editable (`-e`) mode:

```bash
# Install core and test dependencies
pip install -r requirements-dev.txt

# Install plasma_column in editable mode
pip install -e .
```

### Step 4: Run Verification Tests

Verify the installation by running the test suite and a dry-run simulation case:

```bash
# Run unit test suite
pytest

# Test dry-run simulation case execution
python scripts/run_case.py --case cases/baseline_h2.yaml --dry_run
```

---

## 4. Optional WarpX / PyWarpX Integration

If you plan to run full WarpX PIC simulations on your local machine:

1. Build or install WarpX with Python bindings enabled (`-DWarpX_LIB=ON -DWarpX_PYTHON=ON`).
2. Add the WarpX install directory to your `PYTHONPATH` and `LD_LIBRARY_PATH`:

```bash
export PATH=/path/to/warpx/install/bin:$PATH
export PYTHONPATH=/path/to/warpx/install/lib:$PYTHONPATH
export LD_LIBRARY_PATH=/path/to/warpx/install/lib:$LD_LIBRARY_PATH
```

You can verify environment variables and WarpX detection at any time with:

```bash
python scripts/print_environment.py
```

---

## 5. Troubleshooting & FAQs

- **Missing Cross-Section Data Error**:
  Ensure that `warpx_proton_impact_cross_sections_linear/` is present in your repository root. This directory contains tabulated H2 and Kr proton-impact cross section files (`proton_impact_ionization.dat`) needed for analytical rate calculations.

- **PyWarpX Import Warning**:
  If `pywarpx` is not installed, warnings during `run_case.py` are expected and harmless for non-PIC simulation modes.

- **MPI Warnings**:
  If OpenMPI displays CUDA or opal warnings, set:
  ```bash
  export OMPI_MCA_opal_cuda_support="false"
  ```
