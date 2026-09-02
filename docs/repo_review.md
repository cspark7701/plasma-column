# Repository Review: plasma-column

- **Repository**: [`plasma-column`](file:///home/cspark/Work/projects/plasma-column)
- **Branch / Commit**: `main` (`a83da20`)
- **Lead Author**: Chong Shik Park (*Department of Accelerator Science and Center for Accelerator Research, Korea University*)

---

## 1. Executive Summary

The `plasma-column` repository is a specialized scientific simulation, diagnostics, analytical modeling, and publication workflow suite for compact gas-ionized ($\text{H}_2/\text{Kr}$) plasma-assisted space-charge neutralizers in high-current compact-cyclotron axial injection systems ($30\text{ keV}$, multi-mA proton beams).

The codebase is well-structured, modular, and fully tested. All 101 unit tests, repository audit checks, and smoke test routines pass cleanly.

---

## 2. Codebase Architecture & Components

```text
plasma_column/
├── AGENTS.md                  # Project rules, physics specs, & operational guidelines
├── README.md                  # Quickstart, installation, & workflow guide
├── cases/                     # YAML configuration cases & verification presets
│   ├── baseline_h2.yaml       # Standard H2 baseline case (1e-5 Torr)
│   ├── baseline_kr.yaml       # Standard Kr baseline case (1e-6 Torr)
│   ├── bunched_h2.yaml        # RF-bunched beam H2 case (B_f = 5)
│   ├── method_comparison.yaml # 9-case multi-method matrix scan
│   └── verification/          # 5 verification & convergence case configs
├── docs/                      # Extensive documentation & Sphinx/RTD website
│   ├── physics_notes/         # Analytical models, bunched beams, cross sections
│   ├── warpx_patches/         # Local WarpX C++ source tree patch tracking
│   ├── consolidated_report/   # LaTeX consolidated report & bibliography
│   └── site/                  # ReadTheDocs-themed static documentation portal
├── notebooks/                 # Production simulation & analysis Jupyter notebooks
│   ├── runs/                  # PICMI execution notebooks (vacuum, seeded, callback)
│   └── analysis/              # Publication analysis, profiles, perveance, scans
├── paper/                     # Publication figures, tables, & journal outline
├── scripts/                   # CLI entry points for automation, scans, & plotting
│   ├── run_case.py            # Case runner with dry-run & metadata recording
│   ├── run_scan.py            # Parameter matrix scanner with schema validation
│   ├── postprocess_case.py    # Reduced diagnostics & profile extraction
│   ├── make_plots.py          # Unified publication figure & manifest generator
│   └── audit_repo.py          # Strict repository health & integrity auditor
├── src/plasma_column/         # Core Python package
│   ├── constants.py           # Physical constants (SI units, radiation lengths)
│   ├── schema.py              # Validated dataclass schemas (SimulationCaseConfig)
│   ├── beam.py                # ProtonBeam, RFFocusedBeam, λ(z) slice & Er(r,z) fields
│   ├── gas.py                 # NeutralGas, CrossSectionDatabase, MCS & MFP
│   ├── neutralization.py      # Analytical kinetics & perveance scaling laws
│   ├── injection_line.py      # Downstream layout & 2D (Rx, Ry) envelope integration
│   ├── acceptance.py          # Inflector acceptance ellipse & transmission efficiency
│   ├── diagnostics.py         # ParticleNumber, thread-safe DataLoader, masked core η
│   ├── warpx_io.py            # Machine-readable metadata.json & plotfile loader
│   └── plotting/              # Modular publication figure generation package
└── tests/                     # 18 test suites (101 unit tests)
```

---

## 3. Physics & Simulation Framework

### 1. Beamline Optics Ordering

Conforms strictly to baseline layout:

$$\text{buncher} \longrightarrow \text{plasma neutralizer} \longrightarrow \text{solenoid} \longrightarrow \text{quadrupole Q1} \longrightarrow \text{quadrupole Q2} \longrightarrow \text{spiral inflector}$$

### 2. Multi-Tier Simulation Methods

The simulation pipeline supports four distinct simulation fidelity levels:

1. **`vacuum_reference`**: Pure vacuum uncompensated reference beam ($K_{\text{eff}}/K_0 = 1.0$).
2. **`seeded_compensation`**: Static analytical electron-ion density seeding.
3. **`python_callback`**: Dynamic pair injection via PICMI step callback routines.
4. **`cxx_mcc_custom`**: WarpX C++ Monte Carlo Collisions tracking with proton-impact ionization.

### 3. Neutralization & Bunched-Beam Metrics

- **Core vs. Global**: [`src/plasma_column/diagnostics.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/diagnostics.py) provides volume-averaged beam core compensation ($\eta_{\text{local,net}}$) and guards against over-interpreting domain-wide particle counts.
- **RF-Bunched Space Charge**: For a pre-bunched beam with bunching factor $B_f$, peak-bunch effective perveance reduction follows:

  $$\frac{K_{\text{eff,peak}}}{K_{0,\text{peak}}} \approx 1 - \frac{\eta_{\text{avg}}}{B_f}$$

- **Highland Multiple Coulomb Scattering (MCS)**: Gas scattering angle $\theta_0$ and transmission losses through the gas column are fully modeled in [`src/plasma_column/gas.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/gas.py).

---

## 4. Verification & Test Suite Status

| Verification Test | Command | Result |
|---|---|---|
| **Compilation** | `python -m compileall scripts src tests` | **Clean** (0 errors) |
| **Pytest Suite** | `pytest -q` | **101 passed** (100% pass rate) |
| **Repository Audit** | `python scripts/audit_repo.py --root .` | **Passed** |
| **Smoke Test** | `python scripts/smoke_test.py` | **Passed** |
| **Single-Case Dry-Run** | `python scripts/run_case.py --case cases/baseline_h2.yaml --dry_run` | **Passed** (writes valid `metadata.json`) |
| **Matrix-Scan Dry-Run** | `python scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run` | **Passed** (all 9 cases validated) |

---

## 5. Summary & Key Strengths

1. **Strict Type & Schema Safety**: Dataclass configurations ([`schema.py`](file:///home/cspark/Work/projects/plasma-column/src/plasma_column/schema.py)) enforce positive grid sizes, physical boundary checks, and canonical method naming.
2. **Reproducibility**: Every production run produces an isolated output directory containing validated `config.yaml` and `metadata.json` capturing git commit hashes (both repo and WarpX source tree), host environment, and runtime flags.
3. **Data Caching & Vectorization**: Thread-safe `DataLoader` with `st_mtime` cache invalidation and vectorized NumPy/SciPy `binned_statistic` algorithms ensure high postprocessing throughput.
4. **Publication-Ready**: Includes a dedicated manuscript outline ([`paper/plasma_column_journal_outline.md`](file:///home/cspark/Work/projects/plasma-column/paper/plasma_column_journal_outline.md)), automated figure generators (`fig01`–`fig10`), parameter summary tables, and a ReadTheDocs-themed static site under [`docs/site/`](file:///home/cspark/Work/projects/plasma-column/docs/site/).
