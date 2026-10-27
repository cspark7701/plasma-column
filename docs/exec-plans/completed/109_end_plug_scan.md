# Execution Plan Summary: End-Plug Voltage and Width Scan

**Task Index**: 109  
**Date**: 2026-10-28  
**Subject**: Task C4 of `docs/physics_notes/simulation_strategy_tasks.md`. Analyze the end-plug
scan launched in task 108 (0.15 T, 1 eV seed) and choose the plug setting for CW1.

Repository state at start: `main` at `9956a4e`, with the uncommitted CW1 runner
(`scripts/run_cw_best_config.py`, committed in task 110).

---

## 1. Changes

- No code changes. Analysis with the existing scripts:
  `analyze_confinement_scan.py --scan_dir results/plug_scan` and
  `analyze_beam_quality.py --scan_dir results/plug_scan`; outputs in
  `results/plug_scan/analysis/` (git-ignored).
- Docs: "Task C4 result" in `neutralizer_efficiency_strategy.md`; C4 done and the CW1 setting in
  `simulation_strategy_tasks.md`; confinement row of `production_matrix.md`.

## 2. Results

Beam moments in the cell-end slab (z = 0.18–0.20 m), averaged over the second half of the run.

| Case | tau_c (second half / last quarter) | N_e,cell(650 ns)/N_e,cell(0) | eta_ss lower bound | r'_rms | eps_n,rms |
|---|---|---|---|---|---|
| no plugs | 3.4 / 3.2 us | 0.69 | 0.040 | 29 mrad | 0.48 pi mm mrad |
| 300 V, 5 mm | 1.1 / 1.0 us | 0.61 | 0.013 | 35 mrad | 0.71 |
| 100 V, 10 mm | 4.8 / 4.7 us | 0.83 | 0.057 | 33 mrad | 0.66 |
| 300 V, 10 mm | 7.2 / 6.4 us | 0.89 | 0.077 | 33 mrad | 0.69 |
| 100 V, 20 mm | 4.7 / 5.5 us | 0.78 | 0.048 | 32 mrad | 0.61 |
| 300 V, 20 mm | 9.3 / 16.6 us | 0.90 | 0.085 | 32 mrad | 0.66 |

- Plugs >= 10 mm wide double to triple tau_c; the 5 mm plugs still shorten it, so the task 107
  failure came from the radial field of the narrow analytic potential, not only from the
  injection artifact.
- 300 V at 10 and 20 mm give the same electron curve. Selected for CW1: 0.15 T, 1 eV, 300 V,
  10 mm (shorter domain, less uncompensated drift before the cell).
- Beam cost of the wide plugs: +10–15% divergence and +30–40% emittance at the cell end.
- eta_ss stays ~0.08: the trap alone does not reach steady-state compensation (tau_ion = 80 us).
- Wall time: 6 cases in parallel, 4 threads each, 11:06 to 02:47 KST (15.7 h); output
  results/plug_scan/ (22G, git-ignored).

## 3. Verification

- All 6 runs exit 0; both analyses run; electron-count figure checked visually.
- No code changed, so no new tests.

## 4. Limitations

- The long upstream drift (0.12 m) lets the uncompensated 10 mA beam blow up to r_rms ~5–7 mm in
  the cell, filling much of the +-10 mm box with transverse loss; absolute beam moments and tau_c
  are not comparable with tasks 107/108, only between C4 cases. Local core eta at 650 ns is not
  meaningful here. The exit slab behind the 20 mm plugs is only 4 mm long and is not used.
- tau_c from 650 ns runs (a decay of < 0.15 tau_c); the 10 vs 20 mm difference is within fit noise.
- Seeded plasma (analytic source estimate); plugs are an analytic potential valid for r << w.
