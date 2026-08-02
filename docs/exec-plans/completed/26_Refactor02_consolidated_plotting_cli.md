# Execution Summary: Refactor 02 — Consolidated CLI Entrypoint for Plotting Scripts

- **Date**: 2026-08-02
- **Author**: Chong Shik Park
- **Affiliation**: Department of Accelerator Science and Center for Accelerator Research, Korea University, Sejong, 30019 Republic of Korea
- **Task Source**: User Request — High-Priority Refactoring: Consolidate plotting CLI entrypoints into `scripts/make_plots.py`

## Summary of Accomplishments

1. **Unified CLI Plotting Entrypoint ([`scripts/make_plots.py`](file:///home/cspark/Work/projects/plasma_column/scripts/make_plots.py))**:
   - Unified fragmented plotting CLI flags into a single, cohesive command-line interface with `argparse`:
     - `--all`: Generate all figure categories (synthetic, cross-sections, bunched-beam, paper-figures).
     - `--paper-figures` / `--paper`: Run paper manuscript figure generation pipeline (fig01–fig10) targeting `paper/figures/`.
     - `--cross-sections` / `--cross`: Run H₂ vs Kr proton-impact cross-section comparison plot generators.
     - `--bunched-beam` / `--bunched`: Run RF-bunched beam peak space-charge reduction interpretation plots.
     - `--local-neutralization` / `--local`: Run local 3D spatial neutralization profiles for a case directory (`--case-dir`).
     - `--synthetic`: Run synthetic time-series and parameter scan overview figures.
     - `--dry_run`: Validate figure target definitions and parameters without writing files.
     - `--output_dir`: Specify custom plot output directory (default `plots/`).

2. **Verification & Test Suite**:
   - Tested CLI execution: `python scripts/make_plots.py --help` and `python scripts/make_plots.py --dry_run` -> Verified clean execution and dry-run validation.
   - Compiled codebase: `python -m compileall scripts src tests` -> All scripts compiled cleanly.
   - Executed unit test suite: `pytest -q` -> All 51 unit tests passed in 5.29s.

3. **Deliverables Summary**:
   - [`scripts/make_plots.py`](file:///home/cspark/Work/projects/plasma_column/scripts/make_plots.py)
   - [`docs/exec-plans/completed/26_Refactor02_consolidated_plotting_cli.md`](file:///home/cspark/Work/projects/plasma_column/docs/exec-plans/completed/26_Refactor02_consolidated_plotting_cli.md)
