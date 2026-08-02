# Consolidated Simulation Procedure and Publication Workflow

## 1. Overview and Baseline Physics Context

This document provides a single, unified guide covering the end-to-end procedure for **simulation setup, execution, postprocessing diagnostics, optics transport analysis, and publication figure freeze** for the plasma-assisted space-charge neutralizer project.

### 1.1 Baseline Beamline Geometry

All simulation, transport, and publication workflows enforce the baseline axial-injection layout:

$$\text{buncher} \rightarrow \text{plasma neutralizer} \rightarrow \text{solenoid} \rightarrow \text{quadrupole Q1} \rightarrow \text{quadrupole Q2} \rightarrow \text{spiral inflector}$$

> [!IMPORTANT]
> Do not describe or model the baseline neutralizer as being situated after the main solenoid. That placement is tested only as an explicit alternative-geometry study.

### 1.2 Core Physics Objectives and Metrics
- **Beam Parameters**: $30\text{ keV}$, $10\text{ mA}$ proton beam ($\beta \approx 0.008$, $v_p \approx 2.4 \times 10^6\text{ m/s}$).
- **Gas Neutralizers**: $\text{H}_2$ ($10^{-5}\text{ Torr}$) and $\text{Kr}$ ($10^{-6}\text{ Torr}$) plasma column cells ($L_{\text{cell}} = 0.20\text{ m}$).
- **Local Beam-Core Neutralization**:
  $$\eta_{\text{local,net}}(z,t) = \frac{\langle n_e \rangle_{\text{core}}(z,t) - \langle n_i \rangle_{\text{core}}(z,t)}{\langle n_p \rangle_{\text{core}}(z,t)}, \quad \frac{K_{\text{eff,local}}}{K_0} = 1 - \eta_{\text{local,net}}$$
- **RF-Bunched Beam Peak Scaling**:
  $$\frac{K_{\text{eff,peak}}}{K_{0,\text{peak}}} \approx 1 - \frac{\eta_{\text{avg}}}{B_f} \quad (B_f = I_{\text{peak}}/I_{\text{avg}} = 5)$$

---

## 2. Step 1 — Environment Activation and Testing Audit

Before launching simulations or generating figures, activate the `warpx-dev` environment and verify repository integrity:

```bash
cd /home/cspark/Work/projects/plasma_column
conda activate warpx-dev

# 1. Print environment details and WarpX git status
python scripts/print_environment.py

# 2. Run repository structure audit
python scripts/audit_repo.py --root .

# 3. Run full automated unit test suite (49+ tests)
python scripts/smoke_test.py
```

---

## 3. Step 2 — Simulation Execution Procedure

Simulations can be run in **dry-run mode** (for instant validation and parameter checks) or **production mode**.

### 3.1 Dry-Run Parameter Validation (Recommended First Step)
To inspect derived parameters and write `metadata.json` without running long PIC steps:

```bash
python scripts/run_case.py --case cases/vacuum.yaml --dry_run
python scripts/run_case.py --case cases/baseline_h2.yaml --dry_run
python scripts/run_case.py --case cases/baseline_kr.yaml --dry_run
python scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run
```

### 3.2 Running Standard Simulation Cases
To launch full PIC simulation cases:

```bash
# 1. Vacuum Reference (Uncompensated beam propagation)
python scripts/run_case.py --case cases/vacuum.yaml

# 2. Baseline H2 Neutralizer Cell (1e-5 Torr)
python scripts/run_case.py --case cases/baseline_h2.yaml

# 3. Baseline Kr Neutralizer Cell (1e-6 Torr)
python scripts/run_case.py --case cases/baseline_kr.yaml

# 4. RF-Bunched Beam Cases
python scripts/run_case.py --case cases/bunched_h2.yaml
python scripts/run_case.py --case cases/bunched_kr.yaml
```

### 3.3 Custom Ion-Impact MCC Verification Suite
To execute the WarpX custom C++ MCC ion-impact verification tests (Tests 1–7):

```bash
# Run verification suite (dry-run or production)
python scripts/run_mcc_verification.py --dry_run
python scripts/analyze_mcc_verification.py
```

---

## 4. Step 3 — Postprocessing Diagnostics and Beam-Core Metrics

Every completed simulation case directory (`results/<case_name>/`) is postprocessed to extract global and local core space-charge compensation indicators.

```bash
python scripts/postprocess_case.py --case-dir results/seeded_H2_baseline
python scripts/postprocess_case.py --case-dir results/seeded_Kr_baseline
```

