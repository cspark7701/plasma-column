# Execution Plan Summary: Bunched Beam in the Plasma Cell (PIC)

**Task Index**: 119  
**Date**: 2026-11-15  
**Subject**: Task B2 of `docs/physics_notes/simulation_strategy_tasks.md`. Do the cell electrons
survive the 18 ns gaps between bunches, and how does peak-bunch neutralization compare with the
RF average?

Repository state at start of the runs: `main` at `b0f6748` (runs launched 2026-11-14); committed
after tasks 115–118, which finished earlier. Uncommitted CW3/B4 work remains in the tree (both PIC
groups running).

---

## 1. Changes

- `scripts/run_bunched_cell.py` (new, `--dry_run`): 5 WarpX cases (trap / open x B_f 1, 1.3, 5),
  CW1 domain, 32 x 32 x 336, 650 ns, 40 snapshots, 5 x 4 threads on separate physical cores.
- `src/plasma_column/bunched_cell.py` (new): `rf_wavelength_m`, `core_z_profiles` (core densities
  r <= 2 mm and the proton line density), `bunch_metrics` (eta_avg over whole RF wavelengths,
  eta_peak over the top 10% of the line density, B_cell from the line density, n_e modulation,
  gap charge). The peak bins and B_cell use the line density so that transverse beam growth along
  z is not mistaken for bunching (a core-density B_cell gave 2.08 for the DC case).
- `tests/test_bunched_cell.py` (5 tests).
- `scripts/analyze_bunched_cell.py` (new, `--dry_run`, `--z_start` for the B4 section): time
  series, summary, figures in `results/bunched_cell/analysis/` (git-ignored);
  `scripts/analyze_confinement_scan.py --scan_dir results/bunched_cell` for tau_c.
- Docs: "Task B2 result" in `neutralizer_efficiency_strategy.md`, B2 done in
  `simulation_strategy_tasks.md`, bunch-gap row of `docs/production_matrix.md`.

## 2. Results

- trap DC / B_f 1.3 / B_f 5: eta_avg 0.96 / 0.85 / -0.30, eta_peak 0.96 / 1.20 / -0.01 (fluctuations
  +-0.2–0.4), tau_c 3.0 / 1.3 / 0.12 us. Open B_f 1.3: eta_avg 0.72, tau_c 0.31 us; open B_f 5: 0.02 us.
- B_cell measured 1.01 / 1.26 / 3.6.
- Bunching shortens confinement; strong bunching empties the trap.

## 3. Verification

- `pytest -q tests/test_bunched_cell.py`: 5 passed. Run: 2026-11-14 to 2026-11-15 18:31, all five
  cases exit 0, ~0.5–0.7 s/step. A first peak definition (bins above half maximum) selected every
  bin at B_cell 1.26 and was replaced by the top-10% window.

## 4. Limitations

- Small grid, 4 particles per cell, seeded plasma (analytic source estimate); strong snapshot
  fluctuations of the core eta; B_f 5 is a bunch-focus study (bunch injected uncompensated 7 cm
  before the cell); hard-edge cell solenoid (no fringe field) as in tasks <= 111.
