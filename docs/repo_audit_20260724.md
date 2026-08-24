# Repository and WarpX Audit Report (2026-07-24)

## Executive Summary

This audit records the initial repository state, file taxonomy, Python/WarpX execution environment, and WarpX C++ source modifications for the Plasma Column Neutralizer simulation project (`plasma_column`).

- **Date**: 2026-07-24
- **Repository Location**: `/home/cspark/Work/projects/plasma_column`
- **Git Branch**: `main` (commit `d5e3a9d`)
- **Remote**: `https://github.com/cspark7701/plasma-column.git`
- **Active Environment**: `warpx-dev` (Python 3.13.13)
- **PyWarpX Availability**: Import OK (`import pywarpx` succeeds)

---

## 1. Project Git State

```text
Branch: main
Remote: origin (https://github.com/cspark7701/plasma-column.git)
Recent commits:
d5e3a9d Start using antigravity
a5ff61c Add environment setup script
097101f First commit
```

The working tree in `/home/cspark/Work/projects/plasma_column` is clean.

---

## 2. File and Script Taxonomy

### 2.1 Front-End Notebooks (`/plasma_column`)
- [plasma_column_analysis_plots_v2.ipynb](file:///home/cspark/Work/projects/plasma_column/plasma_column_analysis_plots_v2.ipynb): Main analysis notebook for generating perveance and neutralization plots across methods.
- [run_plasma_column_method_comparison.ipynb](file:///home/cspark/Work/projects/plasma_column/run_plasma_column_method_comparison.ipynb): Execution and comparison notebook for seeded, callback, and MCC methods.
- [run_python_callback_source_diagnostics_v2.ipynb](file:///home/cspark/Work/projects/plasma_column/run_python_callback_source_diagnostics_v2.ipynb): Diagnostics notebook for Python callback dynamic source model.
- [run_seeded_full_transport_diagnostics.ipynb](file:///home/cspark/Work/projects/plasma_column/run_seeded_full_transport_diagnostics.ipynb): Diagnostics for full seeded neutralization transport.
- [plasma_column_analysis_plots.ipynb](file:///home/cspark/Work/projects/plasma_column/plasma_column_analysis_plots.ipynb), [plasma_column_analysis_plots_v2--1.ipynb](file:///home/cspark/Work/projects/plasma_column/plasma_column_analysis_plots_v2--1.ipynb): Legacy analysis notebooks.

### 2.2 Production & Diagnostic Python Scripts
- [particle_number_diagnostics_v2.py](file:///home/cspark/Work/projects/plasma_column/particle_number_diagnostics_v2.py): Updated per-step particle number and global ratio diagnostic extractor.
- [particle_number_diagnostics_compare.py](file:///home/cspark/Work/projects/plasma_column/particle_number_diagnostics_compare.py): Script comparing species count trajectories across simulation cases.
- [plasma_column_analysis_plots_v2.py](file:///home/cspark/Work/projects/plasma_column/plasma_column_analysis_plots_v2.py): Python module for plotting transverse/longitudinal profiles, species populations, and effective perveance.
- [plasma_column_callback_source_picmi_v3.py](file:///home/cspark/Work/projects/plasma_column/plasma_column_callback_source_picmi_v3.py): PICMI workflow script using Python callbacks for dynamic ion-electron pair creation.
- [plasma_column_mcc_picmi_v7.py](file:///home/cspark/Work/projects/plasma_column/plasma_column_mcc_picmi_v7.py): PICMI simulation script configured for WarpX MCC.
- [warpx_proton_impact_cross_sections_linear/generate_proton_impact_ionization_warpx_data_linear.py](file:///home/cspark/Work/projects/plasma_column/warpx_proton_impact_cross_sections_linear/generate_proton_impact_ionization_warpx_data_linear.py): Data generator for WarpX MCC proton impact cross-section files.

### 2.3 Archived Files (`/archives`)
- `archives/old_scripts/`: Early iterations of PICMI scripts (`v1`–`v6`) and diagnostic notebooks (`perstep_diagnostics`, `three_cases`).
- `archives/corrected_ion_impact_patch_files.zip`: Zip containing the custom C++ MCC patch source files and diff.

### 2.4 Output & Analysis Artifacts (`/analysis_plots`)
Contains summary CSV files (`perveance_summary.csv`, `simulation_case_summary.csv`, `presentation_perveance_summary.csv`) and PNG plots generated from seeded, callback, and MCC runs.

---

## 3. Environment Audit

- **Conda Environment**: `warpx-dev` located at `/home/cspark/Work/simulation_codes-working/miniforge3/envs/warpx-dev`
- **Python Version**: `3.13.13`
- **`pywarpx` Import Check**: `import pywarpx` executed successfully.

---

## 4. WarpX C++ Source Tree Audit

- **Location**: `/home/cspark/Work/simulation_codes-working/warpx`
- **Git Branch**: `development` (commit `6c04a74dc`)
- **Status**: Contains local modifications adding proton-impact ionization to WarpX BackgroundMCC collision handler.
- **Detailed Documentation**: See [docs/warpx_customization.md](file:///home/cspark/Work/projects/plasma_column/docs/warpx_customization.md).

---

## 5. Next Steps

1. Execute lightweight tests / dry-runs to verify reproducibility (Task 01).
2. Proceed with modular package refactoring (`src/plasma_column`) as outlined in `AGENTS.md` and Task 02.
