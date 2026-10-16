# Simulation Strategies: Parameter Defaults, Storage Optimization, and Disk Usage Guidelines

This document details the simulation parameters, storage footprint breakdown, and recommended configurations for running plasma-column neutralizer PIC simulations in WarpX without exceeding disk capacity.

---

## 1. Root Cause Analysis of High Disk Space Consumption

In WarpX PIC simulations, three diagnostics dictate almost 100% of the disk footprint:

1. **Full 3D Field Diagnostic (`FieldDiagnostic` / `diag1`)**:
   - Dumps $E_x, E_y, E_z, B_x, B_y, B_z, J_x, J_y, J_z, \rho, \text{part\_per\_cell}$ (11 3D mesh arrays).
   - On a $64 \times 64 \times 512$ grid ($\approx 2.1 \times 10^6$ cells), each step dump requires $\sim 180\text{ MB}$.
   - With default `diag_period: 100` over $20{,}000$ steps (vacuum/seeded), this generates **200 dumps $\times$ 180 MB $\approx$ 36 GB** per single case.
   - For callback/MCC cases ($120{,}000$ steps, `diag_period: 600`), 200 dumps also generate **$\approx 36\text{ GB}$** per case.
   - For a 9-case matrix (`method_comparison.yaml`), full field dumps alone consume **over 320 GB**, rapidly exhausting available disk space even on 500 GB drives.

2. **Full Particle Phase Space Diagnostic (`ParticleDiagnostic`)**:
   - Dumps positions $(x, y, z)$, momenta $(u_x, u_y, u_z)$, and weights $w$ for up to tens of millions of macroparticles every `diag_period` (100 or 600 steps), generating tens of GBs per run.

3. **AMReX Checkpoints (`Checkpoint` / `chk<step>/`)**:
   - Dumps complete mesh state, guards, and particle arrays every `checkpoint_period: 2000` (10 checkpoints $\times 2.5\text{ GB} \approx 25\text{ GB}$ per run).

4. **In Contrast: Reduced Diagnostics (`ParticleNumber`, `Timestep`)**:
   - The primary physics quantities of interest ($\eta(t), K_{\text{eff}}/K_0, N_p, N_e, N_i$) are extracted from `reduced_diags/particle_number.txt`, which is only **a few megabytes (text/CSV)**.

---

## 2. Table 1: Current Default Simulation Parameters by Case

> **Superseded (task 94):** Tables 1–3 describe the electromagnetic-solver settings, with which the
> beam never reached the column. Current production settings are in section 6.

| Case Configuration | Method | Grid ($N_x \times N_y \times N_z$) | $N_{\text{steps}}$ | `nppc` (Beam / Plasma) | `diag_period` (Field / Part) | `checkpoint_period` | `reduced_diag_period` | Est. Disk Usage (Per Case) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`vacuum_reference`** | `vacuum` | $64 \times 64 \times 512$ | 20,000 | 16 / 0 | **100** (200 dumps) | **2,000** (10 dumps) | 50 | **~35 – 45 GB** |
| **`seeded_H2_baseline`** | `seeded_compensation` | $64 \times 64 \times 512$ | 20,000 | 16 / 16 | **100** (200 dumps) | **2,000** (10 dumps) | 50 | **~40 – 55 GB** |
| **`seeded_Kr_baseline`** | `seeded_compensation` | $64 \times 64 \times 512$ | 20,000 | 16 / 16 | **100** (200 dumps) | **2,000** (10 dumps) | 50 | **~40 – 55 GB** |
| **`bunched_H2_baseline`** | `seeded_compensation` | $64 \times 64 \times 512$ | 20,000 | 16 / 16 | **100** (200 dumps) | **2,000** (10 dumps) | 50 | **~40 – 55 GB** |
| **`bunched_Kr_baseline`** | `seeded_compensation` | $64 \times 64 \times 512$ | 20,000 | 16 / 16 | **100** (200 dumps) | **2,000** (10 dumps) | 50 | **~40 – 55 GB** |
| **`callback_H2_dynamic`** | `python_callback` | $64 \times 64 \times 512$ | 120,000 | 16 / 16 | **600** (200 dumps) | **10,000** (12 dumps) | 100 | **~50 – 75 GB** |
| **`callback_Kr_dynamic`** | `python_callback` | $64 \times 64 \times 512$ | 120,000 | 16 / 16 | **600** (200 dumps) | **10,000** (12 dumps) | 100 | **~50 – 75 GB** |
| **`cxx_H2_mcc_or_custom`** | `cxx_mcc_custom` | $64 \times 64 \times 512$ | 120,000 | 16 / 16 | **600** (200 dumps) | **10,000** (12 dumps) | 100 | **~50 – 75 GB** |
| **`cxx_Kr_mcc_or_custom`** | `cxx_mcc_custom` | $64 \times 64 \times 512$ | 120,000 | 16 / 16 | **600** (200 dumps) | **10,000** (12 dumps) | 100 | **~50 – 75 GB** |
| **`method_comparison` (Matrix)** | *(All 9 cases)* | $64 \times 64 \times 512$ | 20k / 120k | 16 / 16 | 100 / 600 | 2k / 10k | 50 / 100 | **~450 – 550 GB (Exceeds Disk)** |

