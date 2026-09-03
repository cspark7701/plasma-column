# Execution Plan Summary: Fix Issue 2 - Electron-Impact MCC Ionization Threshold Alignment

**Task Index**: 71  
**Date**: 2026-09-03  
**Subject**: Resolve WarpX SIGABRT assertion crash `(getCrossSection(m_energy_penalty) == 0)` for electron-impact MCC collisions in H2

---

## 1. Problem Description

When running `cxx_H2_mcc_or_custom` (or any run with `--gas H2 --mcc electron_impact`), WarpX aborted immediately at initialization with:

```text
Assertion `(getCrossSection(m_exe_h.m_energy_penalty) == 0)' failed,
file "/home/cspark/Work/simulation_codes-working/warpx/Source/Particles/Collision/ScatteringProcess.cpp", line 71,
Msg: ### ERROR   : Cross-section > 0 at energy cost for collision.
SIGABRT
Abort(6) on node 0
```

### Root Cause
WarpX enforces `WARPX_ALWAYS_ASSERT_WITH_MESSAGE((getCrossSection(m_exe_h.m_energy_penalty) == 0), ...)` to prevent resulting in negative kinetic energies after collision.
For $\text{H}_2$, the fallback electron-impact ionization cross section (`warpx-data/MCC_cross_sections/H/electron_impact_ionization.dat`) starts at $13.59844\text{ eV}$ with $\sigma = 0.0$.
However, [`scripts/plasma_column_mcc_picmi_v7.py`](file:///home/cspark/Work/projects/plasma-column/scripts/plasma_column_mcc_picmi_v7.py) passed a hardcoded $15.43\text{ eV}$ (molecular $\text{H}_2$ potential) as `energy_penalty`. At $15.43\text{ eV}$, $\sigma \approx 9.82 \times 10^{-22}\text{ m}^2 \ne 0$, violating the assertion.

---

## 2. Solution Implemented

1. **Adaptive Zero-Crossing Detection**:
   In [`scripts/plasma_column_mcc_picmi_v7.py`](file:///home/cspark/Work/projects/plasma-column/scripts/plasma_column_mcc_picmi_v7.py):
   - Modified `gas_ionization_energy_eV(cfg, cross_section_file=...)` to inspect the cross-section data file.
   - Determines the exact zero-crossing energy entry ($13.59844\text{ eV}$ for the fallback file, or $15.43\text{ eV}$ if an exact $\text{H}_2$ cross-section table is supplied).
   - Passed `cross_section_file=eion_file` when setting up `electron_scattering_processes["ionization"]["energy"]`.

---

## 3. Verification

1. **WarpX Execution Test**:
   - Ran `python3 scripts/plasma_column_mcc_picmi_v7.py --gas H2 --mcc electron_impact --max_steps 1 --run --cores 1`.
   - Result: Exit code 0, initialization and AMReX/WarpX PIC step completed cleanly with no SIGABRT.
2. **Matrix Scan Dry-Run**:
   - Ran `python3 scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run`.
   - Result: All 9 cases validated and metadata generated under `results/`.
3. **Repository Audit & Tests**:
   - `python3 scripts/audit_repo.py --root .` passed (102 tests passed, 0 errors).
