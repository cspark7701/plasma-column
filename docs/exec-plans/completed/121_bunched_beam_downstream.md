# Execution Plan Summary: Strongly Bunched Beam in the Solenoid and Quadrupole Section

**Task Index**: 121  
**Date**: 2026-11-16  
**Subject**: Task B4 of `docs/physics_notes/simulation_strategy_tasks.md`. Do residual-gas
electrons follow a strongly bunched beam downstream (f_pe vs f_RF), i.e. which compensation limit
of tasks 117/118 applies?

Repository state at start of the runs: `main` at `72ff151` (B4 launched 2026-11-15 14:55 on the
cores freed by B2); code committed with CW3 in `1652a80`.

---

## 1. Changes

- No new code: `scripts/run_line_section.py --group b4 --parallel 2 --cores 4 --core_offset 6`
  (cases fields_Bf3, fields_Bf5p7), analysis with `scripts/analyze_line_section.py --scan_dir
  results/line_section_bunched` and `scripts/analyze_bunched_cell.py --scan_dir
  results/line_section_bunched --z_start 0.12`. Outputs in `results/line_section_bunched/`
  (git-ignored).
- Docs: "Task B4 result" in `neutralizer_efficiency_strategy.md`, B4 done (and B5 note) in
  `simulation_strategy_tasks.md`, bunched-downstream row of `docs/production_matrix.md`.

## 2. Results

- Main solenoid: tau_c 0.22 us (B_f 3) and 0.11 us (B_f 5.7) vs 2.4 us DC (CW3); other regions
  0.1–0.5 us.
- eta_avg / eta_peak: 0.07 / 0.04 (B_f 3), -0.91 / -0.21 (B_f 5.7); static-cloud prediction
  0.03 / -0.21: electrons do not follow the bunches.
- B_cell measured 2.4 and 4.3 (input 3 and 5.7; the bunches spread in the section).

## 3. Verification

- Both cases exit 0 (2026-11-16 12:00 and 12:58; 0.53 s/step alone, 0.78 s/step while CW3 ran).
  Analysis code tested in tasks 119 and 120.

## 4. Limitations

- Seeded plasma (analytic source estimate), small grid, no plugs, 650 ns; density bunching at
  constant velocity; large snapshot fluctuations (std 0.1–0.5 in eta).
