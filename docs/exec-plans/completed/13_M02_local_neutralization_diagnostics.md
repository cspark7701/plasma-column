# Execution Summary: M02 — Local Neutralization Diagnostics and Beam-Core Metrics

- **Date**: 2026-07-24
- **Task Source**: `docs/01_plasma_column_publication_antigravity_tasks/tasks/M02_local_neutralization_diagnostics.md`

## Summary of Accomplishments

1. **Enhanced Diagnostic Modules**:
   - Updated [`src/plasma_column/diagnostics.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/diagnostics.py) with 3D beam-core spatial masking ($r \le r_{\text{core}}$, $z \in [z_{\text{min,cell}}, z_{\text{max,cell}}]$), volume-averaged local electron-only ($\eta_{\text{local,electron\_only}}$) and net-charge ($\eta_{\text{local,net}}$) neutralization metrics, effective perveance ratios ($K_{\text{eff,local}}/K_0$), overcompensation detection ($K_{\text{eff}}/K_0 < 0$), $z$-resolved profiles ($\eta(z)$), radial density profiles ($n_p(r), n_e(r), n_i(r), \rho_{\text{net}}(r)$), and volumetric core charge density computations ($\text{C/m}^3$).
   - Added `GLOBAL_WARNING_MSG` printing and issuing explicit warnings when local 3D data are absent:
     `WARNING: local neutralization cannot be inferred from global particle count alone.`
   - Expanded [`src/plasma_column/warpx_io.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/warpx_io.py) with plotfile discovery (`find_plotfiles`) and metadata reader helpers.

2. **Updated Postprocessing and Plotting Scripts**:
   - Updated [`scripts/postprocess_case.py`](file:///home/cspark/Work/projects/plasma-column/scripts/postprocess_case.py) to generate all required CSVs (`global_particle_number.csv`, `neutralization_from_particle_number.csv`, `local_neutralization_vs_t.csv`, `local_neutralization_vs_z.csv`, `beam_core_charge_density.csv`, `radial_density_profiles.csv`) and machine-readable `diagnostics_summary.json`.
   - Created [`scripts/make_local_neutralization_plots.py`](file:///home/cspark/Work/projects/plasma-column/scripts/make_local_neutralization_plots.py) generating standard plot pairs (`.png` and `.pdf`):
     - `plots/local_Keff_over_K0_vs_time.png` / `.pdf`
     - `plots/local_eta_vs_time.png` / `.pdf`
     - `plots/radial_density_profiles.png` / `.pdf`
     - `plots/z_resolved_neutralization.png` / `.pdf`
     - `plots/global_particle_number_sanity_check.png` / `.pdf`

3. **Added Unit Tests**:
   - Created [`tests/test_local_neutralization_masks.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_local_neutralization_masks.py) covering uniform density neutralization, displaced electron cloud failure modes ($\Delta x = 10\text{ mm}$ showing $\eta_{\text{local}} < 0.05$ despite high global counts), overcompensation detection ($K_{\text{eff}}/K_0 < 0$), missing local diagnostic warnings, and profile calculations.
   - Updated [`tests/test_diagnostics_particle_number.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_diagnostics_particle_number.py).
   - Added `ELEMENTARY_CHARGE` constant alias in [`src/plasma_column/constants.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/constants.py).

4. **Documentation**:
   - Added physics note [`docs/physics_notes/local_neutralization_diagnostics.md`](file:///home/cspark/Work/projects/plasma-column/docs/physics_notes/local_neutralization_diagnostics.md) detailing the physics distinction between global particle counts and local beam-core space-charge neutralization, mathematical formulas, and output file standards.

5. **Deliverables Summary**:
   - `src/plasma_column/diagnostics.py`
   - `src/plasma_column/warpx_io.py`
   - `src/plasma_column/constants.py`
   - `scripts/postprocess_case.py`
   - `scripts/make_local_neutralization_plots.py`
   - `tests/test_local_neutralization_masks.py`
   - `tests/test_diagnostics_particle_number.py`
   - `docs/physics_notes/local_neutralization_diagnostics.md`
   - `docs/exec-plans/completed/13_M02_local_neutralization_diagnostics.md`
