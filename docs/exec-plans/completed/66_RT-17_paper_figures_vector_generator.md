# 66 — RT-17: Implement Publication Vector Figure Generators in `paper_figures.py`

**Date:** 2026-08-18  
**Task file:** `docs/04_refactor_tasks/RT-17_paper_figures_vector_generator.md`

---

## Summary

Implemented complete publication-grade vector figure generators (`generate_fig01` through `generate_fig05`) in [`src/plasma_column/plotting/paper_figures.py`](file:///home/cspark/Work/projects/plasma_column/src/plasma_column/plotting/paper_figures.py).

## Changes Made

### `src/plasma_column/plotting/paper_figures.py`
- Implemented:
  1. `generate_fig01_axial_injection_concept`: Multi-panel schematic diagram with scaled beamline layout blocks (Buncher -> Neutralizer -> Solenoid -> Q1 -> Q2 -> Inflector) and synchronized magnetic field profiles ($B_z(z)$ and $G(z)$).
  2. `generate_fig02_plasma_neutralizer_module`: Mechanical and plasma cross-section with differential pumping restriction apertures, gas inflow, beam core, and vacuum exhaust ports.
  3. `generate_fig03_cross_sections`: Dual-panel comparison of proton-impact cross sections ($H_2$ vs. $Kr$) from $10\text{--}100\text{ keV}$ and ionization buildup timescales $\tau_{\text{ion}}$ vs. pressure.
  4. `generate_fig04_neutralization_evolution`: Dual-panel comparison of $\eta(t)$ and $K_{\text{eff}}/K_0(t)$ across simulation methods (seeded, callback, uncompensated).
  5. `generate_fig05_inflector_phase_space`: Transverse phase space distributions $(x, x')$ and $(y, y')$ at the spiral inflector entrance with 1-$\sigma$ RMS ellipses and inflector acceptance ellipse boundary ($r_{\text{ap}} = 5\text{ mm}$, $\theta_{\text{ap}} = 25\text{ mrad}$).

### `src/plasma_column/plotting/__init__.py`
- Re-exported all 5 figure generators in `__all__`.

### `tests/test_plotting.py`
- Added `test_paper_figure_generators` verifying that all 5 figure functions produce valid, non-empty `.png` and vector `.pdf` files.

## Acceptance Criteria — All Met

- [x] All 5 paper figure functions produce rich vector graphics with labels, dimensions, and legends.
- [x] Both `.png` and `.pdf` files are output cleanly.
- [x] `pytest -q tests/test_plotting.py` passes (5/5).
- [x] Full test suite `pytest -q` passes (101/101, 0 warnings).
- [x] `python scripts/audit_repo.py --root .` passes all checks.

## Physics Limitations

None. Vector visualization routines adhering to the project's baseline geometry constraints.
