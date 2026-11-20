# Execution Plan Summary: Launch of the PIC Convergence Study of the Electron Confinement Time

**Task Index**: 123  
**Date**: 2026-11-20  
**Subject**: Task C6 of `docs/physics_notes/simulation_strategy_tasks.md`. Is the PIC confinement
time numerical? PIC gives tau_c = 4.2 us on the production grid (task 111) and 7.2 us on the
plug-scan grid (task 109). Test electrons in the same static trap survive 100 us (task 114).

Repository state at launch: `main` at `538375c`, clean apart from the new launcher.

---

## 1. Changes

- New `scripts/run_tauc_convergence.py` (`--dry_run`, `--group small|large`). The physics is as in
  CW1: seeded H2 at 1e-5 Torr, 0.15 T, 1 eV seed, 300 V / 10 mm plugs, DC 10 mA, ES FFT,
  z in [-0.07, 0.27] m, 650 ns. Each case changes one numerical parameter:

  | Case | Grid | nppc_plasma | dt | e-MCC |
  |---|---|---|---|---|
  | g32_p4 | 32x32x336 | 4 | 9.48 ps | on |
  | g32_p16 | 32x32x336 | 16 | 9.48 ps | on |
  | g32_p64 | 32x32x336 | 64 | 9.48 ps | on |
  | g32_p16_dt2 | 32x32x336 | 16 | 4.74 ps | on |
  | g32_p4_nomcc | 32x32x336 | 4 | 9.48 ps | off (plug-scan numerics) |
  | g48_p16 | 48x48x504 | 16 | 9.48 ps | on |
  | g64_p32 | 64x64x672 | 32 | 9.48 ps | on |
  | CW1 (task 111, existing) | 64x64x672 | 16 | 9.48 ps | on |

  Motivation for the grid ladder: the Debye length of the 1 eV seed at the beam density
  (~0.17 mm) is below the cell size (0.31 mm at 64x64, 0.63 mm at 32x32), so grid heating is a
  candidate for the electron loss.
- Docs: C6 row ("running") in `simulation_strategy_tasks.md`. The manuscript refers to this study
  as task 123 in its `\pending{}` notes.

## 2. Launch

- 2026-11-20 09:57 KST, two detached runners (`setsid nohup`), logs in
  `results/tauc_convergence/runner_{small,large}.log` (git-ignored):
  - small: 6 cases, 4 at a time, 4 threads each on CPUs 0-7 and 12-19;
  - large: g64_p32 on CPUs 8-10 and 20-22.
  - CPUs 11 and 23 stay free.
- First-minute cost, while test suites from other projects briefly used most CPUs: g32_p16
  0.68 s/step, g32_p64 1.1, g48_p16 1.9, g32_p16_dt2 0.67 (twice the steps), g64_p32 4.2.
  Estimated wall time: small group about 1.5 days, g64_p32 about 3 days. Checkpoints at half the
  run.

## 3. Analysis plan (result task)

- `python scripts/analyze_confinement_scan.py --scan_dir results/tauc_convergence` gives tau_c over
  325–650 ns. Refit CW1 over the same window.
- tau_c vs cell size and vs nppc. If tau_c grows with resolution toward the test-electron result,
  the PIC loss is numerical and eta_ss is near the well limit. If it is converged, the loss is
  collective, and eta_ss ~ 0.05 at 1e-5 Torr.
- Then update the manuscript steady-state paragraph and conclusions, using
  `make_manuscript_study_results.py` with a frozen convergence table.
