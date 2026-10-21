# Execution Plan Summary: Combined Production Matrix, Stage Postprocessing, MCC Check

**Task Index**: 97  
**Date**: 2026-10-20  
**Subject**: Replace the three overlapping production matrices with one matrix (`cases/production.yaml`).
Every physical run is done once in `results/production/`, and postprocessing splits the results into
stages A–C. Also: protect run records from dry runs and run the short C++/MCC small-grid check. The cleanup of
`runs/` and `results/` is task 98. Production is not launched in this task.

Repository state at start: `main` at `45aeb40` (task 96), clean.

---

## 1. Changes

- `cases/production.yaml` (new): 15 cases, each physical run once.
  - Stage A (`A_method_scan`), 4 runs: seeded and cxx_mcc for H2 at 1e-5 Torr and Kr at 1e-6 Torr.
  - Stage B (`B_method_comparison`), 7 runs: stage A plus `vacuum_reference`, seeded H2 at 1e-6 Torr and
    seeded Kr at 1e-5 Torr.
  - Stage C (`C_pressure_scan`), 12 runs: seeded H2 and seeded Kr at 1e-6, 3e-6, 1e-5, 3e-5, 1e-4 and
    3e-4 Torr.
  - Numerics are the task-94 production ES settings: 64x64x512, 23000 steps, nppc_beam 4,
    nppc_plasma 16.
  - Each case records what its runner actually passes: seeded `neutralization -1`, `mcc: none`;
    cxx_mcc `mcc: electron_impact`; vacuum `neutralization 0`, `nppc_plasma 0`.
  - Cases are ordered so stage A finishes first, then the runs B adds, then the runs C adds.
- `src/plasma_column/schema.py`: `ScanMatrixConfig.stages`, which is parsed and validated (no duplicate
  case names, no empty stages, no unknown members), plus `stage_cases(stage)`.
- `src/plasma_column/warpx_io.py`: `has_simulation_output()` and `write_case_records()`.
  `config.yaml`/`metadata.json` in a folder that already has simulation output are replaced only when a
  simulation is launched; the previous metadata is kept as `metadata.prev.json`.
- `scripts/run_case.py`, `scripts/run_scan.py`: write records through `write_case_records`.
  - A dry run no longer overwrites the records of finished runs.
  - A `--resume` skip writes nothing.
- `scripts/postprocess_stages.py` (new): collects each case (missing / incomplete / complete, final
  global counts, local core values from `diagnostics_summary.json`, rescaling label). Writes
  `results/production/stage_<stage>/stage_summary.{csv,json}`, `local_eta_by_case.{png,pdf}` and
  `eta_vs_pressure.{png,pdf}`. Supports `--stage`, `--no_plots` and `--dry_run`.
- `scripts/run_full_production.sh`: new `production` target (menu option 5). For it, step 4 runs
  `postprocess_stages.py`, and the old per-matrix comparison steps 3/3b/4b are skipped.
- The old matrices (`method_scan_baseline.yaml`, `method_comparison.yaml`, `pressure_scan_h2_kr.yaml`)
  are marked SUPERSEDED in their headers.
- Docs: `docs/full_production_pipeline.md` has a new "Production matrix (task 97)" subsection. Exec-plan
  96 §3 now has the accelerated-run results.
- Tests:
  - `test_production_matrix_stages_and_records` (tests/test_case_files.py);
  - stage order, unknown-member and duplicate-name tests (tests/test_schema.py);
  - `tests/test_case_records.py`: records protected, records written for a new folder, stage
    `collect_case` status.

## 2. Verification

- `pytest -q`: 152 passed, 1 skipped. `bash -n scripts/run_full_production.sh` passes.
- `bash scripts/run_full_production.sh dry-run production --skip_step 5,5b,6,6b,7,7b,8` (scratch
  output and log dirs) passes.
  - Steps 5–7 regenerate repository figures even in a dry run, so they were skipped.
- The driver command for production `seeded_H2_1e-5Torr` is identical to the task-94 run's
  (`cases/baseline_h2.yaml`), so that run was moved into the production folder instead of being rerun.
- After the cleanup (task 98), `run_scan.py --matrix cases/production.yaml --dry_run --output_dir results/production`
  validates all 15 cases.
  - It left the moved run's `metadata.json` byte-identical: "existing simulation output, records left
    unchanged".
  - The dry run created 14 two-file stub folders; they were removed afterwards.
- `postprocess_stages.py --stage A_method_scan --dry_run` reports `seeded_H2_1e-5Torr` complete
  (step 23000, local eta_net 0.958) and the other three missing.

## 3. C++/MCC small-grid check

Settings: 32x32x256, ES, 3000 steps (28.4 ns), nppc_beam 4, nppc_plasma 4, seeded plasma
(`--neutralization -1`), `scripts/plasma_column_mcc_picmi_v7.py`. The H2 reference is the task-95 ES
run with the same settings (`runs/solver_cmp/es`).

| run | Np | Ne | Ni | core eta_e | core eta_net | wall time |
|---|---:|---:|---:|---:|---:|---:|
| seeded H2 1e-5 (reference) | 1.7744e9 | 9.5251e9 | 9.6619e9 | 1.476 | 0.446 | 5:20 |
| MCC H2 1e-5 | 1.7750e9 | 9.5307e9 | 9.6589e9 | 1.457 | 0.432 | 5:30 |
| seeded Kr 1e-6 (reference) | 1.7742e9 | 7.7814e9 | 7.9053e9 | 1.250 | 0.327 | 5:38 |
| MCC Kr 1e-6 | 1.7738e9 | 7.7763e9 | 7.8771e9 | 1.246 | 0.322 | 5:37 |

- All runs and their postprocessing exit with 0. MCC is set up for `plasma_electrons`. H2 uses the
  atomic-H electron-impact table as a fallback (13.6 eV vs 15.4 eV threshold; noted in task 95).
- The MCC runs do not gain ions relative to the seeded references (Ni is −0.03 % for H2 and −0.4 % for
  Kr; the differences are statistical).
  - The expected electron-impact yield is at most n_g·σ·v·t ≲ 1e-4 per electron over the window (zero for
    electrons below the threshold).
    So at 1e-6–1e-5 Torr, MCC adds no measurable ionization within the simulated time, and the WarpX
    log reports ionization probability 0.000000 per step.
- Consequence for production: at these pressures, the stage-A cxx_mcc cases are expected to reproduce
  the seeded cases within noise, each at about 9 h. They remain in the matrix as the method comparison
  defined by the plan; dropping them is a user decision.
- WarpX built-in MCC models electron impact only. Proton-impact ionization is not modeled by it (see
  AGENTS.md).

## 4. Production launch (not executed, waiting for user approval)

```bash
bash scripts/run_full_production.sh medium production --snapshots 10 --resume
```

- `--resume` skips `seeded_H2_1e-5Torr` (complete at 23000 steps) and postprocesses it again.
- 14 runs remain, at about 9 h each on 8 cores (about 5.3 days sequential), and about 8 GB each.

## 5. Limitations

- `local_neutralization_vs_t.csv` from `postprocess_case` contains domain-wide ParticleNumber ratios
  despite the `_local` column names. The local `core_averages` and the stage summaries do not use it.
  Not changed in this task.
- Stage summaries take local values from the last snapshot only.
- Seeded results are an analytic/data-driven source model, not self-consistent proton-impact
  ionization.
