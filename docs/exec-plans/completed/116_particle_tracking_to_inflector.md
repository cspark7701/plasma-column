# Execution Plan Summary: Particle Tracking to the Inflector

**Task Index**: 116  
**Date**: 2026-11-15  
**Subject**: Task CW5 of `docs/physics_notes/simulation_strategy_tasks.md`. Replace the KV
transmission estimate by tracked particles, for model beams with tails and for the PIC beams at
the cell exit.

Repository state at start: `main` at `797e1c6`; uncommitted B2, CW3/B4 and B5 work in the tree
(B2 and B5 running).

---

## 1. Changes

- `src/plasma_column/particle_tracking.py` (new): the task 106 lattice (hard-edge solenoid in the
  Larmor frame, Q1/Q2), leapfrog in z (dz = 1 mm), space charge from the actual transverse
  distribution (`SpaceChargeGrid`: cloud-in-cell deposit, FFT convolution with (x, y) / r^2,
  open boundary) scaled by K0 (1 - eta(z)) and the surviving current; loss at the 10 mm pipe;
  inflector acceptance r < 5 mm and |x'|, |y'| < 50 mrad. `kv_beam`, `gaussian_beam`,
  `rms_emittance_m_rad`.
- `tests/test_particle_tracking.py` (4 tests): linear field inside a uniform disc, KV beam follows
  the envelope model (eta 0 and 0.9, within 6%), rms emittance of a KV beam.
- `scripts/track_to_inflector.py` (new, `--dry_run`): part A, KV and Gaussian beams (0.25 /
  0.5 pi mm mrad, eta_down 0 / 0.5 / 0.7 / 0.9, CW2 optics); part B, PIC particles of the last
  3 snapshots at the cell exit of CW1 (task 111) and of the C1 no-plug 0.15 T case (task 107),
  rigid mean rotation removed, optics rematched by differential evolution on the counted
  transmission. Outputs in `results/track_to_inflector/` (git-ignored): `track_summary.csv/.json`,
  `track_rms.csv`, `track_to_inflector.{png,pdf}`. Run: 2 processes on CPUs 10 and 22, a few hours.
- Docs: "Task CW5 result" in `neutralizer_efficiency_strategy.md`, CW5 done in
  `simulation_strategy_tasks.md`, transmission row of `docs/production_matrix.md`.

## 2. Results

- KV: tracked T within 0.01–0.06 of the envelope model where the beam is contained.
- Gaussian (0.25 pi mm mrad): T = 0.52 / 0.77 / 0.93 at eta_down 0.5 / 0.7 / 0.9 (KV 0.57 / 0.93 /
  1.00); tails move the target compensation from ~0.7 to ~0.9.
- PIC CW1 beam: T = 0.46–0.49 for eta_down 0.5–0.9, lost at the pipe because it leaves the cell
  ~10 mm wide (x_rms 5 mm, 17 mrad). PIC short-injection beam: T = 0.53 / 0.76 / 1.00.

## 3. Verification

- `pytest -q tests/test_particle_tracking.py`: 4 passed (the envelope test uses an explicit wide
  grid; a coarse default grid failed it).
- An exit kick to imitate the solenoid fringe had the wrong sign for the PIC beams (no Busch
  rotation in the PIC); replaced by removing the mean rotation.

## 4. Limitations

- The PIC cell solenoid of tasks <= 111 has no radial fringe field: no Busch kick and no
  cell-solenoid focusing, so the PIC exit beams are larger than with a real solenoid (CW1
  pessimistic). The fringe option in the driver comes with task CW3.
- Linear hard-edge lattice, 2D slice space charge, no gas scattering, no image charges.
