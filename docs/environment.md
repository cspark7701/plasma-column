# Simulation Environment and Reproducibility

## 1. Overview

This document describes the environment setup, dependencies, and execution workflow for the Plasma Column Neutralizer simulation project.

- **OS**: Linux
- **Project Directory**: `/home/cspark/Work/projects/plasma_column`
- **WarpX Source Tree**: `/home/cspark/Work/simulation_codes-working/warpx`
- **Primary Conda Environment**: `warpx-dev`

---

## 2. Conda Environment Setup

### Environment Activation
To activate the pre-configured conda environment:

```bash
conda activate warpx-dev
```

If using `miniforge3` directly:
```bash
source /home/cspark/Work/simulation_codes-working/miniforge3/bin/activate warpx-dev
```

Alternatively, to perform automated environment setup, dependency installation, and verification on any new machine, run:
```bash
bash scripts/install.sh
```
For detailed multi-platform installation options, see [`docs/installation.md`](file:///home/cspark/Work/projects/plasma_column/docs/installation.md).

### Python Dependencies
- **Python**: 3.10+ (tested on Python 3.13.13)
- **Core Packages**:
  - `pywarpx` / `picmi` (PICMI interface to WarpX)
  - `numpy`
  - `pandas`
  - `matplotlib`
  - `pyyaml`
  - `scipy`

---

## 3. Environment Audit Script

To verify your environment setup and WarpX source status, run:

```bash
python scripts/print_environment.py
```

This script reports:
1. Active Python executable & version
2. Conda environment name
3. `pywarpx` import status and module location
4. Key scientific package versions (`numpy`, `pandas`, `matplotlib`, `yaml`, `scipy`)
5. Project git commit hash and branch
6. WarpX source tree path and git status/diff summary

---

## 4. Running Simulation Cases

Simulation runs are managed via YAML case configurations and the `run_case.py` script.

### Case Files Location
- `cases/vacuum.yaml`: Baseline reference beam transport without plasma column
- `cases/baseline_h2.yaml`: 30 keV $10\text{ mA}$ proton beam in $10^{-5}\text{ Torr } \text{H}_2$ gas
- `cases/baseline_kr.yaml`: 30 keV $10\text{ mA}$ proton beam in $10^{-6}\text{ Torr } \text{Kr}$ gas

### Dry-Run Mode (Validation & Metadata Generation)
Use `--dry_run` to inspect derived parameters and write `metadata.json` without performing full PIC steps:

```bash
python scripts/run_case.py --case cases/vacuum.yaml --dry_run
python scripts/run_case.py --case cases/baseline_h2.yaml --dry_run
python scripts/run_case.py --case cases/baseline_kr.yaml --dry_run
```

### Execution Output Directory Structure
Each simulation run writes to a case output directory (`results/<case_name>/`) containing:
```text
results/<case_name>/
├── config.yaml
├── metadata.json
├── run.log
└── (plots & diagnostics output)
```
