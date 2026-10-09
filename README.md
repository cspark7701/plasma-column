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

For a full step-by-step installation guide, see [`docs/installation.md`](docs/installation.md) or [`INSTALL.md`](INSTALL.md).

```bash
# 1. Clone the repository
git clone https://github.com/cspark7701/plasma-column.git
cd plasma-column

# 2. Run automated setup & verification script
bash scripts/install.sh
```

---

## 5. Step-by-Step Publication Workflow

For detailed instructions on running simulations for publication-quality figures, papers, and presentations, see [`docs/publication_workflow.md`](docs/publication_workflow.md).

### Quick Summary:
1. **Environment Check**: `python scripts/print_environment.py`
2. **Run Standard Cases**: `python scripts/run_case.py --case cases/baseline_h2.yaml` (calls `plasma_column_mcc_picmi_v7.py` under the hood)
3. **Run Parameter Scans**: `python scripts/run_scan.py --matrix cases/method_comparison.yaml`
4. **Postprocess Case Diagnostics**: `python scripts/postprocess_case.py --case-dir results/seeded_H2_baseline`
5. **Notebook Analysis**: Use the modular notebooks in [`notebooks/runs/`](notebooks/runs) and [`notebooks/analysis/`](notebooks/analysis)
6. **Generate Figures & Manifest**: `python scripts/make_plots.py`

---

## 6. Primary Notebooks

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

## 7. Repository Structure

```text
plasma_column/
  AGENTS.md
  README.md
  INSTALL.md
  setup.sh               # Environment activation & hardware auto-detection
  pyproject.toml / environment.yml / requirements-dev.txt
  .github/workflows/ci.yml
  cases/                 # YAML simulation case configurations
    vacuum.yaml
    baseline_h2.yaml
    baseline_kr.yaml
    bunched_h2.yaml
    bunched_kr.yaml
    method_comparison.yaml
    method_scan_baseline.yaml
    pressure_scan_h2_kr.yaml
    verification/        # Custom ion-impact MCC verification cases
  docs/                  # Documentation, physics notes, patches, & task logs
    installation.md
    environment.md
    publication_workflow.md
    full_production_pipeline.md
    warpx_customization.md
    method_comparison.md
    consolidated_report/ # LaTeX consolidated report (+ PDF)
    development/         # Repo hardening, testing & CI notes
    exec-plans/
      completed/         # Numbered task summaries
    literature/
    physics_notes/
    proceedings/
    publication/         # Figure/table lists, limitations, interpretation
    site/                # Read-the-Docs-style project web page template
    slides/
    verification/        # Custom MCC validation report
    warpx_patches/       # WarpX C++ patch + IonImpactIonization.H
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
      nb_parameter_scan.ipynb
      nb_seeded_h2.ipynb
      nb_seeded_kr.ipynb
      nb_vacuum_reference.ipynb
  paper/                 # Journal outline, figure manifest & CSV tables
  plots/                 # Generated PNG & PDF figures + manifest.csv
  results/               # Isolated simulation run outputs & results (ignored by git)
  scripts/               # CLI wrappers and utilities
    print_environment.py
    run_case.py
    run_scan.py
    run_full_production.sh
    postprocess_case.py
    make_plots.py
    make_paper_figures.py
    make_paper_tables.py
    run_mcc_verification.py
    analyze_mcc_verification.py
    plasma_column_mcc_picmi_v7.py              # PICMI/WarpX MCC & seeded driver
    plasma_column_callback_source_picmi_v3.py  # PICMI/WarpX Python-callback source driver
    _gen_notebooks.py    # Regenerates notebooks (overwrites hand edits)
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
      run_matrix.py      # Scan-matrix expansion for run_scan.py
      hardware.py        # CPU/GPU resource detection
      warpx_io.py        # Machine-readable metadata & plotfile loader
      notebook_utils.py  # Shared notebook styling & path configuration
      plotting/          # Modular publication figure generator package
  tests/                 # Pytest unit test suite
  warpx_proton_impact_cross_sections_linear/  # H2 & Kr MCC cross-section tables
```

---

## 8. Environment Setup

Activate the pre-configured `warpx-dev` conda environment:

```bash
cd /home/cspark/Work/projects/plasma-column
conda activate warpx-dev
# or: source ./setup.sh
```

Run environment audit:

```bash
python scripts/print_environment.py
```

---

## 9. Quick Dry-Run Verification

Validate parameters and write `metadata.json` without performing long PIC steps:

```bash
# Validate single cases
python scripts/run_case.py --case cases/baseline_h2.yaml --dry_run
python scripts/run_case.py --case cases/baseline_kr.yaml --dry_run

# Validate full comparison matrix scan
python scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run
```

---

## 10. Interpreting $K_{\text{eff}}/K_0$

- **$K_{\text{eff}}/K_0 = 1.0$**: Uncompensated space charge (vacuum beam).
- **$0.0 < K_{\text{eff}}/K_0 < 1.0$**: Partial space-charge compensation.
- **$K_{\text{eff}}/K_0 = 0.0$**: Complete $100\%$ charge neutralization.
- **$K_{\text{eff}}/K_0 < 0.0$**: Overcompensation (plasma electron density exceeds beam proton density).

---

## 11. Bunched-Beam Caveat

Because the RF buncher is located upstream of the plasma cell, the proton beam enters as periodic micro-bunches ($B_f \approx 5$).

While the plasma electrons provide an average neutralization $\eta_{\text{avg}}$, the **peak-bunch perveance ratio** during micro-bunch passage is:

$$\frac{K_{\text{eff,peak}}}{K_{0,\text{peak}}} \approx 1 - \frac{\eta_{\text{avg}}}{B_f}$$

For $B_f = 5$ and $\eta_{\text{avg}} = 90\%$, $K_{\text{eff,peak}}/K_{0,\text{peak}} \approx 0.82$, meaning **$82\%$ of peak space-charge blowup remains active**.

---

## 12. WarpX Source Customization

Proton-impact ionization ($p^+ + \text{Gas} \rightarrow p^+ + \text{Gas}^+ + e^-$) is not available in upstream WarpX: its built-in MCC impact ionization targets electron-impact workflows. This project therefore uses custom C++ extensions (`ION_IMPACT_IONIZATION` in `BackgroundMCC`) added to the local WarpX source tree (`/home/cspark/Work/simulation_codes-working/warpx`).

> **Caution**:
> - The custom extension is **not yet validated as a self-consistent PIC model**. [`docs/verification/custom_ion_impact_mcc_validation.md`](docs/verification/custom_ion_impact_mcc_validation.md) defines analytical rate targets (no-gas, zero/fixed cross-section, H2/Kr ratio, time-step convergence, weight and energy bookkeeping); the modified C++ kernel must still be run against these targets before claiming PIC benchmark validation.
> - Seeded-compensation and Python-callback runs are **analytic/data-driven source estimates**, not self-consistent proton-impact MCC.
> - Check that the WarpX build used for a run matches the tracked patch (see `docs/exec-plans/completed/87_repository_review.md`).

- **Documentation**: [`docs/warpx_customization.md`](docs/warpx_customization.md)
- **Patch File**: [`docs/warpx_patches/warpx_plasma_column_current.patch`](docs/warpx_patches/warpx_plasma_column_current.patch)

---

## 13. Repository Audit & Testing

To run the complete unit test suite and repository audit:

```bash
python scripts/audit_repo.py --root .
python -m pytest -q
```
