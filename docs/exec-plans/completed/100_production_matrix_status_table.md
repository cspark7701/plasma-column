# Execution Plan Summary: Production Matrix Status Table

**Task Index**: 100  
**Date**: 2026-10-22  
**Subject**: Markdown table of all production cases with method, gas, pressure, stages and an
empty status column, for tracking runs on the other machines.

---

## 1. Repository State

`main` @ `bc773d0`, clean working tree.

## 2. Changes

- **New** `docs/production_matrix.md`, generated from `cases/production.yaml`:
  - Cases table: 15 rows (#, case, method, gas, pressure, stages, blank status), in matrix order.
    The matrix has 12 seeded, 2 C++ MCC and 1 vacuum case.
  - Stage table: A_method_scan (4), B_method_comparison (7), C_pressure_scan (12).
  - Common settings from the matrix `defaults`: beam, B_z, grid, solver, steps, nppc, diagnostics.
  - Notes on method interpretation:
    - Seeded η is imposed.
    - `cxx_mcc_custom` cases run built-in electron-impact MCC on a seeded plasma, not the custom
      proton-impact extension, even though the YAML labels them `full_self_consistent_cxx_mcc`.
    - Callback, bunched and verification cases are not in the matrix.
  - Commands copied from `docs/full_production_pipeline.md` § "Production matrix (task 97)".
- `docs/full_production_pipeline.md`: link to the new table.

## 3. Verification

- Parsed `cases/production.yaml`: 15 unique case names. Every stage member is a defined case, and
  every case belongs to at least one stage.
- Table rows, stage counts and totals were generated from the parsed YAML, not typed by hand.

## 4. Note

The document is a snapshot of the matrix at `bc773d0`. If `cases/production.yaml` changes,
update the table (the Status column is edited by hand).
