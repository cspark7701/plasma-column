# Execution Plan Summary: ES Smoke Test, EM vs ES Comparison and Callback Source Fixes

**Task Index**: 95  
**Date**: 2026-10-20  
**Subject**: Checks before relaunching `method_scan`/`method_comparison` with the task-94 ES settings:
(1) 500-step smoke test of every method, (2) EM vs ES comparison, (3) callback source check, which
found and fixed two bugs in the Python-callback ionization source.

Repository state at start: `main` at `9b2fe0c`, clean.

---

## 1. Changes

- `src/plasma_column/neutralization.py`: `sample_secondary_pairs(parent_weight, probability,
  weight_target, rng)`. A parent of weight `w` creates a macro-pair with probability
  `min(1, w P / weight_target)` and weight `max(w P, weight_target)`. The expected created weight is `w P`
  (unbiased). `weight_target <= 0` keeps deterministic fractional weights.
- `scripts/plasma_column_callback_source_picmi_v3.py`:
  - Replaced the hard cut `w P > source_weight_min` (default 1.0) with `sample_secondary_pairs`;
    `--source_weight_min` became `--source_weight_target` (default 100).
  - Fixed `ProtonImpactSource`, which called `gas_mass(cfg)` instead of `gas_mass(cfg.gas)`.
    `gas_mass` returns the H2 mass only for the string `"H2"`, so H2 runs used the Kr mass: the cross
    section was taken at E_cm = 29.6 keV instead of 20.0 keV (sigma 2.04e-20 vs 1.61e-20 m^2, +27 %).
    Kr was unaffected. Both uses now go through `collision_energy_cm_eV(gas, v)`.
  - The callback logs `[source] call N: expected pair weight ..., sampled ...` every 500 calls.
- `scripts/compare_solver_runs.py` (new, `--dry_run`): compares two runs of one case over their common
  time window. It writes `solver_comparison_vs_t.csv`, `solver_comparison_summary.json` and
  `solver_comparison_counts.{png,pdf}`.
- Tests: three `sample_secondary_pairs` tests (`tests/test_neutralization.py`) and a collision-energy
  regression test (`tests/test_gas_cross_sections.py`). `pytest -q`: 139 passed, 1 skipped.
- `docs/simulation_strategies.md`: section 7.

## 2. Smoke test (`runs/es_smoke/`, 7.5 GB, git-ignored)

```bash
python3 scripts/run_scan.py --matrix cases/method_scan_baseline.yaml --run --max_steps 500 \
  --snapshots 1 --output_dir runs/es_smoke --cores 8 --gpu auto
```

- All 6 cases finished in 54 min with exit 0 and were postprocessed. Every case used
  `warpx.const_dt = 9.476e-12` and `poisson_solver = FFT`.
- At 500 steps the beam front is at z = -0.009 m. The beam reaches the column (z = 0) at about step 880,
  so local neutralization is undefined in every case and the sources did not act. This tests the
  pipeline, not the physics.
- The C++/MCC cases use the v7 driver and therefore also start from the quasi-neutral seed (task 94).
- For H2, MCC uses the atomic-H electron-impact table (`MCC_cross_sections/H/`, Janev and Smith,
  threshold 13.6 eV) because warpx-data has no H2 electron-impact table; H2 ionizes at 15.4 eV.
  This fallback predates this task and is unchanged.

## 3. EM vs ES (`runs/solver_cmp/`, 7.4 GB, git-ignored)

The case is seeded H2 at 1e-5 Torr on a 32x32x256 grid, compared over the same 28.4 ns. On this grid
`dt_EM = dt_ES / 14.02`, so ES ran 3 000 steps and EM ran 42 063 steps, with snapshot periods 1 000 and
14 021 steps.

| | ES | EM |
|---|---|---|
| wall time / memory | 5 min 20 s / 0.5 GB | 3 h 32 min / 1.7 GB |
| beam macroparticle weight | 4 600 | 330 |
| local core n_p / n_e / n_i [m^-3] | 1.53e15 / 2.26e15 / 1.58e15 | 1.72e15 / 2.44e15 / 1.59e15 |
| local `eta_net` (`K_eff/K0`) | 0.45 (0.55) | 0.49 (0.51) |

- Global counts agree: maximum relative difference 0.6 % (`N_p`), 1.3 % (`N_e`), 0.07 % (`N_i`).
- Global `eta_net` is -0.078 (ES) vs -0.011 (EM). Both are near zero, and this is a small difference of
  large numbers.
- Local values differ by about 10 %, mostly through `n_p` (12 %). The ES beam has 14x heavier
  macroparticles, so its core density is noisier. These runs cannot separate that noise from a real
  solver difference; an ES run with `nppc_beam 56` (same beam weight as EM) would.
- The comparison window ends one particle-number output (0.5 ns) early, because EM's last output falls
  just before the ES end time.

## 4. Callback source check (`runs/callback_es_check*/`, git-ignored)

The check used the small grid, ES, 3 000 steps and `--enable_ionization_source 1`, for H2 at 1e-5 Torr and
Kr at 1e-6 Torr.

- Before the fixes, no pairs were created: per-step `w P` was 5e-4 here (ES production 1.4e-4, old EM
  production 2e-7), far below the cut of 1.0. The old `results/*/callback_*` runs show the same: `N_e`
  and `N_i` stay at the 5.7e-6 placeholder for all 10 000 steps. Those results contain no ionization.
- After the sampling fix, the H2 run created 27 % more pairs than expected from the beam inside the source
  region (particle data from the snapshots). The cause was the gas-mass bug above.
- After both fixes, at step 3 000:

| | Expected sum of w P (callback) | Created | Independent check |
|---|---|---|---|
| H2 | 1.567e5 | 1.584e5 (+1.1 %, 1 584 pairs) | 1.57e5 from snapshot beam counts |
| Kr | 8.70e4 | 8.49e4 (-2.5 %, 849 pairs) | 0.56x H2, the per-step P ratio |

- `N_e = N_i` exactly. Local core `eta` is about 1e-4 at 28 ns, consistent with t/tau.

## 5. Usage

```bash
python3 scripts/plasma_column_callback_source_picmi_v3.py --run --solver es --gas H2 --pressure_torr 1e-5 \
  --source_weight_target 100 --output_dir runs/callback_H2
python3 scripts/compare_solver_runs.py --run_a runs/solver_cmp/es --run_b runs/solver_cmp/em \
  --label_a ES --label_b EM --output_dir runs/solver_cmp
```

## 6. Limitations and open decision

- Ionization build-up is slow. Callback `eta` grows as t/tau, with tau = 80 us (H2, 1e-5 Torr) and 145 us
  (Kr, 1e-6 Torr). A 23 000-step production run (0.22 us) reaches `eta` of about 0.003 (H2) and 0.0015 (Kr).
  Reaching tau needs about 8.5e6 ES steps (about 3 300 h per case).
- Before launching the matrices, choose one:
  - an accelerated source (rate multiplied by F, labeled as rescaled per AGENTS rule 10);
  - fewer or shorter callback cases, relying on the analytic t/tau curve in `neutralization_source_model.csv`.
- MCC electron-impact ionization from 1 eV seed electrons is also negligible on this timescale, so MCC
  cases will look like the seeded cases.
- `--source_weight_target 100` gives about 1.4e5 macro-pairs per production H2 run. Lower it for
  better statistics in the core; raise it with any acceleration factor.
- Python-callback cost is not yet measured at the full grid with an active source.
- All earlier callback results (EM, `results/*/callback_*`) are invalid and must be rerun.