---

## 3. Table 2: Recommended Parameters for Production & Disk-Constrained Runs

To keep disk consumption under **15–25 GB for the entire matrix** while preserving full physics accuracy, publication plots, and checkpoint recovery:

| Parameter | Current Default | Recommended (Storage-Optimized Production) | Recommended (Fast / Verification Mode) | Rationale |
| :--- | :---: | :---: | :---: | :--- |
| **`diag_period`** *(Field/Particles)* | **100** (seeded)<br>**600** (MCC) | **5,000** (seeded: 4 dumps)<br>**20,000** (MCC: 6 dumps) | **20,000** (seeded: final dump only)<br>**120,000** (MCC: final dump only) | Reduces 3D plotfiles by **95–98%**. Only initial, transit, and final steady-state snapshots are needed for 2D/3D slice plots. |
| **`checkpoint_period`** | **2,000** (seeded)<br>**10,000** (MCC) | **10,000** (seeded: 2 dumps)<br>**30,000** (MCC: 4 dumps) | **0** (Disabled for clean full runs) | Keeps checkpoints only for crash recovery without accumulating redundant intermediate states. |
| **`reduced_diag_period`** | **50** / **100** | **50** / **100** *(Keep as-is)* | **50** / **100** *(Keep as-is)* | Generates `< 10 MB` total CSV text data. This contains all time-resolved neutralization curves $\eta(t)$ and $K_{\text{eff}}/K_0$. |
| **`nppc_beam`** | **16** | **8 – 16** | **4 – 8** | Halving `nppc_beam` from 16 to 8 halves the particle phase space dump size while preserving clean beam envelope statistics. |
| **`nppc_plasma`** | **16** | **8 – 16** (0 for vacuum) | **4 – 8** (0 for vacuum) | Adequate macroparticle sampling for core density calculation. |
| **Grid ($N_x, N_y, N_z$)** | $64 \times 64 \times 512$ | **$64 \times 64 \times 256$** (optional) | **$32 \times 32 \times 128$** | Reducing $N_z$ from 512 to 256 maintains $\Delta z \approx 1\text{ mm}$ (sufficient for 20 cm column) and cuts mesh size by $2\times$. |
| **`max_steps`** | 20,000 (seeded)<br>120,000 (MCC) | **15,000 – 20,000** (seeded)<br>**60,000 – 80,000** (MCC) | **5,000** (seeded)<br>**20,000** (MCC) | Seeded reaches steady state by step 10,000–15,000 (2 transits). MCC ionization rates saturate well before 120k steps. |

---

## 4. Table 3: Recommended Parameter Values for Each Case File

| Case File | Recommended $N_{\text{steps}}$ | Recommended `diag_period` | Recommended `checkpoint_period` | Recommended `reduced_diag_period` | Expected Disk Footprint |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`cases/vacuum.yaml`** | 20,000 | **10,000** (2 dumps) | **0** or **10,000** | 50 | **~0.6 GB** |
| **`cases/baseline_h2.yaml`** | 20,000 | **5,000** (4 dumps) | **10,000** (2 dumps) | 50 | **~1.5 GB** |
| **`cases/baseline_kr.yaml`** | 20,000 | **5,000** (4 dumps) | **10,000** (2 dumps) | 50 | **~1.5 GB** |
| **`cases/bunched_h2.yaml`** | 20,000 | **5,000** (4 dumps) | **10,000** (2 dumps) | 50 | **~1.5 GB** |
| **`cases/bunched_kr.yaml`** | 20,000 | **5,000** (4 dumps) | **10,000** (2 dumps) | 50 | **~1.5 GB** |
| **`cases/method_comparison.yaml`**<br>• Seeded cases (1–5)<br>• Callback cases (6–7)<br>• C++ MCC cases (8–9) | <br>20,000<br>80,000<br>80,000 | <br>**10,000** (2 dumps)<br>**20,000** (4 dumps)<br>**20,000** (4 dumps) | <br>**10,000**<br>**20,000**<br>**20,000** | <br>50<br>100<br>100 | **Total Matrix: < 20 GB**<br>*(Down from >450 GB)* |
| **`cases/pressure_scan_h2_kr.yaml`** *(12 cases)* | 15,000 | **15,000** (Final dump only) | **0** (Disabled) | 100 | **Total Scan: < 10 GB** |

