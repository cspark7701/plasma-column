# 61 — RT-13: Implement $z$-Dependent Neutralization in Axial Injection Envelope Model

**Date:** 2026-08-18  
**Task file:** `docs/04_refactor_tasks/RT-13_z_dependent_neutralization_envelope.md`

---

## Summary

Refactored [`compute_beam_envelope`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/injection_line.py) to support region-dependent space-charge perveance $K_{\text{eff}}(z)$, cleanly distinguishing between neutralization within the compact neutralizer cell ($0 \le z \le L_{\text{cell}}$) and downstream drift/matching optics in high vacuum ($z > L_{\text{cell}}$). Added support for arbitrary functional perveance profiles `keff_func(z)`.

## Changes Made

### `src/plasma_column/injection_line.py`
- Extended `compute_beam_envelope` signature with:
  - `eta_cell: Optional[float] = None`
  - `eta_downstream: float = 0.0`
  - `keff_func: Optional[Callable[[float], float]] = None`
  - `eta_net: Optional[float] = None` (preserved for backwards compatibility).
- Implemented $z$-dependent perveance evaluator:
  $$K_{\text{eff}}(z) = \begin{cases} K_0 (1 - \eta_{\text{cell}}), & z \le L_{\text{cell}} \\ K_0 (1 - \eta_{\text{downstream}}), & z > L_{\text{cell}} \end{cases}$$
- Coupled $K_{\text{eff}}(z)$ dynamically inside the RK45 integration ODE.

### `tests/test_injection_line.py`
- Added unit test `test_envelope_cell_only_vs_uniform_neutralization` verifying that:
  - Inside the cell ($z \le 0.20\text{ m}$), cell-only and uniform envelopes match.
  - At the inflector entrance ($z = 1.12\text{ m}$), $R_{x,\text{unif}} < R_{x,\text{cell}} < R_{x,\text{vac}}$.
- Added unit test `test_envelope_custom_keff_func` verifying arbitrary callable perveance profiles.

## Acceptance Criteria — All Met

- [x] `compute_beam_envelope()` supports `eta_cell`, `eta_downstream`, and `keff_func`.
- [x] Cell-only neutralization produces realistic intermediate downstream expansion.
- [x] Full backwards compatibility preserved for legacy calls passing `eta_net`.
- [x] `pytest -q tests/test_injection_line.py` passes (6/6).
- [x] Full test suite `pytest -q` passes (94/94).
- [x] `python scripts/audit_repo.py --root .` passes all checks.

## Physics Limitations

The model uses 2D transverse envelope equations ($R_x, R_y$) with continuous beam perveance $K_{\text{eff}}(z)$. Longitudinal bunching effects can be evaluated using peak-bunch perveance scaling ($K_{\text{eff,peak}} / K_{0,\text{peak}} \approx 1 - \eta_{\text{avg}} / B_f$).
