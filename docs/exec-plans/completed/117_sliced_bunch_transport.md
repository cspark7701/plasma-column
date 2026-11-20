# Execution Plan Summary: Sliced-Bunch Transport into the Inflector Acceptance

**Task Index**: 117  
**Date**: 2026-11-15  
**Subject**: Task B5 of `docs/physics_notes/simulation_strategy_tasks.md`. RF-averaged accepted
current with the bunch resolved in longitudinal slices, instead of one peak slice with the window
bunching factor.

Repository state at start: `main` at `724d4f7`; uncommitted B2 and CW3/B4 work in the tree (B2
PIC runs still running). B4 (PIC of the bunched beam downstream) has not run yet, so both
compensation limits are reported; B4 decides which applies.

---

## 1. Changes

- `src/plasma_column/bunching.py`: `slice_bunching_along_line` splits the best acceptance window
  at the inflector into slices, follows each slice by its circular-mean phase, and returns its
  local current factor along the line (beam fraction within +- half a slice width / slice width).
- `tests/test_bunching.py`: DC slices have factor 1, factor 1 upstream of the buncher, slice
  fractions add up to the window fraction.
- `scripts/sliced_bunch_transport.py` (new, `--dry_run`): sine (B5) or sawtooth (B6) buncher at
  the baseline, between Q1 and Q2, and 7.5 cm before the inflector (alternative-placement study);
  9 slices of 4 deg; KV slice envelopes with K = K0 (B_s - eta) or K0 B_s (1 - eta); common optics
  matched by differential evolution for sum_s f_s T_s (warm start from task 113); 0.25 / 0.5 pi mm
  mrad, eta_down 0 / 0.5 / 0.9, eta_cell 0.91. Outputs in `results/sliced_bunch_transport/`
  (git-ignored): `sliced_bunch_<waveform>.csv/.json/.png/.pdf`. Run: 2 processes on CPUs 10 and 22,
  about 2 h.
- Docs: "Task B5 result" in `neutralizer_efficiency_strategy.md`, B5 row in
  `simulation_strategy_tasks.md`, bunched-downstream row of `docs/production_matrix.md`.

## 2. Results

- The accepted bunch of the sine buncher crosses over before the inflector: local slice factor
  ~22–24 (baseline at z = 0.8 m), converged in particle number (200k vs 800k).
- Gain G at 0.25 pi mm mrad, RF-averaged / per-slice bound at eta_down 0.9: baseline 0.001 / 0.59;
  Q1–Q2 buncher 0.15 / 4.4; buncher 7.5 cm before the inflector 3.5 / 5.6.
- The window-B_f peak slice of tasks 106 and 113 is optimistic for the baseline buncher.

## 3. Verification

- `pytest -q tests/test_bunching.py`: 5 passed. Smoke run with `--maxiter 1` before the
  production run; slice factors checked against 4x more particles.

## 4. Limitations

- Ballistic bunching without longitudinal space charge (the crossover would be blunted; the slice
  factor near the caustic depends on the slice width); slices transported independently; KV
  envelopes and geometric transmission; the 7.5 cm / 8.7 kV case is outside the model.
