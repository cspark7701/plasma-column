# Execution Plan Summary: Paper Preparation Task List

**Task Index**: 90  
**Date**: 2026-10-09  
**Subject**: Write the task list for closing the `\pending` items in
`paper/manuscript/plasma_column_prab.tex` once the production simulations (running on other
machines) are complete. The task files themselves are not tracked by git.

---

## 1. Changes

- `.gitignore`: added `docs/05_paper_prepare_tasks/` (next to the existing `docs/00_…`–`docs/04_…`
  task folders). Confirmed with `git check-ignore -v`.
- Created (untracked) `docs/05_paper_prepare_tasks/` with a README index and 12 task files:

| ID | Task | Needs simulation data |
|---|---|---|
| PP-00 | Data intake, inventory, WarpX build/patch provenance, AGENTS physics checks, v2 dataset freeze | Yes |
| PP-01 | Rudd-model σ_i vs Rudd et al. 1983 measurements; uncertainty band | No |
| PP-02 | PIC convergence (grid, nppc, Δt); EM vs ES solver justification | Yes |
| PP-03 | Execute the 7 custom proton-impact MCC verification tests | Yes |
| PP-04 | Local η_local,net(t) and K_eff/K0 for H2/Kr by model level and confinement | Yes |
| PP-05 | Electron confinement time vs B_z and electrode bias; test η_ss ≈ τ_c/τ_ion | Yes |
| PP-06 | Bunched beam: RF-average vs peak η, gap losses, Eq. 8 and 53 mT estimate | Yes |
| PP-07 | Beam quality at cell exit; corrected transport to inflector; transmission | Yes |
| PP-08 | Charge-exchange loss and keV-valid scattering for H2 and Kr | Partly |
| PP-09 | Retire hard-coded tables and synthetic figures; fix Kr-pressure claim | No |
| PP-10 | Data-driven `results_numbers.tex`, result figures and tables from frozen data | Yes |
| PP-11 | Remove all `\pending`, finalize text, references, author block, build | Yes |

PP-01 and PP-09 can run before the simulation data arrive.

## 2. Notes

- Each task names the manuscript section it closes, the expected run matrix, physics cautions
  (seeded η is imposed; PIC runs cover ≤ 5e-4 of τ_ion; local vs global η; bunched-beam reporting),
  steps, outputs and acceptance criteria.
- All file paths cited in the tasks were checked to exist. The website (`docs/site/index.html`)
  was checked and does not contain the Kr-equivalence claim, so PP-09 lists only three files.

## 3. Verification

- `git status --short` shows only `.gitignore` modified; no task file is tracked.
- All README links in the task folder resolve.
- No code changed; tests not affected.