### Standardized Case Output Files Generated:
- `global_particle_number.csv`: Time series of total particle counts $N_p, N_e, N_i$.
- `neutralization_from_particle_number.csv`: Global neutralization fractions $\eta_{\text{electron\_only}}, \eta_{\text{net}}, K_{\text{eff}}/K_0$.
- `local_neutralization_vs_t.csv`: Time series of volume-averaged beam-core densities ($r \le 2\text{ mm}$) and local $K_{\text{eff,local}}/K_0$.
- `local_neutralization_vs_z.csv`: Slice-by-slice longitudinal profile $\eta_{\text{local}}(z)$ along the beam axis.
- `radial_density_profiles.csv`: Radially-binned species densities $n_p(r), n_e(r), n_i(r)$ and net charge density $\rho_{\text{net}}(r)$.
- `beam_core_charge_density.csv`: Volumetric core charge densities ($\text{C/m}^3$).
- `diagnostics_summary.json`: Machine-readable summary and explicit limitation warnings if local 3D data are absent.

---

## 5. Step 4 — RF-Bunched Beam Analysis & Downstream Injection Optics

To connect plasma-column neutralization results to the downstream beamline transport:

```bash
# 1. Evaluate RF-bunched beam perveance scaling over bunching factors B_f = 1, 2, 3, 5, 10
python scripts/analyze_bunched_beam_neutralization.py

# 2. Simulate downstream beam envelope transport through solenoid and quadrupoles to spiral inflector
python scripts/transport_to_inflector.py
```

### Output Optics Metrics & Figures:
- `data/inflector_entrance_summary.csv`: Transmission percentages and envelope radii at inflector entrance.
- `data/beam_envelope_to_inflector.csv`: Envelope trajectories $R_x(z), R_y(z)$ from $z=0$ to $z=1.0\text{ m}$.
- `data/phase_space_at_inflector.csv`: Transverse phase-space macroparticle coordinates $(x, x')$ and $(y, y')$.
- `plots/envelope_buncher_to_inflector.png` / `.pdf`: Beam envelope comparison (vacuum vs neutralized).
- `plots/inflector_phase_space_xxp.png` / `.pdf`: Phase space ellipse at inflector entrance.
- `plots/transmission_comparison.png` / `.pdf`: Bar chart showing inflector transmission efficiency ($25\%$ vacuum vs $100\%$ neutralized).

---

## 6. Step 5 — Publication Figure Freeze & Manuscript Dataset Workflow

To freeze publication-quality tables, figures, metadata, and dataset files for journal submission:

```bash
# 1. Generate 5 standardized CSV tables under paper/tables/
python scripts/make_paper_tables.py

# 2. Generate 10 publication figure pairs (.png and .pdf) and metadata JSON files under paper/figures/
python scripts/make_paper_figures.py

# 3. Freeze canonical dataset under paper/data/ and generate dataset_manifest.json
python scripts/freeze_publication_dataset.py
```

### 6.1 Publication Package File Organization

```text
paper/
├── plasma_column_journal_outline.md       # PRAB / NIMA manuscript outline
├── figure_manifest.csv                    # Mapping of Fig 1-10 to cases & scripts
├── tables/
│   ├── table_beam_parameters.csv
│   ├── table_gas_parameters.csv
│   ├── table_simulation_parameters.csv
│   ├── table_result_summary.csv
│   └── table_validation_summary.csv
├── figures/
│   ├── fig01_axial_injection_concept.[png|pdf|json]
│   ├── fig02_plasma_neutralizer_module.[png|pdf|json]
│   ├── fig03_analytical_neutralization_time.[png|pdf|json]
│   ├── fig04_local_plasma_density_profiles.[png|pdf|json]
│   ├── fig05_local_Keff_over_K0_vs_time.[png|pdf|json]
│   ├── fig06_bunched_beam_interpretation.[png|pdf|json]
│   ├── fig07_beam_envelope_to_inflector.[png|pdf|json]
│   ├── fig08_inflector_acceptance_transmission.[png|pdf|json]
│   ├── fig09_parameter_scan_summary.[png|pdf|json]
│   └── fig10_numerical_validation.[png|pdf|json]
└── data/
    ├── dataset_manifest.json
    └── (frozen CSV result datasets)
```

### 6.2 Documentation References
- [`docs/publication/publication_result_set.md`](file:///home/cspark/Work/projects/plasma_column/docs/publication/publication_result_set.md): Summary of frozen case result set.
- [`docs/publication/results_interpretation.md`](file:///home/cspark/Work/projects/plasma_column/docs/publication/results_interpretation.md): Physics interpretation of neutralization, bunched-beam scaling, and optics transport.
- [`docs/publication/limitations.md`](file:///home/cspark/Work/projects/plasma_column/docs/publication/limitations.md): Scientific limitations (local vs global metrics, RF peak compensation limits, gas load, MCC validation).
