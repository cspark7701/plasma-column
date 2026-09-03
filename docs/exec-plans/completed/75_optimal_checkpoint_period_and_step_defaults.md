# Execution Plan Summary: Set Optimal Checkpoint Period and Max Step Defaults

**Task Index**: 75  
**Date**: 2026-09-03  
**Subject**: Apply recommended `checkpoint_period` and `max_steps` defaults per simulation method across YAML configurations, schema models, and runner scripts.

---

## 1. Overview of Work

Applied optimal default settings based on runtime characteristics:

| Simulation Method | `max_steps` | `checkpoint_period` | Rationale |
| :--- | :---: | :---: | :--- |
| **`seeded_compensation`** / **`vacuum`** | `20000` | `2000` | Fast execution; dumps ~10 checkpoints across 2.7 beam transits with negligible I/O impact. |
| **`python_callback`** / **`cxx_mcc_custom`** | `120000` | `10000` | Heavy dynamic pair injection / Monte Carlo tracking; dumps 12 checkpoints across 16.2 beam transits (checkpoint every ~15–20 mins). |

### Code & Config Updates:
1. **Runner Scripts**:
   - [`scripts/plasma_column_mcc_picmi_v7.py`](file:///home/cspark/Work/projects/plasma-column/scripts/plasma_column_mcc_picmi_v7.py): Updated default `checkpoint_period` in `PlasmaColumnConfig` to `2000` (matching `max_steps=20000`).
   - [`scripts/plasma_column_callback_source_picmi_v3.py`](file:///home/cspark/Work/projects/plasma-column/scripts/plasma_column_callback_source_picmi_v3.py): Updated default `checkpoint_period` in `Config` to `10000` (matching `max_steps=120000`).
2. **Schema & API (`src/plasma_column/schema.py`)**:
   - Added `get_default_numerics_for_method(method) -> (max_steps, checkpoint_period)`.
   - Updated `SimulationCaseConfig.from_dict()` to automatically populate recommended `max_steps` and `checkpoint_period` defaults if omitted in YAML/dictionary definitions.
   - Added alias recognition for `cxx_mcc` and `mcc` pointing to `cxx_mcc_custom`.
3. **YAML Configuration Files**:
   - Added `checkpoint_period: 2000` to defaults in:
     - [`cases/baseline_h2.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/baseline_h2.yaml)
     - [`cases/baseline_kr.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/baseline_kr.yaml)
     - [`cases/vacuum.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/vacuum.yaml)
     - [`cases/bunched_h2.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/bunched_h2.yaml)
     - [`cases/bunched_kr.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/bunched_kr.yaml)
     - [`cases/pressure_scan_h2_kr.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/pressure_scan_h2_kr.yaml)
     - [`cases/method_scan_baseline.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/method_scan_baseline.yaml)
     - [`cases/method_comparison.yaml`](file:///home/cspark/Work/projects/plasma-column/cases/method_comparison.yaml)
   - Added explicit `checkpoint_period: 10000` per-case overrides for all dynamic callback and C++ MCC cases in `method_comparison.yaml` and `method_scan_baseline.yaml`.
4. **Production Shell Script**:
   - Updated [`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/plasma-column/scripts/run_full_production.sh) startup banner to reflect per-case defaults (`2k seeded/vacuum, 10k callback/MCC`).

---

## 2. Verification

- All 25 unit tests in [`tests/test_schema.py`](file:///home/cspark/Work/projects/plasma-column/tests/test_schema.py) passed cleanly with 0 warnings.
- Full repository audit (`python3 scripts/audit_repo.py --root .`) passed cleanly with all 105 tests passing.
