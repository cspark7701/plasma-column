# Simulation Method Comparison Matrix

## 1. Overview

To model plasma-assisted space-charge neutralization for high-current cyclotron axial injection, four distinct simulation approaches are evaluated across baseline gases ($\text{H}_2$ and $\text{Kr}$) and pressures ($10^{-6}\text{ Torr}$ to $10^{-5}\text{ Torr}$).

---

## 2. Simulation Method Taxonomy

| Method Category | Method Code | Physical Nature | Self-Consistent Collisions? | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline Reference** | `vacuum` | Uncompensated beam propagation in vacuum | No | Reference envelope & space-charge benchmark |
| **Static Seeded Compensation** | `seeded_compensation` | Static analytical background electron density $n_e \approx \eta_{\text{ss}} n_p$ | No | Quick initial perveance reduction estimate |
| **Dynamic Python Callback** | `python_callback` | Dynamic pair creation via Python callback (`sim.user_algorithm_at_step_end`) | Semi-empirical | Dynamic buildup without C++ recompile |
| **Full C++ MCC / Custom Source** | `cxx_mcc_custom` | Particle-in-Cell Monte Carlo Collision tracking of $p^+ + \text{Gas} \rightarrow p^+ + \text{Gas}^+ + e^-$ | **Yes** | Fully self-consistent production simulation |

---

## 3. Comparison Matrix Cases

| Case Name | Gas | Pressure [Torr] | Method Category | Output Directory |
| :--- | :--- | :--- | :--- | :--- |
| `vacuum_reference` | None | $0.0$ | Baseline Reference | `results/vacuum_reference/` |
| `seeded_H2_1e-6Torr` | $\text{H}_2$ | $1.0 \times 10^{-6}$ | Static Analytical Seeded | `results/seeded_H2_1e-6Torr/` |
| `seeded_H2_1e-5Torr` | $\text{H}_2$ | $1.0 \times 10^{-5}$ | Static Analytical Seeded | `results/seeded_H2_1e-5Torr/` |
| `seeded_Kr_1e-6Torr` | $\text{Kr}$ | $1.0 \times 10^{-6}$ | Static Analytical Seeded | `results/seeded_Kr_1e-6Torr/` |
| `seeded_Kr_1e-5Torr` | $\text{Kr}$ | $1.0 \times 10^{-5}$ | Static Analytical Seeded | `results/seeded_Kr_1e-5Torr/` |
| `callback_H2_dynamic` | $\text{H}_2$ | $1.0 \times 10^{-5}$ | Dynamic Source Approximation | `results/callback_H2_dynamic/` |
| `callback_Kr_dynamic` | $\text{Kr}$ | $1.0 \times 10^{-6}$ | Dynamic Source Approximation | `results/callback_Kr_dynamic/` |
| `cxx_H2_mcc_or_custom` | $\text{H}_2$ | $1.0 \times 10^{-5}$ | Full Self-Consistent C++ MCC | `results/cxx_H2_mcc_or_custom/` |
| `cxx_Kr_mcc_or_custom` | $\text{Kr}$ | $1.0 \times 10^{-6}$ | Full Self-Consistent C++ MCC | `results/cxx_Kr_mcc_or_custom/` |

---

## 4. Required Per-Case Output Artifacts

For each completed simulation run, the case directory contains:
- `config.yaml`: Resolved parameters for the run
- `metadata.json`: Machine-readable audit (git hash, conda env, WarpX source diff status)
- `neutralization_from_particle_number.csv`: Particle count time series ($N_p, N_e, N_i, \eta_{\text{net}}, K_{\text{eff}}/K_0$)
- `local_neutralization.csv`: Volume-averaged beam-core densities ($n_p, n_e, n_i, \eta_{\text{net,local}}$)
- `beam_envelope.csv`: Beam RMS size and emittance vs axial position $z$
- `plots/Keff_over_K0.png` & `.pdf`: Perveance ratio evolution figure
- `plots/particle_counts.png` & `.pdf`: Species population buildup figure
- `plots/beam_envelope.png` & `.pdf`: Transverse envelope evolution figure

---

## 5. Execution Commands

To validate matrix configurations and generate metadata without launching long jobs:
```bash
python scripts/run_scan.py --matrix cases/method_comparison.yaml --dry_run
```

To execute full matrix PIC runs:
```bash
python scripts/run_scan.py --matrix cases/method_comparison.yaml --run
```
