# Execution Plan Summary: Production Matrix Status and Results

**Task Index**: 102  
**Date**: 2026-10-26  
**Subject**: Production (task 97 §4) finished. `docs/production_matrix.md` now records each case's
status, run window and final beam-core neutralization.

Repository state at start: `main` at `381e0d5`. `plots/axial_injection_layout.{png,pdf}` were modified
by pipeline steps 5–8 and are not part of this task.

---

## 1. Production run

- `bash scripts/run_full_production.sh medium production --snapshots 10 --resume --output_dir
  results/production --log_dir results/production/logs`, launched 2026-10-21 09:47 KST.
  - `seeded_H2_1e-5Torr` (task 94 run) was skipped by `--resume`. The other 14 cases each ran 23000
    steps in 8.3–9.4 h on 8 cores. The last case finished 2026-10-26 13:03 KST.
  - Steps 1–8 succeeded. Stage summaries are in `results/production/stage_{A_method_scan,
    B_method_comparison,C_pressure_scan}/`.
- `results/production/` is 126 GB (not in git).

## 2. Document changes

- `docs/production_matrix.md`:
  - Status column set to `done` for all 15 cases, and the intro states the completion time.
  - New "Results" section with the run window, local η_e, local η_net, local K_eff/K0 and global η_net
    per case, taken from the stage summaries.
  - Short observations: seeded vs C++ MCC agree; H2 rises to 0.96 by 1e-5 Torr; Kr stays flat at
    0.50–0.58 with η_e ≈ 2 and a slightly negative global η_net (not yet analyzed).
  - Model limitations: seeded source, DC beam, peak-bunch caveat.

## 3. Verification

- Values were checked against `stage_summary.csv`. Run windows come from each case's `metadata.json`
  (start) and its `reducedfiles/particle_number.txt` (last write).
- `bash scripts/md_to_pdf.sh docs/production_matrix.md` was not run: `pandoc` is not on the PATH of
  this shell.

## 4. Open items

- The flat Kr trend and the negative Kr global η_net need analysis (radial profiles, ion retention).
- Review and commit or revert the pipeline's changes to `plots/axial_injection_layout.{png,pdf}`.
