# Execution Plan Summary: Fix Issue 1 - 3D Density Grid Extraction from WarpX Plotfiles

**Task Index**: 70  
**Date**: 2026-09-03  
**Subject**: Reconstruct 3D species densities from particle position and weight diagnostics when field charge density grids are absent

---

## 1. Problem Description

During postprocessing of `callback_Kr_dynamic` (and other runs outputting field diagnostics with only total `rho`), `load_plotfile_densities()` attempted to find per-species charge density grids (`rho_beam_protons`, `rho_plasma_electrons`, etc.) in `ds.field_list`. Because only aggregate fields (`E`, `B`, `J`, `rho`, `part_per_cell`) were present in the plotfile's `boxlib` fields, the 3D density arrays (`np_3d`, `ne_3d`, `ni_3d`) remained zero, producing:

```
Warning: Could not extract 3D density grid arrays from results/callback_Kr_dynamic/diags/diag1002000.
```

Consequently, postprocessing fell back to global counts and omitted true z-resolved and radial profiles.

---

## 2. Solution Implemented

In [`src/plasma_column/warpx_io.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/warpx_io.py):
- Extended `load_plotfile_densities()` with a robust second attempt:
  - When field density grids are not present or empty (`not np.any(result["np_3d"])`), it checks `ds.particle_types`.
  - Reads particle positions (`particle_position_x`, `particle_position_y`, `particle_position_z`) and weights (`particle_weight`) for each species (`beam_protons`, `plasma_electrons`, `gas_ions`/`kr_ions`).
  - Performs 3D histogram binning via `np.histogramdd` matching the WarpX mesh geometry (`domain_left_edge`, `domain_right_edge`, `domain_dimensions`).
  - Normalizes by the voxel cell volume $dV = dx \cdot dy \cdot dz$ to reconstruct exact 3D number density arrays $[m^{-3}]$.

---

## 3. Verification

1. **Postprocess Verification**:
   Executed `python3 scripts/postprocess_case.py --case-dir results/callback_Kr_dynamic`:
   - No warning emitted.
   - 3D density arrays extracted successfully.
   - Correctly generated and saved:
     - `results/callback_Kr_dynamic/local_neutralization_vs_z.csv`
     - `results/callback_Kr_dynamic/radial_density_profiles.csv`
     - `results/callback_Kr_dynamic/beam_core_charge_density.csv`
     - `results/callback_Kr_dynamic/plots/z_resolved_neutralization.png / .pdf`
     - `results/callback_Kr_dynamic/plots/radial_density_profiles.png / .pdf`

2. **Unit Tests**:
   - Added `test_load_plotfile_densities_from_particles()` in [`tests/test_warpx_patch_tracking.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_warpx_patch_tracking.py).
   - Test suite expanded to 102 passing tests (100% pass rate).

3. **Audit**:
   - `python3 scripts/audit_repo.py --root .` passed cleanly.
