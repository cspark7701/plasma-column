# Execution Plan Summary: CW1 Result on the Production Grid

**Task Index**: 111  
**Date**: 2026-11-15  
**Subject**: Task CW1 of `docs/physics_notes/simulation_strategy_tasks.md`. Finish, analyze and
document the best cell configuration (0.15 T, 1 eV seed, -300 V / 10 mm plugs) at production
resolution, launched in task 110.

Repository state at start: `main` at `f84439b`; CW1 restart fix in the tree.

---

## 1. Run history

- 2026-10-28 02:53–12:19 KST: steps 0–34,306 on 24 threads; stopped by request after checkpoint
  `chk034296`.
- 2026-11-14 12:00: scheduled restart (systemd user timer) failed: the service had no
  `LD_LIBRARY_PATH` for `libamrex_3d.so` (pywarpx reports it as "Dimensionality '3d' was not
  compiled"). Relaunch from the login shell failed: relative checkpoint path after the driver's
  chdir. Relaunched 12:04 with an absolute path, 22 threads on CPUs 0-10,12-22.
- Finished 2026-11-15 05:38 at step 102,890 (975 ns) instead of 68,594: PICMI `step()` runs
  `max_steps` more steps after a restart. Reduced diagnostics were appended across the restart
  (continuous from step 0). Total ~27 h, 30 GB output (git-ignored).

## 2. Changes

- `scripts/plasma_column_mcc_picmi_v7.py`: `checkpoint_step()` reads the step from a `chkNNNNNN`
  name; on restart the driver runs `max_steps - checkpoint step`, so `--max_steps` is the total.
- `scripts/run_cw_best_config.py`: passes the checkpoint as an absolute path.
- `tests/test_restart_steps.py` (2 tests).
- Docs: "Task CW1 result" in `neutralizer_efficiency_strategy.md`; CW1 done in
  `simulation_strategy_tasks.md`; confinement row of `production_matrix.md`.

## 3. Results

Analysis: `analyze_confinement_scan.py` and `analyze_beam_quality.py --scan_dir
results/cw_best_config` (outputs in `results/cw_best_config/analysis/`).

| Quantity | 227 ns | 650 ns | 975 ns |
|---|---|---|---|
| N_e in the cell / N_e(0) | 0.97 | 0.87 | 0.81 |
| N_i in the cell / N_i(0) | 0.98 | 0.65 | 0.52 |
| Beam-core eta_net | 0.27 (transient) | 0.81 | 0.93 |

- Core eta_net rings for ~400 ns (0.27–1.7), then 0.91 on average (0.81–1.00) from 490 to 975 ns.
- tau_c = 4.2 us (2-sigma lower bound 4.1, last quarter 3.9); eta_ss >= 0.05.
- Beam x_rms / x'_rms along z (last snapshot): 1.0 mm at injection, 1.7 mm / 15 mrad at the cell
  entrance, 4.7 mm / 21 mrad at the cell end. In the task 107 domain (injection 2 cm before the
  cell, no plugs) the beam stays at 1.0–1.7 mm, <= 5 mrad. The divergence comes from the
  uncompensated drift before the cell (rms space-charge growth sigma'' ~ K/(4 sigma), about
  0.3 /m at 1 mm) and the upstream plug (+10 mrad at the entrance in the plug scan).

## 4. Verification

- `pytest -q`: 181 passed, 1 skipped.
- Particle counts continuous across the restart; core-eta figure checked visually.

## 5. Limitations

- Seeded plasma (analytic source estimate) decaying from t = 0; no proton-impact source, so the
  ~1 us core eta is the seed, not a sustained column.
- Single case; plug cost from the small-grid scan (task 109).
- Core eta is defined in the beam core; with the beam at 5–7 mm rms the core holds a small part of
  the beam.
