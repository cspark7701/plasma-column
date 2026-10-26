# Execution Plan Summary: Bunching Factor Along the Injection Line

**Task Index**: 105  
**Date**: 2026-10-26  
**Subject**: Step 1 of the test plan in `docs/physics_notes/neutralizer_efficiency_strategy.md`.
Compute the local bunching factor B_f(z) from the buncher exit through the plasma cell to the
inflector entrance, to replace the fixed reference B_f = 5 when judging compensation in the cell.

Repository state at start: `main` at `7f118ed`, clean.

---

## 1. Changes

- `src/plasma_column/bunching.py` (new). Ballistic bunching of a DC beam by a thin RF gap
  (sine or ideal sawtooth), with a Gaussian source energy spread.
  - Per-particle drift phase.
  - B_f inside the best cyclotron acceptance window (fraction / (Delta_phi/360)).
  - 2-deg peak current ratio.
  - Optimal gap voltage for a given focus position.
- `scripts/analyze_bunching_along_line.py` (new, `--dry_run`). Writes to
  `results/bunching_along_line/` (git-ignored):
  - CSV and summary JSON with provenance;
  - figure with element spans.
  - Geometry comes from `InjectionLine` (cell 0–0.20 m, inflector entrance 1.12 m). The voltage is
    optimized for the inflector entrance.
  - It also gives the static-background estimate 1 - eta_avg/B_f(z) with the PIC core eta_net of
    seeded H2.
- `tests/test_bunching.py`:
  - a DC beam gives B_f = 1;
  - the fundamental harmonic matches the klystron result I_1/I_0 = 2 J_1(X), i.e. |<exp(i psi)>| = J_1(X);
  - B_f grows from the cell to the inflector.
- Docs:
  - `docs/physics_notes/neutralizer_efficiency_strategy.md` §1: result table and interpretation.
  - `docs/production_matrix.md`: the bunched-beam feasibility row is split into "inside the cell"
    (feasible, nearly DC) and "downstream" (not feasible with the cell alone).

## 2. Results (36° acceptance, 5 eV rms spread)

| Buncher | V | B_f cell entrance → exit (mean) | B_f inflector |
|---|---|---|---|
| Sine | 620 V | 1.02 → 1.36 (1.16) | 5.70 |
| Ideal sawtooth | 1178 V | 1.02 → 1.22 (1.11) | 10.0 |

- In the cell, K_eff,peak/K0,peak ~ 0.29 at the exit (eta_avg = 0.96). With B_f = 5.7 it would be
  0.83.
- The bunch forms downstream of the cell, where the cell electrons do not follow the beam.
- B_f = 1.02 at z = 0 is the statistical bias of the maximum-window estimator for a DC beam with
  2e5 particles.

## 3. Verification

- `pytest -q`: 159 passed, 1 skipped.
- Dry run and full run succeed (about 6 s). The figure was checked visually.

## 4. Limitations

- No space charge, which reduces bunching at multi-mA. No longitudinal effects of the solenoid or
  quadrupoles. Thin gap at the buncher exit.
- The buncher voltage and position are assumptions: the repo has no buncher design. The inflector
  entrance is used as the bunch focus.
- eta_avg is a DC-beam, seeded-plasma PIC value; the K_peak estimates are static-background
  estimates, not bunched-beam simulations.
