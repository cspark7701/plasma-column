# Execution Plan Summary: Transmission vs Downstream Compensation

**Task Index**: 112  
**Date**: 2026-11-15  
**Subject**: Task CW2 of `docs/physics_notes/simulation_strategy_tasks.md`. Transmission of a DC
beam into the inflector versus the compensation downstream of the cell, with the CW1 cell value.

Repository state at start: `main` at `9946f0b`; uncommitted B2/C2/CW3/B3 work in the tree (not
part of this commit).

---

## 1. Changes

- `scripts/transmission_vs_downstream.py` (new, `--dry_run`): eta_cell = 0.91 (CW1 core eta_net,
  task 111), eta_down = 0–0.95 (12 values), emittances 0.25 / 0.5 / 1.0 pi mm mrad (edge,
  normalized); solenoid and Q1/Q2 matched at each point (`match_optics`, warm start from the
  previous eta_down); emittances in parallel processes. Outputs in
  `results/transmission_vs_downstream/` (git-ignored): CSV, JSON with provenance and the eta_down
  needed for T >= 0.5 / 0.9, figure.
- Docs: "Task CW2 result" in `neutralizer_efficiency_strategy.md`; CW2 done in
  `simulation_strategy_tasks.md`; transmission row of `production_matrix.md`.

## 2. Results

| eta_down | 0 | 0.3 | 0.5 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|
| 0.25 pi mm mrad | 0.22 | 0.33 | 0.51 | 0.93 | 1.00 | 1.00 |
| 0.5 pi mm mrad | 0.16 | 0.27 | 0.39 | 0.48 | 0.54 | 0.56 |
| 1.0 pi mm mrad | 0.10 | 0.12 | 0.14 | 0.16 | 0.16 | 0.16 |

- 0.25 pi mm mrad: T >= 0.5 at eta_down >= 0.49, T >= 0.9 at eta_down >= 0.69.
- 0.5 pi mm mrad saturates at T ~ 0.56 (acceptance-limited); 1.0 pi mm mrad emittance-dominated.
- Target for the CW line: eta_down ~ 0.7 through solenoid and quadrupoles, source emittance near
  0.25 pi mm mrad.
- Run time: 36 matches, 2 processes on CPUs 10 and 22, about 55 min.

## 3. Verification

- Dry run and full run; figure checked. End points agree with task 106 (cell only 0.20–0.22, whole
  line 1.0 at 0.25 pi mm mrad).
- Non-monotonic steps below 0.01 in T (e.g. 0.563 → 0.556 at 0.5 pi mm mrad) are optimizer noise.

## 4. Limitations

- Geometric KV estimate, no halo or particle tracking (task CW5); hard-edge elements.
- Uniform eta_down over the whole downstream line; the real retention differs per element (CW3).
- The line starts at the cell entrance with a 2 mm parallel beam; the buncher-to-cell drift seen
  in CW1 is not included.
