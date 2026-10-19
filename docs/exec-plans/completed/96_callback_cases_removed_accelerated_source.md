# Execution Plan Summary: Callback Cases Removed, Accelerated Source Option, Pressure-Scan Record Fix

**Task Index**: 96  
**Date**: 2026-10-20  
**Subject**: Follow-up to task 95. Decision: option 3 for the production matrices (drop the Python-callback
cases) plus at most one clearly labeled accelerated H2 run. Also fixes the `neutralization` value recorded
by the pressure-scan cases.

Repository state at start: `main` at `46446e1`, clean.

---

## 1. Changes

- `cases/method_scan_baseline.yaml` (6 -> 4 cases), `cases/method_comparison.yaml` (9 -> 7): removed
  `callback_{H2,Kr}_baseline` and `callback_{H2,Kr}_dynamic`. With the physical rate, callback
  neutralization reaches only ~0.003 (H2) / ~0.0015 (Kr) in a 0.22 us run (tau = 80 / 145 us).
  `docs/method_comparison.md` updated.
- `scripts/plasma_column_callback_source_picmi_v3.py`: `--source_rate_factor F` (default 1, must be > 0)
  multiplies the ionization rate.
  - F != 1 prints a `RESCALED SOURCE` banner.
  - `neutralization_source_model.csv` gains `source_rate_factor` and `tau_eff_s = tau_s / F`
    (`tau_s` stays physical).
- `src/plasma_column/schema.py`: `PlasmaConfig.source_rate_factor` (validated > 0) and
  `source_weight_target`. The new `build_plasma_cmd_flags` passes them to the callback driver only.
  It is used by `scripts/run_case.py` and `scripts/run_scan.py`.
- `src/plasma_column/diagnostics.py`: `source_rescaling_note(case_dir)` reads `source_rate_factor` from
  `metadata.json`. For F != 1 the postprocessing summary gets a `rescaling` label (AGENTS rule 10).
- `cases/callback_h2_accelerated.yaml` (new): `callback_H2_accel_x1000_rescaled`, H2 at 1e-5 Torr, F = 1000
  (tau_eff = 80 ns), `source_weight_target` 5000, production ES numerics.
- `cases/pressure_scan_h2_kr.yaml`: `plasma.neutralization` 0.5 -> -1.0. The runners always pass
  `--neutralization -1` for seeded cases, so `config.yaml`/`metadata.json` recorded 0.5 for runs that used
  -1 (noted in task 91). The physics of the runs is unchanged; pressure-scan cases at 1e-6/1e-5 Torr remain
  identical to the method_comparison cases of the same name.
- Tests:
  - `build_plasma_cmd_flags` and the `source_rate_factor` validation (`tests/test_schema.py`);
  - the rescaling label (`tests/test_local_neutralization_masks.py`);
  - a check that every seeded matrix case records the neutralization the runner passes
    (`tests/test_case_files.py`);
  - matrix case-count checks updated from 9 to 7.
  - `pytest -q`: 144 passed, 1 skipped.

## 2. Verification

- Dry runs: method_scan 4 cases and method_comparison 7, both pass. The accelerated case passes, and its
  metadata records `source_rate_factor: 1000.0`.
- Small-grid accelerated test (32x32x256, 1 500 steps, `runs/callback_es_check_fixed/accel_H2_short/`):
  - expected pair weight 1.3436e7 = 1000 x the unscaled 1.342e4;
  - sampled 1.357e7 in 2 714 macro-pairs;
  - `N_e = N_i`.
- Generated configs of overlapping matrix cases are identical apart from names, so each physical run can
  be done once and copied:
  - method_scan `cxx_mcc_{H2,Kr}_baseline` = method_comparison `cxx_{H2,Kr}_mcc_or_custom`;
  - `seeded_Kr_baseline` = `seeded_Kr_1e-6Torr`;
  - method_comparison and pressure_scan seeded cases at 1e-6/1e-5 Torr (differed only in the recorded
    `neutralization` before this fix).

## 3. Full-grid accelerated run (in progress at commit time)

```bash
python3 scripts/run_case.py --case cases/callback_h2_accelerated.yaml \
  --output_dir results/es_check/callback_H2_accel_x1000_rescaled --cores 8 --gpu auto
```

- Started 2026-10-20 07:39 KST at about 1.0 s/step before the source acts.
- Expected 9–12.5 h in total.
- The run's `neutralization_source_model.csv` shows F = 1000 and tau_eff = 8.03e-8 s, so the factor
  reaches the driver through `run_case.py`.
- Results will be added to this summary when the run finishes.

## 4. Production plan

The runs are de-duplicated and run in sequence on 8 cores, with `--snapshots 10`:

| Stage | New runs | Reused (copied) | Time |
|---|---|---|---|
| method_scan | seeded Kr baseline, MCC H2, MCC Kr | seeded H2 baseline (`results/es_check/`) | ~27 h |
| method_comparison (`--skip_step 3,3b`) | vacuum, seeded H2 1e-6, seeded Kr 1e-5 | 4 from method_scan | ~24 h |
| pressure_scan (`--skip_step 3,3b`) | 8 seeded (3e-6, 3e-5, 1e-4, 3e-4 Torr, both gases) | 4 from method_comparison | ~70 h |

That is 14 new runs, about 120 h and 115 GB. Before launching, run a short C++/MCC small-grid check with
the beam in the column (the 500-step smoke test never reached the column).

## 5. Limitations

- The accelerated run is an artificial rescaling. F = 1000 also speeds ionization relative to ion
  expulsion (tens of ns) and electron loss. It illustrates the build-up shape; it does not predict
  eta(t) or the steady state.
- Callback-method results for Kr come only from the small-grid check (task 95) and the analytic t/tau
  curve.
- Other `plasma:` fields (column geometry, `steady_state_neutralization`, `plasma_age_s`, ...) are still
  not passed to the drivers, which use their own defaults (the callback column geometry, 0–0.20 m and
  r = 3 mm, matches the case files).
