# Execution Plan Summary: Quasi-Neutral Seed, Numerics Wiring and Full-Grid ES Check

**Task Index**: 94  
**Date**: 2026-10-16  
**Subject**: Follow-up to task 93. (1) Fix the seeded model, which lost its electrons (chosen fix: seed
ions too). (2) Pass solver, grid and `nppc` from the case/matrix files through `run_case.py`/`run_scan.py`.
(3) Run one full-grid case to check the cost estimate before launching the matrices.

---

## 1. Changes

- `scripts/plasma_column_mcc_picmi_v7.py`: `initial_ion_fraction` default 0.0 -> 1.0. Gas ions are loaded
  at the seed-electron density, so the seed starts quasi-neutral.
- `src/plasma_column/schema.py`: `NumericsConfig` gains `solver` (`em`/`es`), `es_method`
  (`FFT`/`Multigrid`) and `dt` (0 = estimate), all validated. The new `build_numerics_cmd_flags()` passes
  grid, domain, `cfl`, `nppc_beam`, solver, `es_method`, `dt` and `reduced_diag_period`; `nppc_plasma` is
  passed only to the seeded/MCC driver. `mcc` is not passed; the method flag still decides it.
- `scripts/run_case.py`, `scripts/run_scan.py`: append these flags to every driver command.
- `cases/{baseline_h2,baseline_kr,vacuum,method_scan_baseline,method_comparison,pressure_scan_h2_kr}.yaml`:
  `solver: es`, `max_steps: 23000` for every method (2 domain transits, 218 ns), `checkpoint_period: 11500`,
  `diag_period: 2300`, `reduced_diag_period: 50`, `nppc_beam: 4`, with updated comments.
  `bunched_{h2,kr}.yaml` are not used by the pipeline and are unchanged.
- `tests/test_schema.py`: flag-builder and invalid-solver tests; `baseline_h2` now expects `nppc_beam = 4`
  and `solver = es`.
- `docs/simulation_strategies.md`: section 6 updated; section 2 Table 1 marked as superseded (EM settings).

## 2. Verification

- `pytest -q`: 135 passed, 1 skipped.
- `run_full_production.sh ... --dry_run` for all three matrices succeeds, and the printed commands contain
  `--solver es --es_method FFT` and the grid/`nppc` flags.

## 3. Full-grid check (`results/es_check/seeded_H2_baseline/`, git-ignored)

```bash
python3 scripts/run_case.py --case cases/baseline_h2.yaml \
  --output_dir results/es_check/seeded_H2_baseline --cores 8 --gpu auto
```

Cost (64x64x512, dt = 9.476e-12 s, 23 000 steps, 8 cores):

| | Estimate (task 93) | Measured |
|---|---|---|
| wall time | 7–13 h | 8 h 48 min (1.38 s/step average; ~1.45 s/step with the beam filled) |
| memory | — | 2.8 GB max RSS |
| disk | 0.5–1 GB/snapshot | 8.2 GB total: 11 plotfiles of 0.34–0.70 GB + 3 checkpoints of 0.35–0.70 GB |

Physics:

- Seed: electrons 9.67e9 and ions 9.67e9 (weight) at step 0. Electrons are kept by the solenoid:
  9.33e9 (-3.5 %) at step 23 000. The previous electron-only seed lost 70 % by step 3000.
- Ions are lost after step ~18 000: 8.16e9 (-16 %) at the end.
- Beam: 5.90e6 macroparticles (weight 6.78e9) at the end, steady from step ~11 400; the beam fills the
  domain (`beam_z_max_m = 0.24`, `core_beam_fill_fraction = 1.0`).
- Global ratios at step 23 000: `eta_electron_only = 1.38`, `eta_net = 0.17`.
- Local core at step 23 000 (`diagnostics_summary.json`):
  - `n_p` = 1.28e15 m^-3, `n_e` = 1.45e15, `n_i` = 2.2e14;
  - `eta_electron_only_local` = 1.13, `eta_net_local` = 0.96, `K_eff/K0` (net) = 0.04.
  - Electrons collect in the beam potential well and ions are pushed out. The core is near full net
    compensation even though the global `eta_net` is only 0.17.
- `eta_net_local(z)` ranges from 0.75 to 1.24; several slices between z = 0.08 and 0.20 m are above 1 (local
  overcompensation).

Correction to the task 93/94 notes: ion expulsion from the beam core is not a microsecond process. A H2+ ion
falling through the ~160 V beam potential crosses the 5 mm beam radius in tens of ns. The code comment and
`docs/simulation_strategies.md` were updated.

## 4. Matrix cost implication

About 9 h and 8 GB per case with 10 snapshots. Use `--snapshots` 5 or fewer, or delete the intermediate
checkpoints after a case completes, if disk is limited.

## 5. Limitations

- The seeded model is an analytic/data-driven seed, not self-consistent proton-impact ionization. The
  result depends on the seed density (`neutralization: -1` -> data-driven estimate) and its ion fraction.
- `eta_electron_only_local = 1.13` gives `K_eff/K0` (electron only) = -0.13. This is labeled
  overcompensation; only the net value (0.96) is physically meaningful because ions are present.
- Ionization build-up (tau ~80 us for H2 at 1e-5 Torr) is far longer than the 0.22 us run, so the run
  tests how the seed redistributes, not how the plasma builds up.
- `local_neutralization_vs_t.csv` is derived from global particle counts (its first steps divide by a
  tiny `N_p`); use `diagnostics_summary.json` and `local_neutralization_vs_z.csv` for the local result.
- The z-profile includes slices just outside the 0–0.20 m column (z = -0.001 and 0.22 m).
- Callback and C++/MCC methods have not yet been run with the ES settings. Existing `results/` from EM
  runs must be rerun, not just re-postprocessed, to compare with these settings.
