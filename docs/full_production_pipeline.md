# Full Production & Analysis Pipeline Guide

This document describes the design, execution, parallel scaling, and 1-to-1 notebook mapping of the **Full Production Simulation & Analysis Pipeline** for the Plasma Column Neutralizer study.

---

## 1. Overview & Objectives

The production pipeline automates the end-to-end simulation, post-processing, figure generation, summary table compilation, dataset freezing, and downstream optics transport analysis in a single reproducible command or notebook.

Key goals:
- **Reproducibility**: Automatic metadata tracking (`metadata.json`, git commit hash, WarpX patch diff).
- **Parallel Core Utilization**: Automatically detects system hardware and allocates **~90% of available CPU cores**.
- **Token Conservation**: Default quiet output mode redirects verbose logs to `logs/` to prevent terminal flooding and token exhaustion during automated execution.
- **1-to-1 Notebook Mirror**: A consolidated Jupyter notebook ([`notebooks/nb_full_production_pipeline.ipynb`](file:///home/cspark/Work/projects/plasma_column/notebooks/nb_full_production_pipeline.ipynb)) mirrors every shell step.

---

## 2. Command Line Usage & Options

Run the full production pipeline directly from the repository root:

```bash
# Standard quiet execution (recommended for CLI / automated prompts)
bash scripts/run_full_production.sh

# Dry-run mode (validates all configurations, creates directories, writes metadata)
bash scripts/run_full_production.sh --dry_run

# Verbose mode (prints all execution logs directly to screen)
bash scripts/run_full_production.sh --verbose

# Custom CPU core percentage allocation (e.g. 75%)
bash scripts/run_full_production.sh --cpu-pct 75
```

Alternatively, use the root executable wrapper:
```bash
./run_full_production.sh --dry_run
```

---

## 3. Parallel Execution & CPU Scaling (~90% Allocation)

The script computes target OpenMP and numerical worker threads based on detected hardware cores:

```bash
TOTAL_CORES=$(nproc)
TARGET_CORES=$(( TOTAL_CORES * 90 / 100 ))
```

Environment variables set automatically:
- `OMP_NUM_THREADS=$TARGET_CORES`
- `OPENMP_NUM_THREADS=$TARGET_CORES`
- `MKL_NUM_THREADS=$TARGET_CORES`
- `NUMEXPR_NUM_THREADS=$TARGET_CORES`

This maximizes multi-threaded efficiency across PIC grid solves and field diagnostics while preserving headroom for OS responsiveness.

---

## 4. Token Conservation & Quiet Log Redirection

When running in quiet mode (default), each step redirects stdout and stderr to isolated log files under `logs/`:

| Step Number | Step Description | Output Log File |
| :--- | :--- | :--- |
| **Step 1** | Environment & Repository Audit | `logs/step_1_8.log` |
| **Step 2** | Matrix Scan Setup & Parameter Validation | `logs/step_2_8.log` |
| **Step 3** | Baseline Case Verification | `logs/step_3_8.log` |
| **Step 4** | Post-Processing & Core Neutralization | `logs/step_4_8.log` |
| **Step 5** | Publication Figures & Cross-Section Plots | `logs/step_5_8.log` |
| **Step 6** | Paper Summary Tables & Dataset Freezing | `logs/step_6_8.log` |
| **Step 7** | RF-Bunched Beam & Downstream Transport | `logs/step_7_8.log` |
| **Step 8** | Repository Integrity Audit | `logs/step_8_8.log` |

This prevents long terminal outputs from consuming context tokens during AI pair programming sessions.

---

## 5. Step-by-Step Execution Workflow (1-to-1 Mapping)

| Pipeline Step | Shell Execution (`run_full_production.sh`) | Notebook Cell (`nb_full_production_pipeline.ipynb`) |
| :--- | :--- | :--- |
| **1. Audit** | `python scripts/print_environment.py` | Section 1: Environment & Repository Audit |
| **2. Scan Setup** | `python scripts/run_scan.py --matrix cases/method_comparison.yaml` | Section 2: Matrix Case Configuration |
| **3. Baseline Run** | `python scripts/run_case.py --case cases/baseline_h2.yaml` | Section 3: Baseline Case Execution |
| **4. Post-Process**| `python scripts/postprocess_case.py --case-dir results/seeded_H2_baseline` | Section 4: Diagnostics & Core Neutralization |
| **5. Figures** | `python scripts/make_plots.py` & `make_paper_figures.py` | Section 5: Publication Figure Generation |
| **6. Tables** | `python scripts/make_paper_tables.py` & `freeze_publication_dataset.py` | Section 6: Paper Summary Tables |
| **7. Transport** | `python scripts/analyze_bunched_beam_neutralization.py` & `transport_to_inflector.py` | Section 7: Bunched Beam & Transport Optics |
| **8. Verification**| `python scripts/audit_repo.py --root .` | Section 8: Final Repository Verification |
