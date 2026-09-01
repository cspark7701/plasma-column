# Full Installation Guide: `plasma-column` + Patched WarpX + Patched warpx-data

This guide installs all three components required for full PIC simulation capability:

| Component | Role | Source |
|---|---|---|
| `plasma-column` | Physics package, diagnostics, plotting | `github.com/cspark7701/plasma-column` |
| `warpx` (patched) | PIC engine with custom ion-impact MCC | `github.com/BLAST-WarpX/warpx` + patch |
| `warpx-data` (patched) | H₂ / Kr proton-impact cross-section tables | `github.com/BLAST-WarpX/warpx-data` + custom tables |

> **Note:** Analytics, diagnostics, and all plotting modules work **without WarpX** (101 tests pass standalone). Only the `cxx_mcc_custom` simulation method requires the patched WarpX build.

---

## Prerequisites

- Linux (Ubuntu 20.04+, RHEL 8+) or macOS 12+
- `conda` / `mamba` — [Miniforge installer](https://github.com/conda-forge/miniforge)
- `git`
- C++ compiler: `g++ >= 9` or `clang++ >= 11` with C++17 support
- `cmake >= 3.20`

Check your compiler and cmake:
```bash
g++ --version
cmake --version
```

---

## Directory Layout

All three components live side-by-side under a common working directory:

```text
~/Work/simulation_codes-working/
├── warpx/                    # Patched WarpX source (built in-place)
└── warpx-data/               # Upstream cross-section data + proton-impact tables

~/Work/projects/
└── plasma-column/            # This project
    └── warpx_proton_impact_cross_sections_linear/
        └── MCC_cross_sections/
            ├── H2/proton_impact_ionization.dat
            └── Kr/proton_impact_ionization.dat
```

---

## Step 1 — Clone `plasma-column`

```bash
cd ~/Work/projects
git clone https://github.com/cspark7701/plasma-column.git
cd plasma-column
```

---

## Step 2 — Create & Activate the Conda Environment

The [`environment.yml`](./environment.yml) pins Python ≥ 3.10, all runtime dependencies,
and installs `plasma_column` in editable mode automatically.

```bash
# Create the environment
conda env create -f environment.yml

# Activate
conda activate warpx-dev
```

> **Updating an existing environment:**
> ```bash
> conda env update -f environment.yml --prune
> ```

Verify the base installation:

```bash
python -c "import plasma_column; print(plasma_column.__version__)"
# → 1.0.0

pytest -q
# → 101 passed, 0 warnings
```

---

## Step 3 — Clone and Patch WarpX

### 3.1 Clone WarpX at the pinned commit

```bash
cd ~/Work/simulation_codes-working
git clone https://github.com/BLAST-WarpX/warpx.git
cd warpx
git checkout 6c04a74dc    # pinned: "Implement reflection from embedded boundaries"
```

### 3.2 Apply the plasma-column patch

The patch modifies **5 C++ source files** and adds **2 helper files** (7 total):

**Modified C++ source files:**

| File | What changes |
|---|---|
| `BackgroundMCCCollision.H` | New `doBackgroundIonImpactIonization()` method; updated `get_nu_max()` signature with `mass_for_energy` param; new private members for ion-impact state |
| `BackgroundMCCCollision.cpp` | New includes (`IonImpactIonization.H`, `KineticEnergy.H`, etc.); `doCollisions()` dispatches ion-impact channel with $P=1-e^{-\nu_\max \Delta t}$; full `doBackgroundIonImpactIonization()` using `filterCopyTransformParticles` |
| `ScatteringProcess.H` | Adds `ION_IMPACT_IONIZATION` and `FORWARD` to `ScatteringProcessType` enum |
| `ScatteringProcess.cpp` | `parseProcessType()` recognises `"ion_impact_ionization"`; `readCrossSectionFile()` rewritten to skip `#` comments/blank lines with improved error messages |
| `.gitignore` | Excludes build artefacts (`build/`, `install/`, `patch/`, `*.orig`, `upgrade.sh`, etc.) |

**New helper files added by patch:**

| File | Purpose |
|---|---|
| `INSTALL.md` | Full cmake build recipe — cmake configure, build, install, and pip_install steps with all required flags |
| `upgrade.sh` | Rebuild script for iterative development — cleans `build/` and `install/`, re-runs cmake + build + install + pip_install |

```bash
# From inside the warpx/ directory
git apply ~/Work/projects/plasma-column/docs/warpx_patches/warpx_plasma_column_current.patch
```

No output = success. Verify:

```bash
git diff --stat
# 5 files changed: .gitignore, BackgroundMCCCollision.H/cpp, ScatteringProcess.H/cpp
# 2 new files created: INSTALL.md, upgrade.sh
```

### 3.3 Build and install WarpX (full cmake build)

The patch includes `INSTALL.md` with the authoritative build recipe. Follow it exactly:

```bash
conda activate warpx-dev
cd ~/Work/simulation_codes-working/warpx

# 1. Configure (all dimensions + FFT + Python bindings)
cmake -S . -B build \
    -DWarpX_DIMS="1;2;3;RZ;RCYLINDER;RSPHERE" \
    -DWarpX_FFT=ON \
    -DWarpX_PYTHON=ON \
    -DCMAKE_PREFIX_PATH=$CONDA_PREFIX \
    -DHDF5_ROOT=$CONDA_PREFIX \
    -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    -DCMAKE_INSTALL_PREFIX=$(pwd)/install \
    2>&1 | tee warpx.cmake.out

# 2. Build (~10–30 minutes; adjust -j to your CPU count)
cmake --build build -j 4 2>&1 | tee warpx.build.out

# 3. Install binaries to install/
cmake --build build -j 4 --target install 2>&1 | tee warpx.install.out

# 4. Install PyWarpX Python package into the conda env
cmake --build build -j 4 --target pip_install 2>&1 | tee warpx.pip_install.out
```

> **Rebuilding after source changes** — use the provided `upgrade.sh` script:
> ```bash
> bash upgrade.sh
> ```
> It cleans `build/` and `install/`, then runs all four cmake steps in sequence.

### 3.4 Create convenience symlinks for executables

```bash
cd ~/Work/simulation_codes-working/warpx/install/bin
ln -sf warpx.2d.MPI.OMP.DP.PDP.OPMD.FFT.EB.QED warpx.2d
ln -sf warpx.1d.MPI.OMP.DP.PDP.OPMD.FFT.EB.QED warpx.1d
ln -sf warpx.rcylinder.MPI.OMP.DP.PDP.OPMD.FFT.EB.QED warpx.rcylinder
ln -sf warpx.rz.MPI.OMP.DP.PDP.OPMD.FFT.EB.QED warpx.rz
ln -sf warpx.rsphere.MPI.OMP.DP.PDP.OPMD.FFT.EB.QED warpx.rsphere
```

### 3.5 Verify WarpX

```bash
python -c "import pywarpx; print('pywarpx OK:', pywarpx.__file__)"
```

Or run the project's full environment audit:

```bash
cd ~/Work/projects/plasma-column
python scripts/print_environment.py
```

Expected output:
```
[Package Dependencies]
  plasma_column     : 1.0.0
  numpy             : x.x.x
  ...

[WarpX / PyWarpX Interface]
  pywarpx import    : OK
  pywarpx location  : .../warpx-dev/lib/python3.x/site-packages/pywarpx/__init__.py

[WarpX Source Tree]
  Branch            : development
  Commit            : 6c04a74dc
  Status            : Modified         ← confirms patch is applied
```

---

## Step 4 — Clone and Patch warpx-data

### 4.1 Clone warpx-data

```bash
cd ~/Work/simulation_codes-working
git clone https://github.com/BLAST-WarpX/warpx-data.git
```

### 4.2 Add the proton-impact cross-section tables

Upstream `warpx-data` ships electron-impact cross sections only. The plasma-column project
adds custom **proton-impact ionization** tables for H₂ and Kr. These are already included in
the project repository at:

```
plasma-column/
└── warpx_proton_impact_cross_sections_linear/
    └── MCC_cross_sections/
        ├── H2/proton_impact_ionization.dat
        └── Kr/proton_impact_ionization.dat
```

The `plasma_column` package reads them directly from the project root — **no additional setup
is required**. The `CrossSectionDatabase` class in `gas.py` resolves this path automatically.

Optionally, copy the tables into your local `warpx-data` clone for unified access:

```bash
cp -r ~/Work/projects/plasma-column/warpx_proton_impact_cross_sections_linear/MCC_cross_sections/H2 \
      ~/Work/simulation_codes-working/warpx-data/warpx_proton_impact_cross_sections/MCC_cross_sections/

cp -r ~/Work/projects/plasma-column/warpx_proton_impact_cross_sections_linear/MCC_cross_sections/Kr \
      ~/Work/simulation_codes-working/warpx-data/warpx_proton_impact_cross_sections/MCC_cross_sections/
```

### 4.3 Verify cross-section data

```bash
cd ~/Work/projects/plasma-column
python -c "
from plasma_column.gas import CrossSectionDatabase
db = CrossSectionDatabase()
s_h2 = db.get_proton_impact_cross_section('H2', 30000.0)
s_kr  = db.get_proton_impact_cross_section('Kr',  30000.0)
print(f'H2  sigma = {s_h2:.4e} m^2')
print(f'Kr  sigma = {s_kr:.4e} m^2')
print(f'Ratio (Kr/H2) = {s_kr/s_h2:.2f}x')
"
```

Expected output:
```
H2  sigma = 1.6135e-20 m^2
Kr  sigma = 8.9648e-20 m^2
Ratio (Kr/H2) = 5.56x
```

---

## Step 5 — Final Verification

```bash
cd ~/Work/projects/plasma-column
conda activate warpx-dev

# 1. Full unit test suite
pytest -q
# → 101 passed, 0 warnings

# 2. Repository health audit
python scripts/audit_repo.py --root .
# → Audit Completed Successfully

# 3. Dry-run simulation cases (exercises full schema + warpx path resolution)
python scripts/run_case.py --case cases/baseline_h2.yaml --dry_run
python scripts/run_case.py --case cases/baseline_kr.yaml --dry_run

# 4. Full environment report
python scripts/print_environment.py
```

---

## Installation Checklist

- [ ] `plasma-column` cloned to `~/Work/projects/plasma-column`
- [ ] `conda env create -f environment.yml` completed successfully
- [ ] `import plasma_column` → version `1.0.0`
- [ ] `pytest -q` → **101 passed, 0 warnings**
- [ ] WarpX cloned and checked out at commit `6c04a74dc`
- [ ] `git apply .../warpx_plasma_column_current.patch` → no errors; 5 files changed + 2 new files (INSTALL.md, upgrade.sh)
- [ ] cmake configure, build, install, pip_install steps completed without errors
- [ ] `import pywarpx` → OK
- [ ] `warpx-data` cloned to `~/Work/simulation_codes-working/warpx-data`
- [ ] Cross-section check: H₂ σ = 1.6135×10⁻²⁰ m², Kr/H₂ ratio = 5.56×

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `git apply` fails with `error: patch failed` | Ensure exact commit: `git checkout 6c04a74dc` |
| cmake configure fails | Check `cmake --version` (≥ 3.20), `g++ --version` (≥ 9), and that `conda activate warpx-dev` is active |
| `import pywarpx` raises `ImportError` | Activate `warpx-dev` env; re-run `cmake --build build --target pip_install` from warpx source dir |
| `FileNotFoundError` for `.dat` cross-section files | Verify `warpx_proton_impact_cross_sections_linear/MCC_cross_sections/H2/` exists in project root |
| MPI / CUDA warnings on startup | `export OMPI_MCA_opal_cuda_support=false` |
| `conda env create` fails (env already exists) | `conda env remove -n warpx-dev` then recreate |
