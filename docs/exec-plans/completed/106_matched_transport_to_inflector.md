# Execution Plan Summary: Matched Envelope Transport to the Inflector

**Task Index**: 106  
**Date**: 2026-10-26  
**Subject**: Step 4 of the test plan in `docs/physics_notes/neutralizer_efficiency_strategy.md`
(task B1 of `docs/physics_notes/simulation_strategy_tasks.md`). Replace the broken envelope
transport (task 103 open item) with a matched model, compute transmission into the inflector for
DC and RF-bunched beams, and record the recommended configurations and the simulation task list.

Repository state at start: `main` at `e00b3db`; uncommitted work of the confinement scan
(task 107) in the tree, not part of this commit.

---

## 1. Changes

- `src/plasma_column/transport.py` (new):
  - KV edge-envelope equations, fixed-step RK4 on a 1 mm grid aligned with the element edges.
  - `perveance_profile`: K(z) with eta_cell / eta_downstream and B_f(z). Two modes for bunched
    beams: `average`, K = K0 (B_f - eta) (electrons cancel only the RF-averaged charge; default),
    and `per_slice`, K = K0 B_f (1 - eta) (upper bound).
  - `transmission`: geometric estimate, pipe 10 mm x inflector aperture 5 mm x divergence 50 mrad.
  - `match_optics`: differential evolution over the solenoid field (0–0.6 T) and Q1/Q2 gradients
    (+-1.5 T/m), several seeds, warm starts from neighbouring scenarios.
- `scripts/transport_to_inflector.py` (rewritten, `--dry_run`): 10 scenarios x 3 emittances
  (0.25, 0.5, 1.0 pi mm mrad, edge, normalized), eta_cell from the frozen PIC data (0.958),
  B_f(z) from the 620 V sine buncher (task 105). Outputs in `results/transport_to_inflector/`
  (git-ignored): summary CSV/JSON with provenance, envelopes CSV, figure.
- `src/plasma_column/injection_line.py`: default optics set to the matched uncompensated DC tune
  at 1 pi mm mrad (solenoid 0.23 T, Q1 -0.28 T/m, Q2 0.85 T/m). The old 5 / -4.5 T/m gradients
  (k L ~ 1.7) gave envelope radii of ~0.8 m.
- `tests/test_injection_line.py`, `tests/test_injection_line_optics.py`: compensation checks now
  compare the largest envelope along the line instead of the exit radius, which at a fixed tune
  depends on the matching.
- `tests/test_transport.py` (new, 6 tests): rigidity and emittance, emittance-only drift against
  the analytic envelope, compensation and bunching ordering, ellipse clipping and transmission
  limits, old gradients too strong, average vs per-slice compensation.
- `scripts/make_recommended_config_sketch.py` (new, `--dry_run`) and
  `docs/physics_notes/figures/recommended_configurations.{png,pdf}`: schematic of the recommended
  CW and bunched configurations (`.gitignore` exception for `docs/physics_notes/figures/`).
- Docs:
  - `docs/physics_notes/injection_line_transport.md` §2–3 rewritten (model, results); the earlier
    "T > 98% with cell-only compensation" claim is withdrawn.
  - `docs/physics_notes/simulation_strategy_tasks.md` (new): task list for CW and bunched beams.
  - `docs/physics_notes/neutralizer_efficiency_strategy.md`: step 4 results, link to the task list.
  - `docs/production_matrix.md`: transmission row (Unknown → Partial), bunched-downstream row and
    summary.
  - `docs/publication_workflow.md`: transport outputs.

## 2. Results (transmission estimate T, eta_cell = 0.958)

| Scenario | 0.25 | 0.5 | 1.0 pi mm mrad |
|---|---|---|---|
| DC, no compensation | 0.17 | 0.13 | 0.08 |
| DC, cell only | 0.20 | 0.16 | 0.10 |
| DC, whole line | 1.00 | 0.62 | 0.17 |
| Bunched, no compensation | 0.004 | 0.004 | 0.004 |
| Bunched, cell only (average) | 0.001 | 0.001 | 0.004 |
| Bunched, whole line (average) | 0.001 | 0.003 | 0.007 |
| Bunched, whole line (per-slice upper bound) | 0.99 | 0.58 | 0.17 |

- Cell-only compensation adds 2–3 points for a DC beam; the beam blows up again in the
  uncompensated drift and solenoid. Whole-line compensation is what makes the DC beam pass.
- With RF-averaged compensation the bunched peak slice keeps K ~ 4.7 K0 at the inflector and is
  not transported in this layout. Bunching must happen close to the inflector.
- At 1 pi mm mrad the 2 mm parallel launch is emittance-dominated (~19 mm after 0.3 m with no
  space charge), so the launch envelope is also a design parameter.

## 3. Verification

- `pytest -q`: 179 passed, 1 skipped (including uncommitted tests of task 107 in the tree).
- `python scripts/transport_to_inflector.py --dry_run` and the full run (about 2 h, 30 matches).
- `python scripts/make_recommended_config_sketch.py --dry_run` and full run; figure checked.

## 4. Limitations

- Geometric KV transmission estimate, no particle tracking, halo or nonlinear fields; hard-edge
  elements; no coupling from the solenoid rotation.
- eta_cell is a DC-beam, seeded-plasma PIC value; eta_downstream values are assumptions.
- B_f(z) is ballistic (no longitudinal space charge).
- Differences below about 0.005 in T are within the optimizer's noise.
- The manuscript still marks transport as pending; it will be updated after particle tracking
  (task CW5) rather than from the envelope estimate alone.
