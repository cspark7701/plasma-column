# Execution Plan Summary: Remove pandas `inplace` Deprecation Warnings

**Task Index**: 125  
**Date**: 2026-11-22  
**Subject**: Resolve the 44 warnings reported by `pytest -q`.

---

## 1. Repository State

`main` @ `aef4b96`, clean working tree.

## 2. Cause

All 44 warnings were `Pandas4Warning` from pandas 3.1.1. pandas deprecates the `inplace` keyword
(PDEP-8) and will remove it in a future version. Five calls in
`src/plasma_column/diagnostics.py` (`read_particle_number`) used it:

| Line | Call |
|---|---|
| 171, 173 | `df.rename(columns=..., inplace=True)` (step/time column names) |
| 210–212 | `drop_duplicates`, `sort_values`, `reset_index` with `inplace=True` (restart dedup) |

They fired once per `ParticleNumber` file read, in `test_dataloader.py`,
`test_diagnostics_particle_number.py`, `test_case_records.py` and
`test_local_neutralization_masks.py`. No other file in the repository uses `inplace=True`.

## 3. Change

Each call now reassigns `df`. The dedup chain is
`df.drop_duplicates(subset=["step"], keep="last").sort_values(by="step").reset_index(drop=True)`.
The result is the same: the last row per step is kept, sorted by step, with a fresh index.

## 4. Verification

- `pytest -q`: 210 passed, 1 skipped, **0 warnings** (was 44).
- `pytest -q -W error`: only 3 tests fail, all on the intentional `UserWarning` that global
  particle-number ratios do not prove local core neutralization. `pyproject.toml` filters that
  warning on purpose (AGENTS.md physics caution), and `-W error` overrides the filter. No other
  warning is hidden.

No physics or numerical behavior changed.