---

## 5. Summary of Actions to Prevent Disk Exhaustion

1. **Change default `diag_period` in YAML files**:
   - Increase from `100` to `5000` or `10000`. Full 3D plotfile dumps every 100 steps are unneeded because all time-series curves are recorded by `reduced_diag_period: 50`.
2. **Clean past heavy dumps**:
   - Run `bash scripts/cleanup.sh --checkpoints` or `bash scripts/cleanup.sh --all` to recover hundreds of gigabytes before launching production.
3. **Optional CLI Flag in Runner Scripts**:
   - Pass `--checkpoint_period 0` or higher values when running `scripts/run_full_production.sh` or `scripts/run_scan.py`.

---

## 6. Electrostatic Solver Option and Beam Transit Time (2026-10-16, task 93)

The electromagnetic solver fixes `dt = 3.38e-13 s` (light-wave CFL). A 30 keV proton
(`v = 2.40e6 m/s`) then needs about 3.2e5 steps to cross the 0.26 m domain, so the 10 000-step
production runs ended with the beam front at z = -12 mm, before the column (task 92).

Both drivers (`plasma_column_mcc_picmi_v7.py`, `plasma_column_callback_source_picmi_v3.py`) now accept
`--solver es` (labframe electrostatic, `--es_method FFT` with open boundaries by default) and `--dt`.
Without `--dt`, the time step is the smallest of the electron limits
(`plasma_column.constants.estimate_electrostatic_timestep`):

| Limit | Value (production grid, 0.15 T, 10 mA) |
|---|---|
| electron gyration, `omega_ce dt <= 0.25` | **9.48e-12 s** (sets dt) |
| plasma oscillation, `omega_pe dt <= 0.2` at `n_e = n_b = 2.07e15 m^-3` | 7.79e-11 s |
| fastest electron (158 V beam potential + 5 v_th) crosses <= 0.5 cell | 1.64e-11 s |

| Quantity | EM (`cfl=0.5`) | ES (`dt=9.48e-12 s`) |
|---|---|---|
| steps to column end (z = 0.20 m) | ~2.7e5 | 9 700 |
| steps per domain transit | ~3.2e5 | 11 400 |
| beam macroparticle weight, `nppc_beam=16` / `4` | 10.2 / 41 | 287 / 1 150 |
| beam macroparticles in a filled domain, `nppc_beam=4` | ~1.6e8 | 5.9e6 |
| wall time per step, 64x64x512, 8 cores | ~2 s | 1.1 s (measured, first 300 steps) |

Since task 94, `run_case.py` and `run_scan.py` pass `numerics` (grid, `cfl`, `solver`, `es_method`, `dt`,
`nppc_beam`, `nppc_plasma`, `reduced_diag_period`) to the drivers through
`plasma_column.schema.build_numerics_cmd_flags`. `numerics.mcc` is not passed; the method flag decides MCC.
The production case and matrix files use `solver: es`, 23 000 steps for every method, `nppc_beam: 4` and
`diag_period: 2300` (10 snapshots).

The seeded model now loads gas ions at the seed-electron density (`initial_ion_fraction = 1.0`), because an
electron-only seed lost 70 % of its electrons before the beam arrived. With a neutral seed, `eta_net` starts
near 0 and rises as the beam potential (~160 V) expels ions radially (tens of ns for H2+). In the full-grid
check (task 94) the core reached local `eta_net = 0.96` by step 23 000 (0.22 us), with ions depleted from
the beam core (n_i/n_e = 0.15) while global eta_net was only 0.17.
