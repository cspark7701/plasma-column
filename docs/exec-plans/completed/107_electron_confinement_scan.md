# Execution Plan Summary: Electron-Confinement Scan

**Task Index**: 107  
**Date**: 2026-10-27  
**Subject**: Step 2 of the test plan in `docs/physics_notes/neutralizer_efficiency_strategy.md`
(task C1 of `docs/physics_notes/simulation_strategy_tasks.md`). Measure the electron
confinement time tau_c of the seeded plasma column versus cell solenoid field, seed electron
temperature and analytic end plugs, and the steady-state compensation it allows.

Repository state at start: `main` at `e00b3db` (scan launched 2026-10-26 14:52 KST); task 106
(`8597960`) was committed while the scan ran.

---

## 1. Changes

- `scripts/plasma_column_mcc_picmi_v7.py`:
  - Analytic electrostatic end plugs: phi(z) = -V sum_k exp(-(z - z_k)^2 / (2 w^2)), centres
    `end_plug_offset` outside the cell ends; paraxial applied fields E_z = -phi',
    E_x,y = (x,y)/2 phi'' added to the solenoid `AnalyticAppliedField`
    (`--end_plug_voltage`, `--end_plug_width`, `--end_plug_offset`).
  - RF-bunched injection for task B2 (not used in this scan): periodic von Mises current profile
    through `AnalyticFluxDistribution` (`--beam_bunching_factor`, `--rf_frequency_hz`,
    `--bunch_acceptance_deg`); density bunching at constant velocity. A smoke run with B_f = 5
    injected half a bunch (6.2e8 protons, = 10 mA x 20 ns / 2e) and then nothing through the gap.
- `scripts/run_confinement_scan.py` (new, `--dry_run`): 12 cases, B_z = 0, 0.05, 0.15 T x seed
  T_e = 1, 10 eV x plugs 0 / 300 V (w = 5 mm, offset 15 mm); 32x32x256, 650 ns (68,594 steps,
  production dt); metadata.json per case. Disjoint CPU sets per parallel case (`taskset`): the
  driver's OMP_PROC_BIND=close otherwise pinned all cases to the same cores (0.87 instead of
  ~0.1 s/step). Reusable `command`, `run_case(fixed=...)`, `core_slots` for later scans.
  The finished-case check allows for the 50-step reduced-diagnostic period.
- `scripts/analyze_confinement_scan.py` (new, `--dry_run`): N_e, N_i, N_p in the cell and
  beam-core eta per snapshot; tau_c fit over the second half (with 2-sigma lower bound) and over
  the last quarter; eta_ss lower bound; CSV/JSON and figures in
  `results/confinement_scan/analysis/` (git-ignored).
- `tests/test_end_plug_field.py` (8 tests): plugs off by default, fields against finite
  differences of phi, electrons pushed back into the cell, plug outside the seeded cell.
  `tests/test_bunched_injection.py` (4 tests): DC limit, mean current and acceptance-window
  fraction reproduced for several B_f.
- Docs: results in `neutralizer_efficiency_strategy.md` (step 2), `simulation_strategy_tasks.md`
  (C1 done, C4 redesigned), `production_matrix.md` (confinement rows).

## 2. Results

| B_z | T_e | tau_c no plugs | tau_c 300 V plugs | eta_net core at 650 ns (no plugs / plugs) |
|---|---|---|---|---|
| 0 | 1 eV | 0.70 us | 0.32 us | 0.79 / 0.67 |
| 0 | 10 eV | 0.97 us | 0.40 us | 0.71 / 0.57 |
| 0.05 T | 1 eV | 1.55 us | 0.35 us | 0.84 / 0.64 |
| 0.05 T | 10 eV | 1.23 us | 0.44 us | 0.76 / 0.56 |
| 0.15 T | 1 eV | 2.15 us | 0.47 us | 0.90 / 0.67 |
| 0.15 T | 10 eV | 1.88 us | 0.43 us | 0.82 / 0.51 |

- The cell solenoid triples tau_c (0.70 → 2.15 us). Best: 0.15 T, 1 eV, no plugs; selected for C4.
- Best tau_c is ~40x below tau_ion = 80 us: eta_ss >= 0.026 in steady state from this trap.
- The 5 mm, 300 V plugs shorten tau_c ~4x: they pull the ions out and the electron loss then
  accelerates. Likely a model artifact (paraxial radial field ~6 MV/m at r = 1 mm; upstream plug
  5 mm from the injection plane), so C4 uses 10 and 20 mm plugs in a longer domain.
- Wall time: 12 cases, 3 in parallel on 8 threads each, 20 h (14:52 to 11:01 KST); 31 GB output.

## 3. Verification

- `pytest -q`: 179 passed, 1 skipped (includes uncommitted C3 tests in the tree).
- Dry runs of both scripts; all 12 runs exit 0; figures checked visually.

## 4. Limitations

- Seeded plasma (analytic source estimate), no ionization source, so tau_c is a decay time of
  the seed, not of a sustained column. 650 ns covers ~0.3–1 tau_c; extrapolation to 80 us is
  task C2.
- Small grid (32x32x256, nppc 4), no MCC; DC beam only.
- Plugs are an analytic applied potential, valid only near the axis (r << w), not electrodes.
