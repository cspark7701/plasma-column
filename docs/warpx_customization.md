# WarpX Customization and Patch Tracking Guide

## 1. WarpX Source Tree Information

- **Local Path**: `/home/cspark/Work/simulation_codes-working/warpx`
- **Git Branch**: `development` (commit `6b32fecc7`)
- **Remote**: `origin/development` (`https://github.com/BLAST-WarpX/warpx.git`)
- **Exported Patch Location**: [`docs/warpx_patches/warpx_plasma_column_current.patch`](file:///home/cspark/Work/projects/plasma-column/docs/warpx_patches/warpx_plasma_column_current.patch)
- **Standalone Custom Header**: [`docs/warpx_patches/IonImpactIonization.H`](file:///home/cspark/Work/projects/plasma-column/docs/warpx_patches/IonImpactIonization.H)

---

## 2. Overview of Modifications

The local WarpX C++ source code includes custom extensions to support **ion-impact ionization** within the Monte Carlo Collision (MCC) module.

Built-in WarpX MCC is designed for electron-impact collisions ($e^- + \text{Gas} \rightarrow e^- + \text{Gas}^+ + e^-$). High-current proton beam neutralizer modeling requires simulating energetic proton-impact ionization directly:

$$p^+ + \text{Gas} \rightarrow p^+ + \text{Gas}^+ + e^-$$

---

## 3. Detailed File Modification Audit

The self-contained patch modifies 4 C++ files and adds 1 new header file (5 files total):

### 3.1 `Source/Particles/Collision/BackgroundMCC/IonImpactIonization.H` (New Header)
- Defines `IonImpactIonizationFilterFunc` for particle rejection sampling against neutral gas density $n_a(x,y,z,t)$ and interpolated center-of-mass cross section $\sigma_i(E_{\text{coll}})$.
- Defines `IonImpactIonizationTransformFunc` to subtract ionization energy from the projectile ion, generate a secondary electron with isotropic kinetic energy ($E_{e,\text{sec}} \approx 1\text{ eV}$), and generate a thermal background gas ion sampled from the neutral gas temperature.

### 3.2 `Source/Particles/Collision/ScatteringProcess.H` & `ScatteringProcess.cpp`
- **Enum Additions**: Added `ION_IMPACT_IONIZATION` to `ScatteringProcessType` enum.
- **Parsing**: Added parsing for `"ion_impact_ionization"` process strings in Python/PICMI scripts and inputs files.
- **Robust Comment Handling**: Updated `readCrossSectionFile()` to strip comment lines starting with `#` and ignore blank lines when loading cross-section data files.

### 3.3 `Source/Particles/Collision/BackgroundMCC/BackgroundMCCCollision.H` & `BackgroundMCCCollision.cpp`
- **Ion-Impact Handler**: Implemented `doBackgroundIonImpactIonization()` method using AMReX particle filtering and transformation (`filterCopyTransformParticles<1>`).
- **Collision Frequencies**: Updated `BackgroundMCCCollision::doCollisions()` to compute maximum ion-impact collision frequencies $\nu_{\text{max,ion\_impact}}$ and probability $P = 1 - \exp(-\nu_{\text{max}} \Delta t)$.
- **Particle Copy Factories**: Configured smart copy factories to generate secondary electron species and secondary gas ion species at the projectile particle position with thermal gas energy + secondary energy partition.

---

## 4. How to Apply the Patch and Build WarpX

### 4.1 Apply Patch to WarpX
From the WarpX source directory:

```bash
cd /home/cspark/Work/simulation_codes-working/warpx

# 1. Ensure working tree is clean
git checkout development

# 2. Check patch applicability (dry run)
git apply --check /home/cspark/Work/projects/plasma-column/docs/warpx_patches/warpx_plasma_column_current.patch

# 3. Apply the patch
git apply /home/cspark/Work/projects/plasma-column/docs/warpx_patches/warpx_plasma_column_current.patch

# 4. Verify modified files
git status --short
# Expected output:
#  M Source/Particles/Collision/BackgroundMCC/BackgroundMCCCollision.H
#  M Source/Particles/Collision/BackgroundMCC/BackgroundMCCCollision.cpp
#  M Source/Particles/Collision/ScatteringProcess.H
#  M Source/Particles/Collision/ScatteringProcess.cpp
# ?? Source/Particles/Collision/BackgroundMCC/IonImpactIonization.H
```

### 4.2 Compile and Install WarpX / PyWarpX

Activate the project conda environment and rebuild:

```bash
conda activate warpx-dev
cd /home/cspark/Work/simulation_codes-working/warpx

# If using existing build tree:
cmake --build build -j 8 --target install
cmake --build build -j 8 --target pip_install

# Or clean rebuild via pip:
python -m pip install -e . --no-build-isolation
```

---

## 5. Machine-Readable Metadata Tracking

Every simulation run executed via `scripts/run_case.py` or `scripts/run_scan.py` automatically writes `metadata.json` containing:
- WarpX source path (`/home/cspark/Work/simulation_codes-working/warpx`)
- WarpX git commit hash (`6c04a74dc`)
- WarpX git branch (`development`)
- WarpX dirty status and list of modified files

This guarantees full auditability and reproducibility for every simulation result.

---

## 6. Verification and Benchmarking Suite

The verification suite for custom ion-impact MCC is implemented in [`scripts/run_mcc_verification.py`](file:///home/cspark/Work/projects/plasma-column/scripts/run_mcc_verification.py) and [`scripts/analyze_mcc_verification.py`](file:///home/cspark/Work/projects/plasma-column/scripts/analyze_mcc_verification.py).

### Summary of Verification Tests
1. **Test 1 — No-gas test**: Verified zero ionization rate when $p = 0$.
2. **Test 2 — Zero cross-section test**: Verified zero ionization rate when $\sigma_i = 0$.
3. **Test 3 — Fixed cross-section rate test**: Verified ionization rate matches analytical $dN_e/dt = N_p n_{\text{gas}} \sigma_i v_p$.
4. **Test 4 — H2 vs Kr cross-section ratio**: Verified secondary electron creation ratio matches $\sigma_{\text{Kr}}/\sigma_{\text{H}_2}$.
5. **Test 5 — Time-step convergence**: Verified collision probability $P = 1 - \exp(-n_{\text{gas}} \sigma_i v_p \Delta t)$ converges as $\Delta t \to 0$.
6. **Test 6 — Macroparticle weight conservation**: Verified physical particle count $N_{\text{phys}} = w \cdot N_{\text{macro}}$.
7. **Test 7 — Energy bookkeeping**: Verified secondary electron energy assignment ($E_{e,\text{sec}} \approx 10\text{ eV}$).

For detailed verification results, see [`docs/verification/custom_ion_impact_mcc_validation.md`](file:///home/cspark/Work/projects/plasma-column/docs/verification/custom_ion_impact_mcc_validation.md).

