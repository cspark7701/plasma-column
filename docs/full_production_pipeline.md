# Full Production & Analysis Pipeline Guide

This document describes the design, execution, parallel scaling, and 1-to-1 notebook mapping of the **Full Production Simulation & Analysis Pipeline** for the Plasma Column Neutralizer study.

---

## 1. Overview & Objectives

The production pipeline automates the end-to-end simulation, post-processing, figure generation, summary table compilation, dataset freezing, and downstream optics transport analysis in a single reproducible command or notebook.

Key goals:
- **Reproducibility**: Automatic metadata tracking (`metadata.json`, git commit hash, WarpX patch diff).
- **Parallel Core Utilization**: Automatically detects system hardware and allocates **~90% of available CPU cores**.
- **Token Conservation**: Default quiet output mode redirects verbose logs to `logs/` to prevent terminal flooding and token exhaustion during automated execution.
- **1-to-1 Notebook Mirror**: A consolidated Jupyter notebook ([`notebooks/nb_full_production_pipeline.ipynb`](file:///home/cspark/Work/projects/plasma-column/notebooks/nb_full_production_pipeline.ipynb)) mirrors every shell step.

---

## 2. Command Line Usage & Options

Run the full production pipeline directly from the repository root:

```bash
# Standard quiet execution (defaults: 8 CPU cores, auto-detect GPU)
bash scripts/run_full_production.sh

# Dry-run mode (validates all configurations, creates directories, writes metadata)
bash scripts/run_full_production.sh --dry_run

# Verbose mode (prints all execution logs directly to screen)
bash scripts/run_full_production.sh --verbose

# Custom worker core allocation (default: 8) and explicit GPU device
bash scripts/run_full_production.sh --cores 8 --gpu 0
```

Alternatively, use the root executable wrapper:
```bash
./run_full_production.sh --cores 8 --gpu auto --dry_run
```

---

## 3. Parallel Execution & GPU Hardware Configuration

The runner scripts and notebooks automatically configure CPU threads (OpenMP, MKL, NumExpr) and GPU accelerators:

```bash
# Default cores is 8; auto-detects GPU (defaults to GPU 0 if available)
export OMP_NUM_THREADS=${CORES:-8}
export OPENMP_NUM_THREADS=${CORES:-8}
export MKL_NUM_THREADS=${CORES:-8}
export NUMEXPR_NUM_THREADS=${CORES:-8}

# If NVIDIA GPU detected via nvidia-smi or /dev/nvidia0:
export CUDA_VISIBLE_DEVICES=0
export HIP_VISIBLE_DEVICES=0
```

CLI options available across all scripts (`run_full_production.sh`, `run_case.py`, `run_scan.py`, and simulation scripts):
- `--cores, -c`: Number of CPU threads/cores (default: **8**).
- `--gpu`: GPU device index (e.g. `0`) or `'auto'` (checks GPU availability and defaults to GPU 0 if available; default: **`auto`**).
- `--checkpoint_period <N>`: Period in steps for dumping full AMReX checkpoints (`chk<step>/`).
- `--resume`: Automatically detects existing checkpoints under `results/<case_name>/` and resumes execution.
- `--restart_from <path>`: Path to a specific checkpoint directory to restart from.
- `NUMEXPR_NUM_THREADS=$TARGET_CORES`

This maximizes multi-threaded efficiency across PIC grid solves and field diagnostics while preserving headroom for OS responsiveness.

### Step selection (`run_full_production.sh` only)

Step labels, in order: `1 2 3 3b 4 4b 5 5b 6 6b 7 7b 8`. Skipped steps print `[SKIPPED]`; the
header line `Steps Run` lists what will execute.

- `--start_step <S>`: skip every step before `S` (e.g. `--start_step 4` reruns analysis only).
- `--skip_sim`: skip all PIC simulation steps (`2`, `3`, `3b`) and analyze existing outputs.
- `--skip_step <S[,S...]>`: skip the listed steps; may be repeated.

```bash
# Pressure scan without rerunning the H2/Kr baselines (identical to results/method_scan/)
bash scripts/run_full_production.sh high pressure_scan --max_steps 10000 --snapshots 10 --skip_step 3,3b
# Redo postprocessing, figures and tables for finished simulations
bash scripts/run_full_production.sh high method_comparison --skip_sim
```

Steps 3/3b run `cases/baseline_{h2,kr}.yaml`, which is the same simulation for every matrix. When
they are skipped, step 4/4b postprocesses the first existing directory among
`<out_dir>/seeded_<gas>_baseline`, `results/method_scan/seeded_<gas>_baseline`,
`results/seeded_<gas>_baseline`, `runs/seeded_<gas>_baseline`, then the matrix case at the
baseline pressure (`seeded_H2_1e-5Torr` / `seeded_Kr_1e-6Torr`).

---

### Production matrix (task 97)

`cases/production.yaml` replaces the three matrices for production. The old matrices shared several
physical runs under different names; here each of the 15 runs exists once, in
`results/production/<case_name>/`. A `stages:` section groups the cases for analysis (per-case table with a status column:
[`production_matrix.md`](production_matrix.md)):

| Stage | Cases | Contents |
|---|---|---|
| `A_method_scan` | 4 | seeded and C++/MCC at the baseline pressures (H2 1e-5, Kr 1e-6 Torr) |
| `B_method_comparison` | 7 | stage A plus vacuum and seeded at the other pressure of each gas |
| `C_pressure_scan` | 12 | seeded H2 and Kr at 1e-6 ... 3e-4 Torr |

```bash
# Validate (writes nothing into finished case directories)
bash scripts/run_full_production.sh dry-run production --skip_step 5,5b,6,6b,7,7b,8
# Run everything; --resume (default) skips finished cases, restarts unfinished ones from checkpoints
bash scripts/run_full_production.sh medium production --snapshots 10
# Stage summaries at any time, e.g. while later stages are still running
python3 scripts/postprocess_stages.py --matrix cases/production.yaml --results_dir results/production
```

- Steps 3/3b are not used (the baselines are matrix cases), step 4 writes
  `results/production/stage_<stage>/stage_summary.{csv,json}` and plots, and step 4b is not needed
  (run_scan.py postprocesses each case).
- Cases are ordered so that stage A finishes first, then the runs stage B adds, then stage C.
- `config.yaml`/`metadata.json` of a directory that already holds simulation output are never replaced by
  a dry run or a resume-skip; a checkpoint restart replaces them and keeps the previous metadata as
  `metadata.prev.json`.
- Pass `--snapshots 10`: the `medium` profile otherwise sets 15 snapshots per case.

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
