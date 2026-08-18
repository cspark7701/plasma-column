# Refactoring and Modular Package Architecture Plan

## 1. Executive Summary

This plan outlines the gradual refactoring of the `plasma_column` codebase from a collection of standalone root scripts and exploratory notebooks into a structured, tested Python package `plasma_column` under `src/`.

The primary goals are:
- Decouple front-end presentation (notebooks) from physics, diagnostics, and I/O logic.
- Eliminate script duplication and clarify canonical code paths.
- Ensure all plotting and analysis routines follow deterministic, scriptable workflows.
- Maintain full backwards compatibility during the migration phase so existing scripts remain executable.

---

## 2. Codebase Audit and Dependency Mapping

### 2.1 Front-End Analysis Notebooks
- `plasma_column_analysis_plots_v2.ipynb`: Reads outputs from `runs/` and calls plotting routines.
- `run_plasma_column_method_comparison.ipynb`: Compares seeded, callback, and C++ MCC simulation methods.
- `run_python_callback_source_diagnostics_v2.ipynb`: Analyzes Python callback dynamic pair creation.
- `run_seeded_full_transport_diagnostics.ipynb`: Analyzes seeded neutralization transport cases.

### 2.2 Legacy & Duplicate Script Mapping
| Category | Archived / Older Iterations | Current Root Implementation | Target Canonical Package Module |
| :--- | :--- | :--- | :--- |
| **PICMI MCC Simulation** | `archives/old_scripts/plasma_column_mcc_picmi_v1..v6.py` | `plasma_column_mcc_picmi_v7.py` | `scripts/run_case.py` + `src/plasma_column/warpx_io.py` |
| **Python Callback PICMI** | `archives/plasma_column_callback_source_picmi.py` (v1, v2) | `plasma_column_callback_source_picmi_v3.py` | `src/plasma_column/neutralization.py` + `scripts/run_case.py` |
| **Particle Diagnostics** | `particle_number_diagnostics.py` | `particle_number_diagnostics_v2.py`, `particle_number_diagnostics_compare.py` | `src/plasma_column/diagnostics.py` |
| **Plotting & Analysis** | `archives/plasma_column_analysis_plots.py` | `plasma_column_analysis_plots_v2.py` | `src/plasma_column/plotting.py` |

---

## 3. Modular Package Architecture (`src/plasma_column/`)

```text
src/plasma_column/
├── __init__.py          # Package initialization & public API re-exports
├── constants.py         # Physical constants (C, QE, ME, MP, AMU, KB, EPSILON_0) & radiation lengths
├── beam.py              # Beam kinematics, perveance K0, RF bunching, slice lambda(z) & radial Er(r,z)
├── gas.py               # NeutralGas density, CrossSectionDatabase, scattering & collision mean free path
├── injection_line.py    # 2D transverse envelope ODE integration with region-dependent K_eff(z)
├── acceptance.py        # Spiral inflector geometric acceptance ellipse & transmission model
├── neutralization.py    # Buildup kinetics, global ratios (eta_e, eta_net, K_eff/K0, peak-bunch perveance)
├── diagnostics.py       # ParticleNumber parsers, DataLoader thread safety, vectorized 2D masked reductions
├── schema.py            # Validated dataclass schemas, YAML parsing, and method dispatch
├── warpx_io.py          # Machine-readable metadata.json & plotfile loader
├── notebook_utils.py    # Shared notebook styling, paths, and execution context
└── plotting/            # Modular publication plotting subpackage
    ├── neutralization.py # Particle populations, eta(t), K_eff/K0, growth rates, profiles
    ├── cross_sections.py # Proton-impact ionization cross-section comparisons
    ├── transport.py      # Phase space scatter & 2D (Rx, Ry) envelope with layout schematic
    ├── paper_figures.py  # Manuscript vector publication figure generators (fig01–fig05)
    └── scan.py           # Multi-case comparison bars, heatmaps & parameter scans
```

---

## 4. Canonical API Specification

