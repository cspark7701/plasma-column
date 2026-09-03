# Production Run Issues — 2026-09-02

**Date recorded**: 2026-09-03  
**Simulation run script**: `run_full_production.sh` (matrix: `cases/method_comparison.yaml`)

Two distinct issues were identified in the full production simulation log. Both are documented below with root cause analysis and recommended fixes.

---

## Issue 1: `yt` 3D Density Grid Extraction Failure — `callback_Kr_dynamic`

### Log Message

```
yt : [INFO] Parameters: domain_dimensions = [ 24  24 128]
Warning: Could not extract 3D density grid arrays from results/callback_Kr_dynamic/diags/diag1002000.
```

### Root Cause

The WarpX plotfile for `callback_Kr_dynamic` only contains **electromagnetic and global grid fields** (`Bx`, `By`, `Bz`, `Ex`, `Ey`, `Ez`, `jx`, `jy`, `jz`, `part_per_cell`, `rho`). It does **not** contain per-species charge density grids such as `rho_beam_protons`, `rho_plasma_electrons`, or `rho_gas_ions`.

The field matching logic in `src/plasma_column/warpx_io.py → load_plotfile_densities()` searches field names for substrings `"electron"`, `"proton"`, `"beam"`, and `"ion"`. Since none of the actual field names match, all three 3D arrays (`ne_3d`, `ni_3d`, `np_3d`) remain zero, and the condition `np.any(plot_data["np_3d"])` fails, triggering the fallback path.

### Underlying Simulation Diagnostic Configuration

Both runner scripts (`plasma_column_callback_source_picmi_v3.py` and `plasma_column_mcc_picmi_v7.py`) configure field diagnostics using:

```python
data_list=["E", "B", "J", "rho", "part_per_cell"]
```

This writes only the **total** rho and aggregate field quantities, not the per-species charge density grids. To extract per-species grids, `rho_<species>` or `particle_density` outputs for each species must be separately requested.

### Impact

- Local 3D diagnostic quantities (`eta_local,net`, `K_eff,local/K0`, radial profiles, z-profiles) are **zeroed out** and effectively placeholder values.
- Global-count–based postprocessing proceeds normally and plots are still generated.
- The explicit fallback warning (`WARNING: local neutralization cannot be inferred from global particle count alone.`) is correctly issued.
- **Plots produced are correctly labeled** as global-count estimates.

### Recommended Fix

To recover per-species 3D densities, add per-species field output to the WarpX diagnostic configuration. For example, in the PICMI scripts change:

```python
# Before:
data_list=["E", "B", "J", "rho", "part_per_cell"],

# After:
data_list=["E", "B", "J", "rho", "part_per_cell"],
# plus per-species particle diagnostics or check WarpX rho_<species> support
```

Alternatively, per-species particle diagnostics (already configured for particle position/momentum/weight) can be used to reconstruct density profiles via histogram binning in postprocessing. A future task should implement this path in `warpx_io.py`.

---

## Issue 2: WarpX Assertion Crash — `cxx_H2_mcc_or_custom` (`ScatteringProcess.cpp:71`)

### Log Message

```
[INFO] electron_impact: using H/ cross-section data as H2 fallback:
  /home/cspark/Work/simulation_codes-working/warpx-data/MCC_cross_sections/H/electron_impact_ionization.dat
Initializing AMReX ...
Assertion `(getCrossSection(m_exe_h.m_energy_penalty) == 0)' failed,
  file "Source/Particles/Collision/ScatteringProcess.cpp", line 71
