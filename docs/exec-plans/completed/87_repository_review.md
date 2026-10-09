# Execution Plan Summary: Repository Review and README Fixes

**Task Index**: 87  
**Date**: 2026-10-09  
**Subject**: Full repository review against `AGENTS.md` and `README.md`; fix the README problems found.

---

## 1. Repository State at Start

```text
branch : main (clean working tree)
HEAD   : 1f74b9d  setup.sh hardware auto-detection
tracked: 293 files; 86 prior task summaries in docs/exec-plans/completed/
WarpX  : /home/cspark/Work/simulation_codes-working/warpx @ 6c04a74dc (dirty, 5 modified files)
env    : warpx-dev (miniforge3)
```

## 2. Checks Executed

| Check | Result |
|---|---|
| `python -m pytest -q` | 122 passed, 1 skipped |
| `python scripts/audit_repo.py --root .` | Audit completed successfully |
| `python scripts/run_case.py --case cases/vacuum.yaml --dry_run` | Success; output in `results/vacuum_reference/` (git-ignored) |
| `git -C <warpx> diff` vs `docs/warpx_patches/warpx_plasma_column_current.patch` | **Differ** (~390 diff lines) |
| `docs/warpx_patches/IonImpactIonization.H` vs live WarpX copy | Identical |

## 3. Findings

### 3.1 WarpX patch provenance mismatch (high priority, open)

- The live WarpX tree is on `6c04a74dc`; its modified C++ files were last edited 2026-09-01.
- The tracked patch was regenerated on 2026-09-26 (task 84) against a different WarpX base, `6b32fecc7`.
- The live diff and the tracked patch therefore differ. Any MCC binary built from the live tree is
  most likely built from the **older** version of the C++ changes and cannot be recreated from the
  tracked patch. This violates `AGENTS.md` rules 7 and 9 for production MCC runs.
- The live tree's `.gitignore` excludes `IonImpactIonization.H`, so `git diff` and the WarpX
  "dirty" flag in run metadata do not show that file.
- **Recommended fix**: either rebuild WarpX from `6b32fecc7` plus the tracked patch, or save the live
  diff as a second, clearly labelled patch. Extend `warpx_io` metadata to record SHA-256 hashes of
  the patched source files, not only WarpX commit + dirty flag.

### 3.2 Overstated validation wording (open outside README)

- `docs/verification/custom_ion_impact_mcc_validation.md` states that its tests are **analytical
  targets** and that the modified C++ kernel has not yet been run against them.
- `docs/warpx_customization.md` §6 describes the same tests as "Verified ...", which overstates
  their status. Not changed in this task.

### 3.3 README problems (fixed in this task)

1. Duplicate section number "5"; sections are now numbered 1–13.
2. Five absolute `file:///home/cspark/...` links replaced with repository-relative links.
   26 further `file:///` links remain in `docs/*.md` (not changed in this task).
3. Repository-structure tree was incomplete. Added: `INSTALL.md`, `setup.sh`, packaging files,
   CI workflow, `cases/verification/`, extra case files, `docs/` subfolders (`consolidated_report/`,
   `development/`, `publication/`, `site/`, `verification/`, `warpx_patches/`), `paper/`,
   `notebooks/runs/nb_parameter_scan.ipynb`, the two PICMI drivers, MCC verification and paper
   scripts, `run_matrix.py`, `hardware.py`, and `warpx_proton_impact_cross_sections_linear/`.
4. §12 "WarpX Source Customization" claimed "Self-consistent proton-impact ionization" without
   caveat. Rewritten to state that upstream WarpX MCC impact ionization targets electron impact,
   that the custom extension is not yet validated as a self-consistent PIC model, that
   seeded/callback runs are analytic/data-driven source estimates, and that the WarpX build must be
   checked against the tracked patch.

### 3.4 Housekeeping (open, low priority)

- Ignored clutter in the project root: `archives/` (84 MB), `__pycache__/`, empty `command/`.
- `scripts/_gen_notebooks.py` regenerates all notebooks and will overwrite hand edits.
- CI (`.github/workflows/ci.yml`) runs `compileall src scripts .`; `.` already covers the other two.

## 4. Files Changed

- `README.md`
- `docs/exec-plans/completed/87_repository_review.md` (this file)

## 5. Verification

- `grep -n "file:///" README.md` returns nothing.
- Section headers in `README.md` are numbered 1–13 with no duplicates.
- All README link targets exist in the repository.
- `python -m pytest -q` and `python scripts/audit_repo.py --root .` re-run after the edit (see §2).

## 6. Physics Limitations Restated

- Proton-impact MCC through the custom WarpX extension is not yet benchmarked in PIC; results from
  it must not be called self-consistent validated PIC until §3.1 and §3.2 are resolved.
- Seeded and callback results are analytic/data-driven source estimates.
- Global `ParticleNumber` ratios do not establish local beam-core neutralization, and average
  neutralization overstates peak-bunch compensation (`K_eff,peak/K0,peak ≈ 1 − η_avg/B_f`).
