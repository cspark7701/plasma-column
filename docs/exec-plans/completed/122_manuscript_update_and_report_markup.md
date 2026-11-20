# Execution Plan Summary: Manuscript Update and Consolidated-Report Markup

**Task Index**: 122  
**Date**: 2026-11-20  
**Subject**: Mark up the consolidated report against the current results (tasks 96–121), and
update the journal manuscript and proceedings drafts with the confinement, transport and
bunched-beam studies.

Repository state at start: `main` at `f134b13`, clean.

---

## 1. Changes

- New `scripts/make_manuscript_study_results.py` (`--dry_run`, `--from_frozen`). It freezes 19
  study summaries from `results/` into `paper/manuscript/study_data/` (108 KB, tracked) with
  `provenance.json`. It writes 129 `\numst...` macros to `paper/manuscript/numbers_studies.tex` and
  makes figs. 9–11 (confinement times, transmission vs eta_down, bunched-beam gain; figures are
  git-ignored and rebuilt by the script).
- `paper/manuscript/plasma_column_prab.tex`:
  - abstract and conclusion rewritten;
  - new methods subsection "Confinement, transport and bunching models";
  - new results subsections "Electron confinement in the cell" (with the steady-state bracket
    eta_ss ~0.05 to ~1), "Transport to the inflector" and "Bunched beam"; the old "Still
    required" list is removed;
  - discussion: "Downstream compensation" paragraph, buncher alternative-placement note, and
    updated limitations.
  - Remaining `\pending`: tau_c convergence (task 123), proton-impact MCC validation, cross-section
    uncertainty, charge exchange and scattering, funding.
- `docs/consolidated_report/plasma_column_consolidated_report.tex` (+ rebuilt PDF): markup with
  `\old{}` (struck red), `\new{}` (blue) and boxed notes. It marks:
  - the self-consistent C++ MCC claim (not validated, not used);
  - the Kr-at-1e-6-Torr equivalence (equal rate needs 1.8e-6 Torr; seeded Kr eta 0.50–0.58);
  - T > 98 % (it depends on downstream compensation);
  - K0 = 6.43e-4 (the formula gives 1.25e-3);
  - eta_ss = 0.90–0.95 (it is set by tau_c);
  - B_f = 360/dphi (uniform bunch only);
  - the main-solenoid/quadrupole values and the transmission formula;
  - the typed-in results table, which gets a new current-results table and new main findings.
- `paper/plasma_column_journal_outline.md`, `docs/proceedings/jacow_outline.md`,
  `docs/proceedings/introduction_draft.tex`: the wrong Kr-advantage and C++ MCC claims are
  replaced, and the confinement, transport and bunching results are added.

## 2. Verification

- `python scripts/make_manuscript_study_results.py --dry_run` and a full run, then `--from_frozen`.
  The macros were checked against the documented results of tasks 107–121. The CW1 window uses the
  second half of the run (487–975 ns), as `analyze_confinement` does, which gives the documented
  0.91.
- The manuscript (12 pages) and the report (9 pages) build with latexmk with no undefined
  references. The JACoW draft compiles with pdflatex.
- `pytest -q`: 210 passed, 1 skipped.

## 3. Usage

```bash
python scripts/make_manuscript_study_results.py               # after re-running a study
python scripts/make_manuscript_study_results.py --from_frozen # figures/macros from study_data/
cd paper/manuscript && latexmk -pdf plasma_column_prab.tex
```

## 4. Limitations

- The report markup types the current numbers by hand, with task references. The manuscript takes
  them only from the frozen data.
- `paper/tables/*.csv` still hold the typed-in values found in task 88 (PP-09); the manuscript does
  not use them.
- The manuscript conclusions stay provisional until the tau_c convergence study (task 123).