### ERROR: Cross-section > 0 at energy cost for collision.
SIGABRT
Error: Simulation failed for cxx_H2_mcc_or_custom (exit code 6)
```

### Root Cause — WarpX Assertion

`ScatteringProcess.cpp:71` enforces the requirement that the cross-section must be **exactly zero** at the energy cost (ionization threshold), because a nonzero value would allow a collision event that leaves the colliding particle with negative kinetic energy:

```cpp
if (m_exe_h.m_energy_penalty > 0) {
    WARPX_ALWAYS_ASSERT_WITH_MESSAGE(
        (getCrossSection(m_exe_h.m_energy_penalty) == 0),
        "Cross-section > 0 at energy cost for collision."
    );
}
```

`getCrossSection()` performs linear interpolation on the uniformly-spaced energy grid.

### Cross-Section Data Analysis

The H electron-impact ionization file:
```
/warpx-data/MCC_cross_sections/H/electron_impact_ionization.dat
```

| Parameter | Value |
|---|---|
| First energy (grid start) | 13.59844 eV |
| Grid spacing dE | 0.26649 eV |
| Total entries | 75,000 |
| First cross section (at 13.60 eV) | 0.0 (zero, correct) |
| H2 ionization threshold configured | **15.43 eV** (set in `gas_ionization_energy_eV()`) |
| Interpolated σ at **15.43 eV** | **9.82 × 10⁻²² m²** ← **nonzero → assertion fails** |

The cross-section data file uses the H ionization threshold (~13.6 eV) as its zero point. The configured ionization energy penalty for H2 is **15.43 eV**, which falls well into the rising portion of the cross-section curve. WarpX requires `σ(E_threshold) == 0` exactly.

### Configured Value vs. Data File Zero

In `scripts/plasma_column_mcc_picmi_v7.py`:

```python
def gas_ionization_energy_eV(cfg: PlasmaColumnConfig) -> float:
    # First ionization energies, used only for electron-impact MCC.
    return 15.43 if cfg.gas == "H2" else 14.00
```

The H cross-section file (used as H2 fallback) has its zero crossing at **13.598 eV** (H atom ionization potential). Setting `energy_penalty = 15.43 eV` causes the assertion to fire because `σ(15.43 eV) ≈ 9.82 × 10⁻²² m² ≠ 0`.

### Impact

- The `cxx_H2_mcc_or_custom` simulation **crashes on startup** before any PIC steps are executed.
- No diagnostic output is produced for this case.

### Recommended Fix

There are two correct approaches:

**Option A — Match energy threshold to data file zero crossing (preferred)**

Set `energy_penalty` for H2 to the H data file's actual zero-crossing energy:

```python
def gas_ionization_energy_eV(cfg: PlasmaColumnConfig) -> float:
    # H cross-section file (used as H2 fallback) has its zero at 13.598 eV.
    # WarpX requires sigma(E_threshold) == 0 exactly.
    return 13.60 if cfg.gas == "H2" else 14.00
```

> **Caveat**: This uses H atomic ionization potential (13.6 eV) as a proxy for H2 molecular ionization (15.43 eV). The threshold mismatch introduces a ~12% bias in the collision energy budget. This should be clearly labeled as an approximation pending a proper H2 electron-impact cross-section file.

**Option B — Supply a proper H2 electron-impact cross-section file**

Generate or obtain a validated H2 electron-impact ionization cross-section file with its zero starting at exactly **15.43 eV**. Place it at:

```
/warpx-data/MCC_cross_sections/H2/electron_impact_ionization.dat
```

This is the physically correct solution. The current file in `H/` is for atomic hydrogen, not H2 molecular gas.

### Physics Limitation Notice

The current `electron_impact` MCC mode using the H atomic cross-section file as an H2 fallback is a known approximation. This must be clearly stated in any report or publication:

> **Warning**: The `cxx_H2_mcc_or_custom` case uses H atomic electron-impact ionization cross sections as a fallback for H2. This is a coarse approximation and is **not physically equivalent** to H2 electron-impact ionization. Results from this simulation method should be interpreted with this caveat.

---

## Summary Table

| Issue | Case | Status | Priority |
|---|---|---|---|
| yt field name mismatch → 3D density not extracted | `callback_Kr_dynamic` | Postprocessing degrades to global counts; plots are generated but without local profiles | Medium |
| WarpX σ(E_threshold) ≠ 0 → assertion crash | `cxx_H2_mcc_or_custom` | Simulation fails to start; no PIC output | High |

---

## Follow-Up Tasks

1. **Fix `gas_ionization_energy_eV()` for H2** to match H cross-section data file threshold (13.60 eV) as a stopgap, and document it as an approximation.
2. **Obtain or generate a proper H2 electron-impact cross-section file** with threshold at 15.43 eV.
3. **Add per-species charge density output** (`rho_<species>`) to PICMI field diagnostic `data_list` for all simulation cases, enabling local 3D core diagnostics.
4. **Improve `load_plotfile_densities()`** to also parse WarpX particle diagnostics (position + weight histograms) as an alternative density grid source when per-species field grids are absent.
