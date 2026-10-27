# Execution Plan Summary: CW1 Launch on the Production Grid

**Task Index**: 110  
**Date**: 2026-10-28  
**Subject**: Task CW1 of `docs/physics_notes/simulation_strategy_tasks.md`. Run the best cell
configuration from the confinement and plug scans (tasks 107, 109) at production resolution.

Repository state at start: `main` at `39ae9f1`, with the uncommitted CW1 runner.

---

## 1. Changes

- `scripts/run_cw_best_config.py` (new, `--dry_run`): one case at production numerics (ES solver,
  production dt, nppc_beam 4, nppc_plasma 16, electron-impact MCC on H2), 64x64x672 over
  x,y +-10 mm and z [-0.07, 0.27] m (production dz = 0.51 mm), 650 ns (68,594 steps), checkpoints
  every quarter, `--restart_from` to extend toward ~2 us. Refuses plug widths that the domain
  cannot hold (injection must be >= 4 widths outside the upstream plug centre).
- `scripts/run_confinement_scan.py`: `run_case` on a restart appends to `run.log` and writes
  `metadata_restart.json`, keeping the original log and metadata.
- `simulation_strategy_tasks.md`: CW1 running.

## 2. Launch

- Configuration: B_z = 0.15 T, seed T_e = 1 eV, seeded H2 1e-5 Torr (analytic source estimate),
  DC 10 mA, -300 V analytic end plugs, w = 10 mm, centres 30 mm outside the cell ends.
- Started 2026-10-28 02:53 KST on 24 OpenMP threads (no other job running); 0.79 s/step at
  step 300, so about 15–20 h.
- Output `results/cw_best_config/B0p15_Te1_V300_w10mm/` (git-ignored). Analysis when finished:
  `analyze_confinement_scan.py --scan_dir results/cw_best_config` and
  `analyze_beam_quality.py --scan_dir results/cw_best_config`.

## 3. Verification

- `pytest -q`: 179 passed, 1 skipped. Dry runs for 10 mm (command printed) and 20 mm plugs
  (refused: needs zmin <= -0.14 m).
- Run stepping, first checkpoint and plotfile written.

## 4. Limitations

- Single case: no same-grid no-plug reference; the comparison with no plugs comes from the C4
  small-grid scan (task 109).
- The beam is injected 70 mm before the cell (vs 20 mm in production runs), so it enters the cell
  larger than in the 218 ns production matrix; compare core eta with that in mind.
- Plugs are an analytic potential (valid for r << w), not electrode surfaces.
