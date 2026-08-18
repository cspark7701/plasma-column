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
2. **Run Standard Cases**: `python scripts/run_case.py --case cases/baseline_h2.yaml` (calls `plasma_column_mcc_picmi_v7.py` under the hood)
3. **Run Parameter Scans**: `python scripts/run_scan.py --matrix cases/method_comparison.yaml`
4. **Postprocess Case Diagnostics**: `python scripts/postprocess_case.py --case-dir results/seeded_H2_baseline`
5. **Notebook Analysis**: Use the modular notebooks in [`notebooks/runs/`](file:///home/cspark/Work/projects/plasma_column/notebooks/runs) and [`notebooks/analysis/`](file:///home/cspark/Work/projects/plasma_column/notebooks/analysis)
6. **Generate Figures & Manifest**: `python scripts/make_plots.py`

---

## 5. Primary Notebooks

*(Note: All notebooks use the `warpx-dev` Jupyter kernel.)*

1. [`notebooks/runs/nb_vacuum_reference.ipynb`]: Vacuum reference run — establishes K_eff/K0 ≈ 1 baseline.
2. [`notebooks/runs/nb_seeded_h2.ipynb`]: Seeded H2 neutralizer full transport run.
3. [`notebooks/runs/nb_seeded_kr.ipynb`]: Seeded Kr neutralizer full transport run.
4. [`notebooks/runs/nb_callback_h2.ipynb`]: Python callback ionization source — H2.
5. [`notebooks/runs/nb_callback_kr.ipynb`]: Python callback ionization source — Kr.
6. [`notebooks/analysis/nb_analysis_plots.ipynb`]: Auto-discovers all completed runs and generates the full publication figure set.
7. [`notebooks/analysis/nb_bunched_beam_perveance.ipynb`]: RF-bunched beam K_eff,peak analysis, perveance landscape, and RF sensitivity plots.
8. [`notebooks/analysis/nb_cross_section_comparison.ipynb`]: H2 vs Kr cross-section comparison, τ vs pressure, neutralization build-up family curves, and 2-D pressure×length map.
9. [`notebooks/analysis/nb_local_neutralization_profiles.ipynb`]: Local radial/axial density profiles, transverse density slice, η(z) H₂ vs Kr, and phase-space portraits.
10. [`notebooks/analysis/nb_parameter_scan_analysis.ipynb`]: Full parameter scan heatmaps, comparison bar charts, and small-multiple η(t) grid.
11. [`notebooks/analysis/nb_extended_visualizations.ipynb`]: Extended physics visualization suite — perveance landscape, K_eff/K₀ vs η, ionization τ, η(t) family, 2-D maps, RF sensitivity, phase-space portraits, and summary table.
12. [`notebooks/nb_full_production_pipeline.ipynb`]: Consolidated pipeline notebook mirroring `run_full_production.sh` step-by-step.

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
  notebooks/             # Jupyter notebooks for runs and analysis
    nb_full_production_pipeline.ipynb
    analysis/
      nb_analysis_plots.ipynb
      nb_bunched_beam_perveance.ipynb
      nb_cross_section_comparison.ipynb
      nb_extended_visualizations.ipynb
      nb_local_neutralization_profiles.ipynb
      nb_parameter_scan_analysis.ipynb
    runs/
      nb_callback_h2.ipynb
      nb_callback_kr.ipynb
      nb_seeded_h2.ipynb
      nb_seeded_kr.ipynb
      nb_vacuum_reference.ipynb
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
      constants.py       # Physical constants, conversions & radiation lengths
      beam.py            # ProtonBeam, RFFocusedBeam, slice lambda(z) & radial Er(r,z)
      gas.py             # NeutralGas density, CrossSectionDatabase, scattering & MFP
      injection_line.py  # 2D envelope integration with region-dependent K_eff(z)
      acceptance.py      # Inflector acceptance ellipse & transmission efficiency
      neutralization.py  # Neutralization kinetics & perveance scaling
      diagnostics.py     # ParticleNumber & vectorized 2D masked core diagnostics
      schema.py          # Validated dataclass schemas & YAML case parsing
      warpx_io.py        # Machine-readable metadata & plotfile loader
      notebook_utils.py  # Shared notebook styling & path configuration
      plotting/          # Modular publication figure generator package
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
