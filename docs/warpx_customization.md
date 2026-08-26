# WarpX Customization and Patch Tracking Guide

## 1. WarpX Source Tree Information

- **Local Path**: `/home/cspark/Work/simulation_codes-working/warpx`
- **Git Branch**: `development`
- **Base Commit**: `6c04a74dc` ("Implement reflection from embedded boundaries (#6588)")
- **Remote**: `origin/development`
- **Exported Patch Location**: [`docs/warpx_patches/warpx_plasma_column_current.patch`](file:///home/cspark/Work/projects/plasma-column/docs/warpx_patches/warpx_plasma_column_current.patch)

---

## 2. Overview of Modifications

The local WarpX C++ source code includes custom extensions to support **ion-impact ionization** within the Monte Carlo Collision (MCC) module.

Built-in WarpX MCC is designed for electron-impact collisions ($e^- + \text{Gas} \rightarrow e^- + \text{Gas}^+ + e^-$). High-current proton beam neutralizer modeling requires simulating energetic proton-impact ionization directly:

$$p^+ + \text{Gas} \rightarrow p^+ + \text{Gas}^+ + e^-$$

---

## 3. Detailed File Modification Audit

### 3.1 `Source/Particles/Collision/ScatteringProcess.H` & `ScatteringProcess.cpp`
- **Enum Additions**: Added `ION_IMPACT_IONIZATION` and `FORWARD` to `ScatteringProcessType` enum.
- **Parsing**: Added parsing for `"ion_impact_ionization"` process strings in Python/inputs files.
- **Robust Comment Handling**: Updated `readCrossSectionFile()` to strip comment lines starting with `#` and ignore blank lines when loading cross-section data files.

### 3.2 `Source/Particles/Collision/BackgroundMCC/BackgroundMCCCollision.H` & `BackgroundMCCCollision.cpp`
- **Ion-Impact Handler**: Implemented `doBackgroundIonImpactIonization()` method using AMReX particle filtering and transformation (`filterCopyTransformParticles`).
- **Collision Frequencies**: Updated `BackgroundMCCCollision::doCollisions()` to compute maximum ion-impact collision frequencies $\nu_{\text{max,ion\_impact}}$ and probability $P = 1 - \exp(-\nu_{\text{max}} \Delta t)$.
- **Particle Copy Factories**: Configured smart copy factories to generate secondary electron species and secondary gas ion species at the projectile particle position with thermal gas energy + secondary energy partition.

---

## 4. Building PyWarpX with Custom C++ Extensions

To build PyWarpX with these C++ modifications enabled:

```bash
cd /home/cspark/Work/simulation_codes-working/warpx
conda activate warpx-dev

# Clean previous build artifacts
rm -rf build

# Configure and compile Python bindings
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

