# Execution Plan Summary: Simulation Strategies and Storage Optimization Documentation (`docs/simulation_strategies.md`)

**Task Index**: 79  
**Date**: 2026-09-04  
**Subject**: Document simulation parameter defaults, root causes of excessive disk consumption, and storage-optimized configuration strategies in `docs/simulation_strategies.md`.

---

## 1. Overview of Work

Created [`docs/simulation_strategies.md`](file:///home/cspark/Work/projects/plasma-column/docs/simulation_strategies.md) containing:
1. **Root Cause Analysis of Disk Footprint**:
   - Analysis of full 3D `FieldDiagnostic` dumps (11 arrays per dump $\approx 180$ MB each, totaling $>36$ GB for 200 dumps per case and $>320$ GB across matrices).
   - High-frequency particle phase-space dumps and AMReX checkpoints ($10 \times 2.5$ GB $\approx 25$ GB).
   - Comparison with lightweight reduced diagnostics (`particle_number.txt` $<10$ MB total).
2. **Table 1: Current Default Parameters by Case**:
   - Compares grid, step count, particle per cell counts, diagnostic periods, checkpoint intervals, and estimated per-case disk footprints.
3. **Table 2: Recommended Parameters for Production & Disk-Constrained Runs**:
   - Recommends increasing `diag_period` to 5,000–10,000 for seeded runs and 20,000 for MCC runs (cutting 3D plotfile volume by 95–98%).
   - Recommends increasing `checkpoint_period` or disabling intermediate checkpoints (`checkpoint_period: 0`) for clean production runs.
4. **Table 3: Case-by-Case Recommendations**:
   - Specific parameter guidelines for `vacuum.yaml`, `baseline_h2.yaml`, `baseline_kr.yaml`, `bunched_h2.yaml`, `bunched_kr.yaml`, `method_comparison.yaml`, and `pressure_scan_h2_kr.yaml`.
5. **Mitigation Actions**:
   - Preserves reduced diagnostics (`reduced_diag_period: 50`) so all publication curves ($\eta(t)$, $K_{\text{eff}}/K_0$) remain untouched while keeping total storage under 15–25 GB.

---

## 2. Verification

- Verified [`docs/simulation_strategies.md`](file:///home/cspark/Work/projects/plasma-column/docs/simulation_strategies.md) markdown tables and formatting.
- Cleaned up temporary files (`tmp.md`).
- Executed unit test suite under the project conda environment (`121 passed, 1 skipped`).
