# Packaging, Testing, and CI Infrastructure

- **Date**: 2026-08-04
- **Author**: Chong Shik Park
- **Affiliation**: Department of Accelerator Science and Center for Accelerator Research, Korea University, Sejong, 30019 Republic of Korea
- **Task**: Task 01 — Packaging, Tests, and CI Hardening

## Overview

The `plasma_column` repository is fully packaged as a computational research package supporting editable installations via `setuptools` and `pyproject.toml`. The testing and CI infrastructure runs lightweight unit tests without requiring a local WarpX binary or GPU setup in CI environments.

## Package Configuration & Environment Files

- [`pyproject.toml`](file:///home/cspark/Work/projects/plasma-column/pyproject.toml): Standard PEP 621 package specification with `[project.optional-dependencies]` dev set and `[tool.pytest.ini_options]`.
- [`environment.yml`](file:///home/cspark/Work/projects/plasma-column/environment.yml): Conda environment file for reproduction on local development workstations (`warpx-dev`).
- [`requirements-dev.txt`](file:///home/cspark/Work/projects/plasma-column/requirements-dev.txt): Development requirements for lightweight CI runners.
- [`.github/workflows/ci.yml`](file:///home/cspark/Work/projects/plasma-column/.github/workflows/ci.yml): GitHub Actions CI workflow executing multi-version Python testing (`3.10`, `3.11`, `3.12`).

## Unit Test Coverage (`tests/`)

The test suite contains **68 unit tests** covering:
1. **Proton Kinematics**: `proton_beta_gamma_speed(30.0)` at 30 keV ($\beta \approx 0.008, v \approx 2.4 \times 10^6 \text{ m/s}$).
2. **Ideal-Gas Density Conversion**: `gas_density_m3(p_torr, T_K)` conversion from Torr to $\text{m}^{-3}$.
3. **RF Bunched-Beam Optics**: `bunch_length_s()` and `bunch_length_m()` phase-to-length calculations.
4. **Space-Charge Neutralization Scaling**: $K_{\text{eff}}/K_0 = 1 - \eta_{\text{net}}$ perveance degradation formula.
5. **YAML Case Validation**: Automated schema validation across all `cases/*.yaml` simulation matrices.
6. **Decoupled Plotting API**: Matplotlib publication styling and re-exports without requiring `pywarpx`.
7. **Diagnostic Data Parsers**: `DataLoader` in-memory caching and reduced diagnostic text file parsing on synthetic data.

## CI Workflow Command Sequence

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
python -m compileall src scripts .
pytest -q
python scripts/run_case.py --case cases/baseline_h2.yaml --dry_run
python scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run
```

All CI steps complete in lightweight headless environments within seconds.
