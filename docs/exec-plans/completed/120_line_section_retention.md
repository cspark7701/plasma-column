# Execution Plan Summary: Electron Retention in the Solenoid and Quadrupole Section

**Task Index**: 120  
**Date**: 2026-11-16  
**Subject**: Task CW3 of `docs/physics_notes/simulation_strategy_tasks.md`. How long do
residual-gas compensation electrons stay in the main solenoid and quadrupoles, and which
eta_downstream can they give (input to CW2/CW5)?

Repository state at start of the runs: `main` at `dfe0116` (CW3 launched 2026-11-15 18:33, after
B2); driver changes uncommitted until now.

---

## 1. Changes

- `scripts/plasma_column_mcc_picmi_v7.py`: new config fields and options `--solenoid_zmin`,
  `--solenoid_zmax`, `--solenoid_fringe` (tanh edges with the paraxial radial field
  B_x,y = -(x,y)/2 dB_z/dz, which gives the Busch kick; default 0 = the previous hard edge, so
  earlier runs are reproducible) and `--quadrupoles "z0:z1:G;..."` (hard-edge B_x = G y,
  B_y = G x). The applied field sums solenoid and quadrupole terms.
- `tests/test_quadrupole_field.py` (8 tests): zero fields without quadrupoles, gradients inside and
  outside, G > 0 focuses protons in x, hard-edge solenoid unchanged, fringe field divergence-free
  paraxially with B_r < 0 at the entrance.
- `scripts/run_confinement_scan.py`: `core_slots(..., offset)` so two runners share the machine.
- `scripts/run_line_section.py` (new, `--dry_run`): groups cw3 (fields / solenoid / nofields,
  `results/line_section/`) and b4 (task B4); 32 x 32 x 816, z -0.02 to 0.80 m, 650 ns.
- `scripts/analyze_line_section.py` (new, `--dry_run`): per-region electron/ion/beam counts,
  tau_c fit and late core eta_net; outputs in `<scan_dir>/analysis/` (git-ignored).
- Docs: "Task CW3 result" in `neutralizer_efficiency_strategy.md`, CW3 done in
  `simulation_strategy_tasks.md`, new row in `docs/production_matrix.md`.

## 2. Results

- tau_c (solenoid + quads / solenoid only / no fields): main solenoid 2.4 / 3.0 / 0.57 us;
  Q1 0.57 / 0.67 / 0.90 us; Q2 0.71 / 1.4 / 3.4 us; drift solenoid–Q1 0.46 / 0.59 / 0.54 us.
- Late core eta_net 0.6–0.97 everywhere (seed not yet decayed).
- Steady state at 1e-5 Torr (tau_ion 80 us): eta_ss ~0.03 in the solenoid, < 0.01 in the quads.

## 3. Verification

- `pytest -q tests/test_quadrupole_field.py`: 8 passed; smoke runs checked that the WarpX parser
  accepts the tanh expressions. Runs: 3 x 4 threads on physical cores 0–5, 2026-11-15 18:33 to
  2026-11-16 19:21, all exit 0 (0.5 s/step alone, up to 1.5 s/step while B4 shared the machine).

## 4. Limitations

- Seeded plasma (analytic source estimate), no plugs, small grid, 650 ns; quadrupole edges hard;
  the PIC tau_c may be a lower limit (task 114). The 2 mm parallel injected beam is not the CW1
  cell-exit beam (retention study, not transport).
