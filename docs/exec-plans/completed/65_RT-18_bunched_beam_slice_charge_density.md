# 65 — RT-18: Add Slice-Dependent Charge Density $\lambda(z)$ and Radial Electric Field $E_r(r,z)$ to `beam.py`

**Date:** 2026-08-18  
**Task file:** `docs/04_refactor_tasks/RT-18_bunched_beam_slice_charge_density.md`

---

## Summary

Implemented longitudinal slice line charge density profiles $\lambda(z)$ (parabolic, Gaussian, and top-hat) and radial space-charge electric field calculations $E_r(r, z)$ on `RFFocusedBeam` in [`src/plasma_column/beam.py`](file:///home/cspark/Work/projects/plasma_column/src/plasma_column/beam.py).

## Changes Made

### `src/plasma_column/beam.py`
- Added properties and methods to `RFFocusedBeam`:
  - `bunch_charge_C`: Total bunch charge $Q_{\text{bunch}} = I_{\text{avg}} / f_{\text{RF}}$.
  - `peak_line_charge_density(profile="parabolic")`: Peak on-axis line charge density $\lambda_0 = \lambda(0)$.
  - `line_charge_density(z, profile="parabolic")`: Slice line charge density $\lambda(z)$ supporting scalar and array inputs.
  - `radial_electric_field(r, z=0.0, profile="parabolic", sigma_r=None)`: Radial space-charge field for Gaussian beam core:
    $$E_r(r, z) = \frac{\lambda(z)}{2 \pi \epsilon_0 r} \left[1 - \exp\left(-\frac{r^2}{2 \sigma_r^2}\right)\right]$$

### `tests/test_bunched_beam.py`
- Added unit tests:
  - `test_bunch_charge_and_conservation`: Verified numerical charge conservation $\int \lambda(z) dz = Q_{\text{bunch}}$ to $<0.01\%$ for parabolic and Gaussian bunch profiles.
  - `test_radial_space_charge_electric_field`: Verified $E_r(0)=0$, linear core behavior, and $1/r$ asymptotic behavior far outside the beam core ($r \gg \sigma_r$).

## Acceptance Criteria — All Met

- [x] Parabolic and Gaussian longitudinal bunch profiles implemented.
- [x] Charge conservation numerically verified.
- [x] Radial space-charge field asymptotics verified.
- [x] `pytest -q tests/test_bunched_beam.py` passes (4/4).
- [x] Full test suite `pytest -q` passes (100/100).
- [x] `python scripts/audit_repo.py --root .` passes all checks.

## Physics Limitations

The 2D radial field expression assumes a locally round Gaussian transverse distribution with slowly varying slice envelope $\partial \sigma_r / \partial z \ll 1$.
