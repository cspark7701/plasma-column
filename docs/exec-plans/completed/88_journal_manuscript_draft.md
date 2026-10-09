# Execution Plan Summary: Journal Manuscript Draft

**Task Index**: 88  
**Date**: 2026-10-09  
**Subject**: Locate the missing `paper/*.tex`; resurrect it if deleted, otherwise draft a
journal-submission-quality manuscript.

---

## 1. Search for an Existing Manuscript

| Location searched | Result |
|---|---|
| `git log --all` for any `*.tex` / `paper/*` add or delete | Only `docs/consolidated_report/*.tex` and `docs/proceedings/introduction_draft.tex` ever tracked |
| `git stash list` (1 stash) | Contains only `plots/axial_injection_layout.pdf` |
| Unreachable git blobs (`git fsck --lost-found`) | No LaTeX blob |
| `archives/` and its zip files | No `.tex` |
| Filesystem search for `*plasma*column*.tex` | Only the consolidated report |
| Task 16 / 45 notes | Created only `paper/plasma_column_journal_outline.md` |

**Conclusion**: no manuscript `.tex` ever existed, so nothing was deleted. A new draft was written.

## 2. Problems Found in the Existing `paper/` Material (not changed)

These were found while collecting source material. The new draft does **not** cite any of them.

1. `paper/tables/*.csv` are string literals in `generate_paper_tables()`
   (`src/plasma_column/plotting/paper_figures.py`). None of them is computed:
   - `table_result_summary.csv`: η_net = 0.90/0.95 and 100 % inflector transmission are typed in.
     η_ss = 0.90 is an *input* of the WarpX driver (`steady_state_neutralization`), not an output.
   - `table_validation_summary.csv` marks all 7 MCC tests "PASSED", but
     `docs/verification/custom_ion_impact_mcc_validation.md` states that they are analytical
     targets that have not been run with the C++ kernel.
   - `table_beam_parameters.csv` gives K0 = 1.34e-4; the code gives 1.25e-3.
   - `table_gas_parameters.csv` gives τ_H2 = 0.259 ms and τ_Kr = 0.047 ms; the code gives
     80 µs and 145 µs.
   - `table_simulation_parameters.csv` (32×32×256, dt = 1e-11 s) does not match the driver
     defaults (64×64×512, CFL 0.5, dt ≈ 338 fs).
2. `paper/data/inflector_entrance_summary.csv` gives transmission 0.005–0.011 % and beam radii of
   ~0.5–0.8 m, contradicting the 25 %/100 % in the result table.
3. The phase-space figure in `paper_figures.py` uses `np.random.default_rng(42)` labeled "η = 0.9", and
   `make_paper_figures.py` imports `generate_synthetic_3d_grid` from `plasma_column._testing`.
4. Physics error repeated in `docs/physics_notes/h2_kr_cross_sections.md`,
   `docs/literature/literature_review.md` and the consolidated report: "Kr at 1e-6 Torr gives
   equivalent neutralization to H2 at 1e-5 Torr". Since σ_Kr/σ_H2 = 5.56 < 10, Kr at 1e-6 Torr is
   1.8× *slower*; equal τ needs 1.8e-6 Torr.
5. The consolidated report abstract claims "fully self-consistent C++ MCC" and transmission
   "< 35 % → > 98 %"; neither is supported by repository data.
6. `scripts/plasma_column_mcc_picmi_v7.py` does not use the custom proton-impact MCC at all
   (only electron-impact ionization and H2 charge exchange).
7. Highland multiple-scattering formula is applied at 30 keV, outside its validity range.

## 3. What Was Built

| File | Role |
|---|---|
| `src/plasma_column/design_estimates.py` | Closed-form estimates: perveance, laminar envelope, doubling length, τ_ion, well depth, ion expulsion time, electron crossing/escape, confinement field, bunch time scales, PIC duration from driver defaults |
| `scripts/make_manuscript_figures.py` | Writes 5 figures, `numbers.tex` (58 LaTeX macros) and `manuscript_numbers.json` (with provenance); `--dry_run` supported |
| `paper/manuscript/plasma_column_prab.tex` | PRAB (REVTeX 4.2) draft, 7 pages, 5 figures, 1 table |
| `paper/manuscript/references.bib` | 16 references; 14 confirmed by web lookup (publisher/JACoW/OSTI/arXiv). Not looked up: Reiser 2008 textbook entry; Rudd 1992 author list and Vahedi 1995 page range (volume/year confirmed) |
| `tests/test_design_estimates.py` | 7 tests (kinematics, K0, τ, equal-τ pressure, doubling length vs ODE, scalings, time-scale ordering) |

References from `docs/consolidated_report/references.bib` that could not be verified were not
used (IOTA arXiv:1502.01736 author list, C400/U400R/LBNL cyclotron proceedings, Holmes 1979).

## 4. Key Analytical Results in the Draft

- K0 = 1.25e-3; an uncompensated laminar beam doubles in 8.6 cm and grows 5.1× over 20 cm.
- τ_ion = 80 µs (H2, 1e-5 Torr), 145 µs (Kr, 1e-6 Torr); Kr matches H2 at 1.8e-6 Torr.
- Free longitudinal escape of 10-eV electrons (107 ns) limits cell-local η to ~1e-3.
- Bunch gap 18 ns vs electron crossing 1.1 ns: bunched-beam compensation needs B_z ~ 53 mT or end plugs.
- Static-background peak-bunch bound: K_eff,peak/K0,peak = 0.82 for η_avg = 0.9, B_f = 5.
- PIC runs (6.8 ns seeded, 41 ns dynamic) cover ~5e-4 of τ_H2.
- A 36° bunch at 50 MHz gives B_f = 10 if uniform; B_f = 5 is kept as a parameter.

## 5. Verification

- `python scripts/make_manuscript_figures.py --dry_run` → success; full run writes all outputs.
- `pdflatex`/`bibtex` build: 7 pages, no errors, no undefined references, no overfull boxes.
- `python -m compileall scripts src tests` → OK.
- `python -m pytest -q` → 129 passed, 1 skipped.
- `python scripts/audit_repo.py --root .` → success.

## 6. Outputs

- Tracked: `paper/manuscript/{plasma_column_prab.tex, references.bib, numbers.tex, manuscript_numbers.json}`.
- Generated, git-ignored: `paper/manuscript/figures/*.{pdf,png}`, `plasma_column_prab.pdf`, LaTeX aux files.
- Docs: `docs/publication_workflow.md` §7; README structure tree.

## 7. Open Items (marked `[PENDING]` in the draft)

1. Compare Rudd-model σ at 30 keV with Rudd *et al.* 1983 measurements; uncertainty band.
2. PIC convergence study; electromagnetic vs electrostatic solver justification.
3. Run the custom ion-impact MCC verification with a WarpX build matching the archived patch (see task 87 §3.1).
4. Production PIC: local η(t), confinement time vs B_z/electrode bias, bunched-beam runs, transport to inflector.
5. Charge-exchange loss and screened-Coulomb scattering for H2 and Kr.
6. Fix or retire the hard-coded tables and synthetic figures in §2 above, and correct the Kr pressure claim in the physics notes and consolidated report.
