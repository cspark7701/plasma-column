# Execution Plan Summary: Beam-Core Local Neutralization Time Series

**Task Index**: 99  
**Date**: 2026-10-21  
**Subject**: Before production, `local_neutralization_vs_t.csv` held the domain-wide ParticleNumber
ratios under `*_local` column names, a global-vs-local mislabel (found in task 96). It now holds
beam-core values from every plotfile.

Repository state at start: `main` at `87891f2` (task 98), clean.

---

## 1. Changes

- `src/plasma_column/diagnostics.py`:
  - New `compute_local_neutralization_vs_t(plotfiles)` and `LOCAL_T_COLUMNS`. Each row is one
    snapshot: step, time, `beam_in_core`, `core_beam_fill_fraction`, core-averaged np/ne/ni, local
    eta_electron_only/eta_net and K_eff/K0.
  - The core definition is the same as in `diagnostics_summary.json`: r <= 2 mm, 0 <= z <= 0.20 m,
    beam-filled cells.
  - `postprocess_case_directory` writes this series. With no plotfiles, it writes a header-only CSV
    instead of global ratios. Global ratios remain in `global_particle_number.csv` and
    `neutralization_from_particle_number.csv`.
- `scripts/make_local_neutralization_plots.py`:
  - Strips the `_local` suffix before calling the shared plot functions. Those functions read
    `eta_net`/`keff_over_k0`, so the previous "Beam-Core Local Neutralization vs Time" plots were drawn
    empty.
- `docs/physics_notes/local_neutralization_diagnostics.md`: the CSV description is updated.
- `tests/test_diagnostics_particle_number.py`:
  - A case with no plotfiles gives an empty local series.
  - A new test checks one row per plotfile with core values and NaN before the beam arrives.

## 2. Verification

- `pytest -q`: 153 passed, 1 skipped.
- Re-postprocessed `results/production/callback_H2_accel_x1000_rescaled` and
  `results/production/seeded_H2_1e-5Torr`. The 11-row series reproduce the per-snapshot table in
  exec-plan 96 §3 (for example, eta_net local 0.811 and 0.958 at step 23000).
  - `seeded_H2_1e-5Torr/metadata.json` is unchanged.

## 3. Limitations

- Time resolution is the plotfile period (2300 steps = 21.8 ns with 10 snapshots). Reduced diagnostics
  remain global.
