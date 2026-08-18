# 62 — RT-14: Implement Gas Target Scattering and Mean Free Path Calculations

**Date:** 2026-08-18  
**Task file:** `docs/04_refactor_tasks/RT-14_gas_scattering_and_mean_free_path.md`

---

## Summary

Implemented analytical models for proton-gas target interactions in [`src/plasma_column/gas.py`](file:///home/cspark/Work/projects/plasma_column/src/plasma_column/gas.py):
1. Collision mean free path $\lambda_{\text{mfp}} = 1 / (n_{\text{gas}} \sigma)$.
2. Beam transmission fraction $T = \exp(-n_{\text{gas}} \sigma_{\text{loss}} L)$.
3. Highland / Lynch-Dahl Multiple Coulomb Scattering (MCS) RMS projected angle $\theta_0$ across neutral $H_2$ and $Kr$ gas columns.

Added physical radiation length mass density constants for $H_2$ and $Kr$ to [`src/plasma_column/constants.py`](file:///home/cspark/Work/projects/plasma_column/src/plasma_column/constants.py).

## Changes Made

### `src/plasma_column/constants.py`
- Added:
  - `RADIATION_LENGTH_H2 = 630.5  # kg/m^2 (63.05 g/cm^2)`
  - `RADIATION_LENGTH_KR = 353.4  # kg/m^2 (35.34 g/cm^2)`

### `src/plasma_column/gas.py`
- Implemented:
  - `mean_free_path_m(n_gas_m3, sigma_m2) -> float`
  - `transmission_fraction(n_gas_m3, sigma_loss_m2, length_m) -> float`
  - `multiple_scattering_rms_rad(energy_keV, gas_species, pressure_torr, length_m, temperature_K=300.0) -> float`

### `tests/test_gas_cross_sections.py`
- Added unit tests:
  - `test_mean_free_path_and_transmission`: checks $\lambda \approx 194\text{ m}$ and transmission $T > 99.8\%$ for $10^{-5}\text{ Torr } H_2$.
  - `test_multiple_coulomb_scattering`: validates that 30 keV protons in $10^{-5}\text{ Torr } H_2$ / $10^{-6}\text{ Torr } Kr$ experience negligible angular scattering ($\theta_0 < 0.2\text{ mrad} \ll 1\text{ mrad}$).

## Acceptance Criteria — All Met

- [x] `mean_free_path_m`, `multiple_scattering_rms_rad`, and `transmission_fraction` implemented in `gas.py`.
- [x] Validated that at baseline parameters ($30\text{ keV}$, $10^{-5}\text{ Torr } H_2$, $L=0.20\text{ m}$), $\theta_0 \approx 0.13\text{ mrad}$ and $T > 99.8\%$.
- [x] `pytest -q tests/test_gas_cross_sections.py` passes (7/7).
- [x] Full test suite `pytest -q` passes (96/96).
- [x] `python scripts/audit_repo.py --root .` passes all checks.

## Physics Limitations

The multiple scattering calculation employs the standard Highland / Lynch-Dahl parametrization for homogeneous gas targets. For bunched beams with strong space charge, space-charge forces typically dominate over multiple scattering at $p \le 10^{-5}\text{ Torr}$.
