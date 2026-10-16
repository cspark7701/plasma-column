# Execution Plan Summary: Step Selection Options for run_full_production.sh

**Task Index**: 91  
**Date**: 2026-10-16  
**Subject**: Add `--start_step`, `--skip_sim` and `--skip_step` to `scripts/run_full_production.sh` so
finished simulations are not rerun (needed before launching `pressure_scan`).

---

## 1. Motivation

- Each 10000-step case takes about 5.5–8 h and ~85 GB with `--snapshots 80`.
- Steps 3/3b always rerun `cases/baseline_{h2,kr}.yaml`. That run is the same for every matrix:
  `results/method_scan/seeded_H2_baseline/warpx_used_inputs` is byte-identical to
  `results/method_comparison/seeded_H2_1e-5Torr/warpx_used_inputs` (Kr: same for `seeded_Kr_1e-6Torr`).
- The script had no way to skip a step, so redoing analysis meant rerunning every simulation.

## 2. Changes

`scripts/run_full_production.sh`:

1. New options (step labels `1 2 3 3b 4 4b 5 5b 6 6b 7 7b 8`):
   - `--start_step <S>`: skip steps before `S`.
   - `--skip_sim`: skip steps `2`, `3`, `3b`.
   - `--skip_step <S[,S...]>`: skip listed steps; may be repeated.
   Unknown labels exit with an error. The banner prints `Steps Run`; skipped steps print `[SKIPPED]`.
2. Step 4/4b baseline directory is now the first existing one of `<out_dir>/seeded_<gas>_baseline`,
   `results/method_scan/seeded_<gas>_baseline`, `results/seeded_<gas>_baseline`,
   `runs/seeded_<gas>_baseline`, `<out_dir>`/`results` `seeded_H2_1e-5Torr` or `seeded_Kr_1e-6Torr`.
   Previously H2 had no fallback to the matrix case, so skipping step 3 in `pressure_scan` would have
   postprocessed a missing directory.

`docs/full_production_pipeline.md`: new "Step selection" subsection with examples.

A method_comparison pipeline was running from this script during the edit. The new version was written
to a separate file and moved into place with `mv`, so the running `bash` process kept reading the old
(now unlinked) file through its open descriptor (`/proc/<pid>/fd/255 -> ... (deleted)`).

## 3. Verification

- `bash -n scripts/run_full_production.sh` → OK.
- `dry-run pressure_scan --skip_step 3,3b --skip_step 5,5b,6,6b,7,7b` (output and logs in a scratch
  directory) → `Steps Run: 1 2 4 4b 8`, exit 0; step 4/4b used `results/method_scan/seeded_{H2,Kr}_baseline`.
- `--skip_sim --start_step 8` → `Steps Run: 8`.
- `--start_step 9` and `--skip_step 3c` → error message, exit 1.

## 4. Usage

```bash
bash scripts/run_full_production.sh high pressure_scan --max_steps 10000 --snapshots 10 --skip_step 3,3b
bash scripts/run_full_production.sh high method_comparison --skip_sim
```

Skipping individual finished matrix cases needs no new option. With `--resume` (the pipeline default
unless `--fresh` is given), `run_scan.py` skips a case whose `reducedfiles/particle_number.txt`
already reaches `max_steps` and only reruns `postprocess_case.py`. Tested with a one-case matrix whose
`reducedfiles/` was copied from `results/method_comparison/seeded_H2_1e-5Torr` → "already completed
10000 steps. Skipping simulation."

The `pressure_scan` cases at 1e-6/1e-5 Torr launch the same WarpX run as the `method_comparison` cases
of the same name: `run_scan.py` passes only gas, pressure, steps, beam energy/current and diagnostic
periods, plus `--neutralization -1` for the seeded method. The matrix-level `plasma:` block
(`neutralization: 0.5`, ...) is not passed, although it is written to `config.yaml`/`metadata.json`.

## 5. Limitations

- When step 3 is skipped, step 4 writes its postprocessing CSV/JSON files into the reused directory
  (e.g. `results/method_scan/seeded_H2_baseline/`), replacing the ones already there.
- Step selection does not check that the skipped simulations actually finished; step 4 runs on
  whatever the chosen directory contains.
- Steps 5–7 read their own default inputs and are not matrix-specific; this task does not change that.
- Open issue, not fixed here: every `diagnostics_summary.json` checked (method_scan seeded/cxx,
  method_comparison seeded) reports `np_core_avg = 0.0` and `eta_net_local ~ 1e45`, including runs
  that never had `.old` plotfiles. The local-neutralization path in `postprocess_case.py`
  (`load_plotfile_densities` / `compute_local_core_neutralization`) needs fixing; rerunning
  postprocessing on other copies of the data does not change the result.
