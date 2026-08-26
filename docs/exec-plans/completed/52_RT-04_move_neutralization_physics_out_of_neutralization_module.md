# 52 — RT-04: Split Physics Helpers Out of `neutralization.py` into `beam.py` / `gas.py`

**Date:** 2026-08-15  
**Task file:** `docs/04_refactor_tasks/RT-04_move_neutralization_physics_out_of_neutralization_module.md`

---

## Summary

Decoupled gas and beam physics helper functions from [`src/plasma_column/neutralization.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/neutralization.py) into their canonical homes in [`src/plasma_column/gas.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/gas.py) and [`src/plasma_column/beam.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/beam.py). Added backward-compatibility aliases with `DeprecationWarning` in `neutralization.py` to allow graceful transition across downstream scripts and notebooks.

## Changes Made

### `src/plasma_column/gas.py`
- Added standalone functions `gas_density_m3(pressure_torr, temperature_K=300.0)` and `ionization_tau_s(n_gas_m3, sigma_m2, beam_speed_m_s)`.

### `src/plasma_column/neutralization.py`
- Focused the module on genuine neutralization-ratio and $\eta$-buildup functions (`neutralization_fraction`, `keff_over_k0_from_eta`, `peak_keff_over_k0_from_average_eta`, `compute_neutralization_ratios`).
- Preserved backward-compatible aliases emitting `DeprecationWarning` for `gas_density_m3`, `proton_beta_gamma_speed`, `ionization_tau_s`, `bunch_length_s`, and `bunch_length_m`, delegating to `gas.py` and `beam.py`.

### Scripts and Tests
- Updated `scripts/run_mcc_verification.py`, `scripts/scan_cross_section_sensitivity.py`, `scripts/make_paper_figures.py`, and `tests/test_basic_physics.py` to import directly from `plasma_column.gas` and `plasma_column.beam`.
- Added deprecation test cases in `tests/test_neutralization.py` and direct unit tests in `tests/test_gas_cross_sections.py`.

## Acceptance Criteria — All Met

- [x] `neutralization.py` exports only genuine neutralization functions along with deprecation aliases.
- [x] `gas.py` exports `ionization_tau_s` and `gas_density_m3`.
- [x] Deprecation warnings are emitted when calling legacy functions in `neutralization.py`.
- [x] `pytest -q` passes without regressions (88/88 passed).
- [x] `python scripts/audit_repo.py --root .` passes clean.

## Physics Limitations

None. Calculations use identical physical formulas and constants across modules.
