# Execution Plan Summary: Electron Suppressor Before the Inflector

**Task Index**: 115  
**Date**: 2026-11-15  
**Subject**: Task CW4 of `docs/physics_notes/simulation_strategy_tasks.md`. Which suppressor
voltage keeps the compensating electrons of the line from draining into the inflector field?

Repository state at start: `main` at `5f5e0c8`; uncommitted B2, CW3/B4 and CW5 work in the tree
(B2 and CW3/B4 PIC runs still running). CW4 is committed before CW3 because it finished first and
does not depend on the CW3 runs.

---

## 1. Changes

- `src/plasma_column/suppressor.py` (new): axisymmetric (r, z) finite-difference Poisson solve
  (scipy sparse direct): grounded 10 mm pipe, ring suppressor at -V_s, inflector leakage +V_inf on
  the pipe wall from 30 mm downstream, Neumann ends; 10 mA beam (2 mm) with net compensation
  eta_down upstream of the suppressor (radial deposition by annulus fraction, so the line charge
  is exact on any grid). `barrier_V` (compensated-beam potential minus the lowest on-axis
  potential at and after the suppressor) and `lens_focal_length_m` (paraxial ray in the potential
  relative to V_s = 0, which removes the beam's own space charge).
- `tests/test_suppressor.py` (4 tests): on-axis potential of the uncompensated beam vs the
  analytic value, compensation lowers it, the suppressor creates a barrier, the lens focuses
  with f ~ 1 / V_s^2.
- `scripts/suppressor_scan.py` (new, `--dry_run`): V_s 0–2 kV x aperture 5 / 7.5 mm x eta_down
  0.5 / 0.7 / 0.9 x V_inf 0 / 1 / 3 kV (144 solutions, a few minutes on one core). Outputs in
  `results/suppressor_scan/` (git-ignored): csv/json, barrier and on-axis potential figures.
- Docs: "Task CW4 result" in `neutralizer_efficiency_strategy.md`, CW4 done in
  `simulation_strategy_tasks.md`, new row in `docs/production_matrix.md`.

## 2. Results

- Needed V_s for a 20 V barrier: 62 / 96 / 122 V (5 mm aperture) and 115 / 154 / 195 V (7.5 mm)
  at eta_down 0.5 / 0.7 / 0.9; V_inf 0–3 kV changes this by < 1 V.
- Without a suppressor the barrier is negative (-19 to -68 V): electrons leave the line.
- Lens focal length ~4 km at the needed voltage, 50 m at 1 kV: no effect on the beam optics.

## 3. Verification

- `pytest -q tests/test_suppressor.py`: 4 passed. Three model errors found and fixed during
  development: a Dirichlet downstream end forced 0 V on axis (now Neumann), the beam charge was
  over-deposited by 13% (annulus weighting), and the first lens estimate was dominated by beam
  space charge and had a sign error in the ray equation.

## 4. Limitations

- Static, axisymmetric, uniform beam; the inflector field (a dipole-like electric field) is only
  an illustrative wall potential; electrons judged by the on-axis barrier (no magnetized or
  off-axis orbits, no secondary electrons from the electrode).
