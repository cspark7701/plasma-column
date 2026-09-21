# Execution Plan Summary: Fix Proton-Impact Cross-Section File Resolution & Repository Fallback

**Task Index**: 81  
**Date**: 2026-09-22  
**Subject**: Resolve `FileNotFoundError` during matrix runs (`seeded_H2_1e-6Torr`) by adding automatic repository-bundled cross-section fallback in `plasma_column_mcc_picmi_v7.py` and `plasma_column_callback_source_picmi_v3.py`.

---

## 1. Problem Diagnosis

During execution of matrix scans or production pipelines containing gas-loaded simulation cases (`seeded_H2_1e-6Torr`):
- `vacuum_reference` completed successfully because it operates in pure vacuum without background gas.
- The next case, `seeded_H2_1e-6Torr`, failed with:
  ```text
  FileNotFoundError: Cross-section data file not found: /home/cspark/Work/simulation_codes-working/warpx-data/MCC_cross_sections/H2/proton_impact_ionization.dat
  ```
- **Root Cause**: Upstream `warpx-data` only provides electron impact tables for `H`, `He`, `Ar`, and `Xe`. The proton-impact cross section tables for $\text{H}_2$ and $\text{Kr}$ (`proton_impact_ionization.dat`) are generated and tracked directly inside the repository under `warpx_proton_impact_cross_sections_linear/MCC_cross_sections/`.
- However, `get_cross_section_dir()` in [`scripts/plasma_column_mcc_picmi_v7.py`](file:///home/cspark/Work/projects/plasma-column/scripts/plasma_column_mcc_picmi_v7.py) and `load_cross_section()` in [`scripts/plasma_column_callback_source_picmi_v3.py`](file:///home/cspark/Work/projects/plasma-column/scripts/plasma_column_callback_source_picmi_v3.py) were strictly searching `<warpx_data_dir>/MCC_cross_sections/<gas>` without falling back to the repository's own bundled cross-section database.

---

## 2. Changes Implemented

1. **[`scripts/plasma_column_mcc_picmi_v7.py`](file:///home/cspark/Work/projects/plasma-column/scripts/plasma_column_mcc_picmi_v7.py)**:
   - Updated `get_cross_section_dir(cfg)` to check:
     1. User-specified `cfg.h2_cross_section_dir` (if $\text{H}_2$).
     2. `<warpx_data_dir>/MCC_cross_sections/<gas>`.
     3. Fallback to `CrossSectionDatabase` from `plasma_column.gas` (`warpx_proton_impact_cross_sections_linear/MCC_cross_sections/<gas>`).
     4. Direct repository path fallback relative to script location.
   - Updated `validate_cross_section_files(cfg)` and the `charge_exchange` collision registration to fall back to `warpx_data_dir/MCC_cross_sections/H/Hion_on_H2_charge_exchange.dat` if `Hion_on_H2_charge_exchange.dat` is not under `xsec_dir`.

2. **[`scripts/plasma_column_callback_source_picmi_v3.py`](file:///home/cspark/Work/projects/plasma-column/scripts/plasma_column_callback_source_picmi_v3.py)**:
   - Updated `load_cross_section(cfg)` with fallback to `CrossSectionDatabase` and bundled linear cross-section tables in the repository.

3. **[`tests/test_gas_cross_sections.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_gas_cross_sections.py)**:
   - Updated `test_mcc_script_interp_sigma_matches_gas_db()` to assert cross-section presence and interpolation agreement for both $\text{H}_2$ and $\text{Kr}$ without conditional skipping.
   - Added `test_callback_script_load_cross_section()` to verify callback cross-section loader for both $\text{H}_2$ and $\text{Kr}$.

---

## 3. Verification

1. **Isolated Execution Test**:
   - Ran `python3 scripts/plasma_column_mcc_picmi_v7.py` with `--gas H2 --pressure_torr 1e-6 --neutralization -1 --run` on 5 steps.
   - Verified WarpX initialized cleanly, loaded proton-impact cross section $\sigma = 1.613 \times 10^{-20}\text{ m}^2$, evolved particles, and finished with exit code 0.
2. **Pre-Push CI Validation**:
   - Ran `bash scripts/check_github_actions.sh --fast`:
     - Python bytecode compilation (`compileall`): PASS
     - Pytest suite: 122 passed, 1 skipped (0 failures).
