# Plasma Column Neutralizer Simulation for Cyclotron Axial Injection

Modeling, analytical theory, diagnostics, and simulation workflows for a compact plasma-assisted space-charge neutralizer in high-current compact-cyclotron axial injection lines.

---

## 1. Project Purpose

High-current (multi-mA, $30\text{ keV}$) proton beams experience strong uncompensated space-charge divergence in low-energy beam transport (LEBT) lines prior to entering a spiral inflector. This project evaluates whether a compact gas-ionized plasma column ($\text{H}_2$ or $\text{Kr}$) can effectively reduce beam perveance $K_0$ before the primary solenoid matching lens.

---

## 2. Baseline Beamline Layout

```text
buncher -> plasma neutralizer -> solenoid -> quadrupole Q1 -> quadrupole Q2 -> spiral inflector
```

> **Note**: The plasma neutralizer cell is located **upstream of the main solenoid**.

---

## 3. Physics Models

1. **Ionization Kinetics**: $p^+ + \text{Gas} \rightarrow p^+ + \text{Gas}^+ + e^-$.
2. **Neutralization Build-up**: $\eta(t) = \eta_{\text{ss}} (1 - e^{-t/\tau})$, where $\tau = 1 / (n_{\text{gas}} \sigma v_{\text{beam}})$.
3. **Space-Charge Perveance Reduction**: $K_{\text{eff}} / K_0 = 1 - \eta_{\text{net}}$, where $\eta_{\text{net}} = (N_e - N_i) / N_p$.
4. **RF-Bunched Beam Peak Space Charge**: $K_{\text{eff,peak}} / K_{0,\text{peak}} \approx 1 - \eta_{\text{avg}} / B_f$.

---

## 4. Quickstart & Installation

