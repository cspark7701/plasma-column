# Execution Plan Summary: Neutralizer Efficiency Strategy Note

**Task Index**: 104  
**Date**: 2026-10-26  
**Subject**: Record the time structure of the beam that reaches the column and the inflector
(DC from the source, velocity-modulated by the buncher, density-bunched near the inflector),
the ranked strategies for a more efficient neutralizer, and the test plan.

Repository state at start: `main` at `4c33600`, clean.

---

## 1. Changes

- `docs/physics_notes/neutralizer_efficiency_strategy.md` (new):
  - beam time structure along the axial injection line;
  - what limits eta: eta_ss ~ min(1, tau_c/tau_ion), and ion removal;
  - seven ranked strategies: electron trap with end electrodes, active filling, H2, plateau
    pressure, placement where the beam is least bunched, B_z >= 53 mT through the gap,
    overcompensation control;
  - recommended configuration;
  - four-step test plan (bunching factor along the line, confinement scan, bunched-beam PIC,
    transport fix).
- `docs/production_matrix.md`: link to the note from the feasibility section.

## 2. Verification

- Documentation only. All numbers are taken from `paper/manuscript/numbers.tex`,
  `numbers_pic.tex` and `docs/production_matrix.md`.

## 3. Limitations

- Strategies other than gas choice and pressure plateau are analytic estimates. The PIC results
  use a seeded plasma, a DC beam and 218 ns.
- Step 1 of the test plan follows as task 105.
