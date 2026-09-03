# Execution Plan Summary: Production Run Issues Documentation

**Task Index**: 69  
**Date**: 2026-09-03  
**Subject**: Analysis and Documentation of Full Production Simulation Errors (yt extraction warning and WarpX MCC assertion failure)

---

## 1. Summary of Work

Documented the root cause analysis and mitigation paths for two issues identified from the full production simulation run logs:

1. **`yt` 3D Density Grid Extraction Warning (`callback_Kr_dynamic`)**:
   - WarpX field diagnostics in `plasma_column_callback_source_picmi_v3.py` and `plasma_column_mcc_picmi_v7.py` record aggregate field arrays (`E`, `B`, `J`, `rho`, `part_per_cell`), but omit per-species charge densities (`rho_<species>`).
   - As a result, `load_plotfile_densities()` fails to match per-species density fields (`ne_3d`, `np_3d`, `ni_3d`) and safely falls back to domain-wide particle counts with clear warnings.

2. **WarpX MCC Assertion Failure (`cxx_H2_mcc_or_custom`, exit code 6)**:
   - WarpX checks `assert(getCrossSection(m_energy_penalty) == 0)` in `ScatteringProcess.cpp:71`.
   - The H atomic electron-impact ionization fallback data file starts at 13.598 eV, whereas `gas_ionization_energy_eV(cfg)` was set to 15.43 eV (H2 molecular ionization potential). At 15.43 eV, the cross-section is already non-zero (~9.82e-22 m^2), triggering the SIGABRT.

---

## 2. Artifact Created

- Created detailed markdown report: [`docs/notes/production_run_issues_2026-09-02.md`](file:///home/cspark/Work/projects/plasma-column/docs/notes/production_run_issues_2026-09-02.md)

---

## 3. Verification

- Repository audit and pytest suites remain clean and passing.