### `plasma_column.constants`
- Provides standard physical constants (`C`, `QE`, `ME`, `MP`, `AMU`, `KB`, `EPSILON_0`), conversions (`TORR_TO_PA`, `EV_TO_JOULE`), and radiation lengths (`RADIATION_LENGTH_H2`, `RADIATION_LENGTH_KR`).

### `plasma_column.beam`
- `ProtonBeam`: Dataclass managing $E_{\text{beam}}$, $I_{\text{beam}}$, $r_{\text{beam}}$, $\beta$, $\gamma$, $v_{\text{beam}}$, and uncompensated perveance $K_0$.
- `RFFocusedBeam`: Extension containing RF frequency $f_{\text{RF}}$, bunching factor $B_f$, bunch charge $Q_{\text{bunch}}$, slice line charge density $\lambda(z)$ (parabolic, Gaussian, top-hat), and radial space-charge electric field $E_r(r, z)$.

### `plasma_column.gas`
- `NeutralGas`: Dataclass calculating neutral number density $n_{\text{gas}} = p / (k_B T)$ for $\text{H}_2$ and $\text{Kr}$.
- `CrossSectionDatabase`: Lookup and interpolation for proton-impact ionization in laboratory and center-of-mass frames.
- `mean_free_path_m`, `transmission_fraction`, `multiple_scattering_rms_rad`: Analytical scattering and transmission loss models.

### `plasma_column.injection_line`
- `InjectionLine`: Optical layout dataclass representing the baseline compact cyclotron injection beamline.
- `compute_beam_envelope`: 2D coupled envelope ODE solver with region-dependent perveance $K_{\text{eff}}(z)$ separating the neutralizer cell from downstream vacuum drift.

### `plasma_column.neutralization`
- `compute_neutralization_ratios(N_p, N_e, N_i)`: Returns $\eta_{\text{electron\_only}}$, $\eta_{\text{net}}$, $K_{\text{eff,electron\_only}}/K_0$, $K_{\text{eff,net}}/K_0$.
- `compute_bunched_beam_peak_perveance(eta_avg, bunching_factor)`: Evaluates peak-bunch space charge factor $K_{\text{eff,peak}}/K_{0,\text{peak}} \approx 1 - \eta_{\text{avg}}/B_f$.

### `plasma_column.diagnostics`
- `load_particle_number_diagnostic(path)`: Loads and cleans WarpX `ParticleNumber.txt` data.
- `compute_local_core_neutralization`, `compute_local_neutralization_vs_z`: Vectorized 2D masked array reductions within the beam core in the neutralizer cell.
- `DataLoader`: Thread-safe cached reader for high-throughput diagnostic postprocessing.

### `plasma_column.plotting`
- Deterministic figure generators with dual `.png` and vector `.pdf` output via `save_figure()`.
- Modular generators for transport phase space, 2D envelopes with beamline element layout schematics, and vector paper figures (`fig01`–`fig05`).

---

## 5. Migration Roadmap & Execution Status

1. **Phase 1: Architecture & Hardening (Completed: RT-01 to RT-12)**
   - Extracted git and metadata logic to `warpx_io.py`.
   - Unified method dispatch in `schema.py`.
   - Thread-safe `DataLoader` caching and dataclass round-trip validation.
   - Cleaned root directory of stale scripts and notebooks into `scripts/` and `archives/`.

2. **Phase 2: Physics & Feature Enhancements (Completed: RT-13 to RT-18)**
   - Region-dependent $K_{\text{eff}}(z)$ in beam envelope integration (`injection_line.py`).
   - Gas target scattering, mean free path, and transmission loss (`gas.py`).
   - Vectorized 2D masked array reduction for $z$-resolved diagnostics (`diagnostics.py`).
   - 2D $(R_x, R_y)$ envelope transport with beamline layout schematic overlay (`transport.py`).
   - Longitudinal slice charge density $\lambda(z)$ and radial space-charge field $E_r(r, z)$ (`beam.py`).
   - Dedicated vector publication figure generators (`paper_figures.py`).
