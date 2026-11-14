# Execution Plan Summary: Test-Electron Confinement to 100 us

**Task Index**: 114  
**Date**: 2026-11-15  
**Subject**: Task C2 of `docs/physics_notes/simulation_strategy_tasks.md`. Does the solenoid +
end-plug trap hold electrons for tau_ion ~ 80 us, beyond the ~1 us reach of the PIC runs?

Repository state at start: `main` at `934a10e`; uncommitted B2/CW3 work in the tree.

---

## 1. Changes

- `src/plasma_column/electron_trap.py` (new): guiding-centre test electrons in uniform B_z;
  axial motion under the analytic plug E_z (same potential as the PIC driver); static net beam
  well (1 - eta) phi_b of a uniform 10 mA, 2 mm beam in a 10 mm pipe; Monte Carlo elastic e-H2
  collisions (approximate momentum-transfer cross section, +-30%); Coulomb heating by the beam
  protons (energy diffusion, 0.040 eV/us); velocity changes shift the guiding centre by
  |dv_perp| / omega_c, keeping total energy in the beam well; losses at the pipe wall and beyond
  the plugs. `confinement_time_s` fit.
- `tests/test_electron_trap.py` (6 tests): cross section, plugs hold cold electrons, no-plug
  streaming loss, heating rate, energy conservation with collisions, tau fit. A first version
  drew the gyrophase twice in a collision and heated electrons ~10x too fast; found in the smoke
  run and fixed before the production run.
- `scripts/trap_orbit_tracking.py` (new, `--dry_run`): B_z 0.05 / 0.15 T x plugs 0 / 100 /
  300 V (w = 10 mm, offset 30 mm) x eta 0.5 / 0.9 x birth T 1 / 10 eV, plus a dt / 2.5 check;
  2000 electrons, 100 us, dt 0.5 ns. Outputs in `results/trap_orbit_tracking/` (git-ignored).
- Docs: "Task C2 result" in `neutralizer_efficiency_strategy.md`; C2 done in
  `simulation_strategy_tasks.md`; confinement row of `production_matrix.md`.

## 2. Results

- Plugs >= 100 V: surviving fraction 0.999–1.000 at 100 us for every B, eta and birth energy;
  no radial loss; mean energy 1.5 → ~5 eV (born at 1 eV) and 15 → 16–18 eV (born at 10 eV).
- No plugs: all electrons lost axially, tau_c 1.5–2.7 us (PIC without plugs: 0.7–2.2 us).
- The classical, static-trap bound on eta_ss is 1. The PIC tau_c of 4–9 us with plugs comes from
  self-consistent or numerical effects not in this model.
- Run: 25 cases, 2 processes on CPUs 10 and 22, about 35 min.

## 3. Verification

- `pytest -q tests/test_electron_trap.py`: 6 passed. dt check (0.2 ns) agrees with 0.5 ns.

## 4. Limitations

- Test particles: no electron space charge, ion dynamics, fluctuations or instabilities; no e-e
  or inelastic collisions; approximate elastic cross section; uniform B (no mirror, no field
  errors); plug radial field neglected (r << w); gyrophase not tracked.
- Open: PIC convergence of tau_c (nppc, grid), and the self-consistent fill level of the trap
  (electron space charge vs plug barrier; possible overcompensation).
