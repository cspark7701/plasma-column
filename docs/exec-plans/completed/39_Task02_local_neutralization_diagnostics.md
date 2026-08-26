# Execution Summary: Task 02 — Local Neutralization Diagnostics

- **Date**: 2026-08-04
- **Author**: Chong Shik Park
- **Affiliation**: Department of Accelerator Science and Center for Accelerator Research, Korea University, Sejong, 30019 Republic of Korea
- **Task Source**: [`docs/03_plasma_column_repo_analysis_task_prompts/TASK_02_local_neutralization_diagnostics.md`](file:///home/cspark/Work/projects/plasma-column/docs/03_plasma_column_repo_analysis_task_prompts/TASK_02_local_neutralization_diagnostics.md)

## Summary of Accomplishments

1. **Primary Local Beam-Core Diagnostic API ([`src/plasma_column/diagnostics.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/diagnostics.py))**:
   - Implemented cylindrical spatial beam-core mask routines ($r_{\text{core}} \le 2\text{ mm}$, $z \in [0.0\text{ m}, 0.20\text{ m}]$):
     - `compute_local_core_neutralization(ne_3d, ni_3d, np_3d, x, y, z)`
     - `compute_radial_density_profiles(ne_3d, ni_3d, np_3d, x, y, z)`
     - `compute_local_neutralization_vs_z(ne_3d, ni_3d, np_3d, x, y, z)`
     - `compute_charge_density()`
   - Keeps electron-only ($\eta_{\text{electron\_only}}$) and net-charge ($\eta_{\text{net}}$) indicators separate and flags overcompensation regimes ($K_{\text{eff,local}}/K_0 < 0$).
   - Explicitly emits warning if only domain-wide global particle counts exist: `WARNING: local neutralization cannot be inferred from global particle count alone.`

2. **Standardized Per-Case Output Artifacts ([`scripts/postprocess_case.py`](file:///home/cspark/Work/projects/plasma-column/scripts/postprocess_case.py))**:
   - Postprocessing generates 6 standardized diagnostic datasets per case:
     - `global_particle_number.csv`
     - `local_neutralization_vs_t.csv`
     - `local_neutralization_vs_z.csv`
     - `beam_core_charge_density.csv`
     - `radial_density_profiles.csv`
     - `diagnostics_summary.json`

3. **Publication Diagnostic Figure Pipeline ([`scripts/make_local_neutralization_plots.py`](file:///home/cspark/Work/projects/plasma-column/scripts/make_local_neutralization_plots.py))**:
   - Renders 5 standard diagnostic figure pairs (`.png` and `.pdf`):
     - `plots/local_Keff_over_K0_vs_time`
     - `plots/local_eta_vs_time`
     - `plots/radial_density_profiles`
     - `plots/z_resolved_neutralization`
     - `plots/global_particle_number_sanity_check`

4. **Synthetic Diagnostic Unit Tests ([`tests/test_local_neutralization_masks.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_local_neutralization_masks.py))**:
   - Tested:
     1. Uniform overlapping electron/proton density gives exact expected $\eta_{\text{local}}$.
     2. Displaced electron cloud ($\Delta x > 0$) gives poor beam-core compensation despite high global $N_e$.
     3. Overcompensation is flagged explicitly (`overcompensated: True`).
     4. Missing 3D grid data gracefully falls back with explicit warnings.

5. **Deliverables Summary**:
   - [`src/plasma_column/diagnostics.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/diagnostics.py)
   - [`scripts/postprocess_case.py`](file:///home/cspark/Work/projects/plasma-column/scripts/postprocess_case.py)
   - [`scripts/make_local_neutralization_plots.py`](file:///home/cspark/Work/projects/plasma-column/scripts/make_local_neutralization_plots.py)
   - [`docs/physics_notes/local_neutralization_diagnostics.md`](file:///home/cspark/Work/projects/plasma-column/docs/physics_notes/local_neutralization_diagnostics.md)
   - [`tests/test_local_neutralization_masks.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_local_neutralization_masks.py)
   - [`docs/exec-plans/completed/39_Task02_local_neutralization_diagnostics.md`](file:///home/cspark/Work/projects/plasma-column/docs/exec-plans/completed/39_Task02_local_neutralization_diagnostics.md)
