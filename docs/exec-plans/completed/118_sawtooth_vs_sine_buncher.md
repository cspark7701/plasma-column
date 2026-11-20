# Execution Plan Summary: Ideal Sawtooth vs Sine Buncher

**Task Index**: 118  
**Date**: 2026-11-15  
**Subject**: Task B6 of `docs/physics_notes/simulation_strategy_tasks.md`. Does the stronger
bunching of a sawtooth buncher (window B_f = 10 vs 5.7) still pay off with space charge?

Repository state at start: `main` at `e9d1c69`; uncommitted B2 and CW3/B4 work in the tree (B2
trap cases and B4 PIC runs running).

---

## 1. Changes

- No code changes: `scripts/sliced_bunch_transport.py` (task 117) run with `--waveform sawtooth`
  (ideal linear ramp over the RF period in `plasma_column.bunching.BuncherModel`). Outputs in
  `results/sliced_bunch_transport/sliced_bunch_sawtooth.{csv,json,png,pdf}` (git-ignored). Run:
  2 processes on CPUs 10 and 22, about 2 h.
- Docs: "Task B6 result" in `neutralizer_efficiency_strategy.md`, B6 done in
  `simulation_strategy_tasks.md`.

## 2. Results

- Optimal voltages: 1.17 kV (baseline), 4.27 kV (between Q1 and Q2), 14 kV (7.5 cm before the
  inflector); window B_f 10, 10, 6.8; the whole beam is inside the window for the first two.
- No crossover: slices peak at the inflector (local factor 19 at the baseline, 36 for Q1–Q2).
- G (0.25 pi mm mrad), RF-averaged compensation, eta_down 0 / 0.5 / 0.9: baseline 1.25 / 0.59 /
  0.33 (sine 0.010 / 0.003 / 0.001); Q1–Q2 3.4 / 2.0 / 1.5 (sine 0.62 / 0.29 / 0.15). Per-slice
  bound at eta_down 0.9: 6.9 and 10.0.

## 3. Verification

- Same code path as task 117 (tests in `tests/test_bunching.py`); `--dry_run` checked.

## 4. Limitations

- Ideal sawtooth (not realizable; a few-harmonic buncher gives less); ballistic, independent
  slices, KV envelopes. Non-baseline positions are an alternative-placement study; the 14 kV case
  is far outside the model.