For a full step-by-step installation guide, see [`docs/installation.md`](file:///home/cspark/Work/projects/plasma_column/docs/installation.md) or [`INSTALL.md`](file:///home/cspark/Work/projects/plasma_column/INSTALL.md).

```bash
# 1. Clone the repository
git clone https://github.com/cspark7701/plasma_column.git
cd plasma_column

# 2. Run automated setup & verification script
bash scripts/install.sh
```

---

## 5. Step-by-Step Publication Workflow

For detailed instructions on running simulations for publication-quality figures, papers, and presentations, see [`docs/publication_workflow.md`](file:///home/cspark/Work/projects/plasma_column/docs/publication_workflow.md).

### Quick Summary:
1. **Environment Check**: `python scripts/print_environment.py`
2. **Run Standard Cases**: `python scripts/run_case.py --case cases/baseline_h2.yaml`
3. **Run C++ MCC PICMI**: `python plasma_column_mcc_picmi_v7.py --output_dir results/cxx_H2_mcc --gas H2 --pressure_torr 1e-5 --run`
4. **Postprocess Case Diagnostics**: `python scripts/postprocess_case.py --case-dir results/seeded_H2_baseline`
5. **Notebook Analysis**: Open [`run_plasma_column_method_comparison.ipynb`](file:///home/cspark/Work/projects/plasma_column/run_plasma_column_method_comparison.ipynb) and [`plasma_column_analysis_plots_v2.ipynb`](file:///home/cspark/Work/projects/plasma_column/plasma_column_analysis_plots_v2.ipynb)
6. **Generate Figures & Manifest**: `python scripts/make_plots.py`

---

## 5. Primary Notebooks

1. [`run_plasma_column_method_comparison.ipynb`](file:///home/cspark/Work/projects/plasma_column/run_plasma_column_method_comparison.ipynb): Method comparison across Vacuum, Seeded, Callback, and C++ MCC runs.
2. [`plasma_column_analysis_plots_v2.ipynb`](file:///home/cspark/Work/projects/plasma_column/plasma_column_analysis_plots_v2.ipynb): Main front-end analysis and figure generation notebook.
3. [`run_python_callback_source_diagnostics_v2.ipynb`](file:///home/cspark/Work/projects/plasma_column/run_python_callback_source_diagnostics_v2.ipynb): Diagnostics notebook for Python callback dynamic pair creation.
4. [`run_seeded_full_transport_diagnostics.ipynb`](file:///home/cspark/Work/projects/plasma_column/run_seeded_full_transport_diagnostics.ipynb): Detailed beam envelope and RMS emittance transport diagnostics.

---

## 6. Repository Structure

```text
plasma_column/
  AGENTS.md
  README.md
  cases/                 # YAML simulation case configurations
    vacuum.yaml
    baseline_h2.yaml
    baseline_kr.yaml
    bunched_h2.yaml
    bunched_kr.yaml
    method_comparison.yaml
  docs/                  # Documentation, physics notes, patches, & task logs
    environment.md
    publication_workflow.md
    refactor_plan.md
    warpx_customization.md
    method_comparison.md
    antigravity_tasks/
    exec-plans/
      completed/
    literature/
    physics_notes/
    proceedings/
    slides/
    warpx_patches/
  plots/                 # Generated PNG & PDF figures + manifest.csv
  results/               # Isolated simulation run outputs & results (ignored by git)
  scripts/               # CLI wrappers and utilities
    print_environment.py
    run_case.py
    run_scan.py
    postprocess_case.py
    plot_cross_sections.py
    plot_bunched_beam_perveance.py
    make_plots.py
    audit_repo.py
  src/
    plasma_column/       # Core Python package modules
      __init__.py
      constants.py
      beam.py
      gas.py
      neutralization.py
      diagnostics.py
      plotting.py
      warpx_io.py
  tests/                 # Pytest unit test suite
```

---

## 7. Environment Setup

Activate the pre-configured `warpx-dev` conda environment:

```bash
cd /home/cspark/Work/projects/plasma_column
conda activate warpx-dev
# or: source ./setup.sh
```

Run environment audit:

```bash
python scripts/print_environment.py
```

---

## 8. Quick Dry-Run Verification

Validate parameters and write `metadata.json` without performing long PIC steps:

```bash
# Validate single cases
python scripts/run_case.py --case cases/baseline_h2.yaml --dry_run
python scripts/run_case.py --case cases/baseline_kr.yaml --dry_run

# Validate full comparison matrix scan
python scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run
```

---

## 9. Interpreting $K_{\text{eff}}/K_0$

- **$K_{\text{eff}}/K_0 = 1.0$**: Uncompensated space charge (vacuum beam).
- **$0.0 < K_{\text{eff}}/K_0 < 1.0$**: Partial space-charge compensation.
- **$K_{\text{eff}}/K_0 = 0.0$**: Complete $100\%$ charge neutralization.
- **$K_{\text{eff}}/K_0 < 0.0$**: Overcompensation (plasma electron density exceeds beam proton density).

---

## 10. Bunched-Beam Caveat

Because the RF buncher is located upstream of the plasma cell, the proton beam enters as periodic micro-bunches ($B_f \approx 5$).

While the plasma electrons provide an average neutralization $\eta_{\text{avg}}$, the **peak-bunch perveance ratio** during micro-bunch passage is:

$$\frac{K_{\text{eff,peak}}}{K_{0,\text{peak}}} \approx 1 - \frac{\eta_{\text{avg}}}{B_f}$$

For $B_f = 5$ and $\eta_{\text{avg}} = 90\%$, $K_{\text{eff,peak}}/K_{0,\text{peak}} \approx 0.82$, meaning **$82\%$ of peak space-charge blowup remains active**.

---

## 11. WarpX Source Customization

Self-consistent proton-impact ionization ($p^+ + \text{Gas} \rightarrow p^+ + \text{Gas}^+ + e^-$) uses custom C++ extensions added to the local WarpX source tree (`/home/cspark/Work/simulation_codes-working/warpx`).

- **Documentation**: [`docs/warpx_customization.md`](file:///home/cspark/Work/projects/plasma_column/docs/warpx_customization.md)
- **Patch File**: [`docs/warpx_patches/warpx_plasma_column_current.patch`](file:///home/cspark/Work/projects/plasma_column/docs/warpx_patches/warpx_plasma_column_current.patch)

---

## 12. Repository Audit & Testing

To run the complete unit test suite and repository audit:

```bash
python scripts/audit_repo.py --root .
python -m pytest -q
```
