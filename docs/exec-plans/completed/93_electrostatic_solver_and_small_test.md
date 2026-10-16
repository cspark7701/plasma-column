# Execution Plan Summary: Electrostatic Solver Option, Beam Weight, Run Estimates and Small Test

**Task Index**: 93  
**Date**: 2026-10-16  
**Subject**: Follow-up to task 92 (the beam never reached the column in the 10 000-step runs). Steps:
(1) electrostatic solver, (2) beam macroparticle weight, (3) cost estimates, (4) small WarpX test.

---

## 1. Changes

- `src/plasma_column/constants.py`: `estimate_electrostatic_timestep` (electron gyration, plasma
  frequency, fastest-electron Courant limits) and `beam_potential_depth_V`.
- `scripts/plasma_column_mcc_picmi_v7.py` and `scripts/plasma_column_callback_source_picmi_v3.py`:
  `--solver {em,es}` (default `em`, so existing commands are unchanged), `--es_method {FFT,Multigrid}`
  (FFT = integrated Green function with open boundaries; Multigrid uses Dirichlet walls), `--dt`
  (0 = estimate). For `es` the time step is passed to WarpX as `time_step_size`. The v7 driver reports
  `field_solver`, `beam_macroparticle_weight`, `beam_domain_transit_steps`, `beam_reaches_column_end_step`
  and the dt limits.
- Beam weight: flux injection adds `nppc_beam` macroparticles per source cell per step, so weight
  = `I dt / e / (nppc_beam * N_source_cells)`. The larger ES time step raises it 28x; `nppc_beam` sets the rest.
- `src/plasma_column/diagnostics.py` (found by the test): `load_particle_number_diagnostic` took
  `Np, Ne, Ni` from columns 5, 6, 7, which in WarpX's 3-species file (10 columns) are
  `gas_ions_macroparticles`, `total_weight`, `beam_protons_weight`. Columns are now chosen by the
  `<species>_weight()` header names (fallback: 7, 8, 9 for 10 columns; the old 5, 6, 7 kept for
  8-column files). Global eta is NaN when `Np = 0`.
- `tests/test_local_neutralization_masks.py`: test for the 10-column ParticleNumber layout.
- `docs/simulation_strategies.md`: section 6 (dt limits, EM vs ES table).

## 2. Estimates (production grid 64x64x512, H2 1e-5 Torr, 10 mA, 0.15 T)

| | EM (current) | ES |
|---|---|---|
| dt | 3.38e-13 s | 9.48e-12 s (gyration-limited) |
| steps to column end / domain transit | 2.7e5 / 3.2e5 | 9 700 / 11 400 |
| beam weight (`nppc_beam` 4) | 41 | 1 150 |
| beam macroparticles, filled domain (`nppc_beam` 4) | 1.6e8 | 5.9e6 |
| wall time per step (8 cores) | ~2 s | 1.1 s measured (first 300 steps; expected 1.5–2 s when filled) |
| 23 000 steps (2 transits) | — | roughly 7–13 h per case |

Disk: the coarse test plotfile is 49 MB; at full resolution with a filled beam, roughly 0.5–1 GB per
snapshot (estimate), so use 10 snapshots or fewer.

## 3. Small test (`runs/es_small_test/`, git-ignored)

```bash
python3 scripts/plasma_column_mcc_picmi_v7.py --solver es --run --output_dir runs/es_small_test \
  --gas H2 --pressure_torr 1e-5 --nx 32 --ny 32 --nz 256 --nppc_beam 4 --nppc_plasma 4 \
  --max_steps 3000 --diag_period 1000 --cores 8 --gpu auto
python3 scripts/postprocess_case.py --case-dir runs/es_small_test
```

- Exit 0; 5 min 26 s wall time, 0.11 s/step, 0.5 GB RSS.
- Beam front `beam_z_max_m = 0.049` at step 3000 (expected 0.048): the beam enters the column.
- `beam_in_core = true`, fill fraction 0.25, local `eta_net = 0.187` in the beam-occupied core.
- Seed electrons: total weight 9.69e9 → 2.92e9 (-70 %) by step 3000 (28 ns).
- Timing run `runs/es_timing_full_grid/` (64x64x512, 300 steps): 1.1 s/step.

## 4. Limitations and open issues

- **Seeded model loses its electrons.** It loads electrons only (ions get a 1 m^-3 placeholder density
  when `initial_ion_fraction = 0`). Before the beam arrives nothing confines them, so most leave before
  the beam reaches them (local eta 0.19 vs seeded 0.83). Options: seed ions too; start the seed when the
  beam has filled the column; or pre-fill the domain with beam at t = 0. Not changed here.
- `run_scan.py` passes only gas, pressure, steps, beam energy/current, diagnostics and the method flag.
  It does not pass solver, grid, `nppc` or `cfl` from the matrix files, so `--solver es` is not yet
  available through `run_full_production.sh`.
- The ES solver drops electromagnetic effects (none needed at 30 keV, beta = 0.008), and the
  gyration limit assumes the 0.15 T solenoid; a stronger field needs a smaller dt.
- Seeded and callback ES runs are not yet compared with EM over a common time window.
- Global eta compares all particles in the domain; it is large while the beam fills the domain
  (e.g. 1.6 at step 3000 of the test), which is expected.
- Existing `results/*/neutralization_from_particle_number.csv` files were written with the wrong
  columns; re-run `postprocess_case.py` to regenerate them.
- The beam-front slice has a tiny `n_p`, which gives a large local eta there (46 at z = 0.049 m in the
  test) and slightly biases the core average while the beam is still filling the column.
