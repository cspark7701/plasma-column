# 64 — RT-16: Enhance `plot_beam_envelope_transport` for $(R_x, R_y)$ with Beamline Element Schematic

**Date:** 2026-08-18  
**Task file:** `docs/04_refactor_tasks/RT-16_envelope_rx_ry_beamline_schematic.md`

---

## Summary

Refactored [`plot_beam_envelope_transport`](file:///home/cspark/Work/projects/plasma_column/src/plasma_column/plotting/transport.py) to support 2D transverse envelope tracking ($R_x(z)$ horizontal and $R_y(z)$ vertical) and added an automated top beamline element schematic overlay illustrating the physical layout of the axial injection matching section.

## Changes Made

### `src/plasma_column/plotting/transport.py`
- Updated `plot_beam_envelope_transport` to accept DataFrames with `(z, Rx, Ry)` or `(z, r)`, as well as tuples `(z, Rx, Ry)` and `(z, r)`.
- Rendered separate horizontal $R_x(z)$ (solid) and vertical $R_y(z)$ (dashed) envelope curves.
- Added top schematic canvas (`show_elements=True`) drawing colored bounding boxes for:
  - Plasma Neutralizer Cell ($0 \le z \le 20\text{ cm}$)
  - Main Solenoid ($30 \le z \le 55\text{ cm}$)
  - Quadrupole Q1 ($65 \le z \le 77\text{ cm}$)
  - Quadrupole Q2 ($85 \le z \le 97\text{ cm}$)
  - Spiral Inflector entrance marker ($z = 112\text{ cm}$)
- Plotted the inflector aperture limit reference line ($r_{\text{ap}} = 5.0\text{ mm}$).

### `tests/test_plotting.py`
- Added unit test `test_plot_beam_envelope_transport_2d_and_schematic` verifying both DataFrame and tuple input formats with and without element schematics.

## Acceptance Criteria — All Met

- [x] Renders $(R_x, R_y)$ curves cleanly.
- [x] Element layout schematic overlay drawn with accurate bounding boxes.
- [x] Dual format export (`.png` and `.pdf`) verified.
- [x] `pytest -q tests/test_plotting.py` passes (4/4).
- [x] Full test suite `pytest -q` passes (98/98).
- [x] `python scripts/audit_repo.py --root .` passes all checks.

## Physics Limitations

None. Visualization and matching envelope representation.
