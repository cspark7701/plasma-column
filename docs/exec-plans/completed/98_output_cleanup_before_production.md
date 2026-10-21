# Execution Plan Summary: Cleanup of runs/ and results/ Before Production

**Task Index**: 98  
**Date**: 2026-10-20  
**Subject**: After the accelerated H2 run (task 96) and the MCC check (task 97) finished, remove the test
and superseded EM outputs. Keep their small evidence, and move the two finished full-grid runs into
`results/production/` (cases/production.yaml). Deletion approved by the user. Both directories are
git-ignored, so this commit holds only this summary.

Repository state at start: `main` with the task-97 changes uncommitted.

---

## 1. Actions

- Small evidence was copied to `results/validation/` (82 MB): CSV, JSON, PNG/PDF, logs, reducedfiles and
  warpx_used_inputs. Plotfiles and checkpoints were excluded.
  - From `runs/`: callback_es_check, callback_es_check_fixed, es_small_test, es_smoke,
    es_timing_full_grid, mcc_es_check, solver_cmp.
  - The superseded EM matrix results: `em_legacy_method_scan/`, `em_legacy_method_comparison/`.
  - The two run_case logs of the full-grid runs.
- Moved into `results/production/`:
  - `results/es_check/seeded_H2_baseline` → `seeded_H2_1e-5Torr`. Its original metadata is kept;
    `case_config.case_name` is `seeded_H2_baseline`.
  - `results/es_check/callback_H2_accel_x1000_rescaled` → same name. It is not part of
    `production.yaml`, and the stage summaries ignore it.
- Deleted:
  - `runs/*` listed above;
  - `results/method_scan/` and `results/method_comparison/` (old EM results);
  - `results/es_check/`;
  - 23 dry-run stub folders in `results/` (config.yaml + metadata.json only, checked before removal).
- Untouched: `results/delete.sh`, `plots/` (git status clean).
- Disk use went from 625 GB to 565 GB.

## 2. Verification

- `ls runs` is empty. `results/` holds `delete.sh`, `production/` (2 runs, 16 GB) and `validation/`
  (82 MB). No plotfile or checkpoint folders are left under `results/validation/`.
- `run_scan.py --matrix cases/production.yaml --dry_run --output_dir results/production` validates
  15 cases and leaves `seeded_H2_1e-5Torr/metadata.json` byte-identical. The 14 stub folders the dry
  run created were removed by name after their content was checked.
- `postprocess_stages.py --stage A_method_scan --dry_run` reports `seeded_H2_1e-5Torr` complete
  (local eta_net 0.958).

## 3. Notes

- `results/validation/` is the only remaining record of the ES smoke test, the EM vs ES comparison, the
  callback checks, the MCC check and the old EM matrices. Their plotfiles cannot be regenerated without
  rerunning.
- Production (task 97 §4) is not launched.
