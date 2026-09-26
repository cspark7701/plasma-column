# Execution Plan Summary: Fix and Rebase WarpX Ion-Impact MCC Patch

**Task Index**: 84  
**Date**: 2026-09-26  
**Subject**: Resolve patch failure for `docs/warpx_patches/warpx_plasma_column_current.patch`, recover missing `IonImpactIonization.H` header, rebase patch onto WarpX `development` (`6b32fecc7`), and document exact build instructions.

---

## 1. Problem Diagnosis & Root Causes

When running `git apply docs/warpx_patches/warpx_plasma_column_current.patch` inside `/home/cspark/Work/simulation_codes-working/warpx`, the command failed with errors on 3 C++ files and `upgrade.sh`:

1. **Missing Core Header File (`IonImpactIonization.H`)**:
   - The original patch added `Source/Particles/Collision/BackgroundMCC/IonImpactIonization.H` to `.gitignore`.
   - Consequently, `git diff` ignored `IonImpactIonization.H`, omitting the crucial 233-line header defining `IonImpactIonizationFilterFunc` and `IonImpactIonizationTransformFunc`.
   - Even if applied, C++ compilation would fail with `fatal error: IonImpactIonization.H: No such file or directory`.
   - Located the original C++ implementation archived under `/home/cspark/Work/projects/plasma_column/simulations/warpx_ion_impact_ionization_patch/Source/Particles/Collision/BackgroundMCC/IonImpactIonization.H`.

2. **Upstream WarpX Codebase Evolution**:
   - The original patch was based on an older development commit (from PR #6588).
   - In upstream `development` (`6b32fecc7`):
     - `Source/Particles/Collision/ScatteringProcess.H`: Added `TWOPRODUCT_REACTION` and `FORWARD` to `ScatteringProcessType` enum, conflicting with the patch hunk that tried to add `FORWARD` again.
     - `Source/Particles/Collision/ScatteringProcess.cpp`: Refactored `parseProcessType` to handle `two_product_reaction` and `forward`, causing context mismatch.
     - `Source/Particles/Collision/BackgroundMCC/BackgroundMCCCollision.cpp`: Removed obsolete include `BinaryCollisionUtils.H` and `TwoProductUtil.H`, causing header hunk failure.

3. **Collision with Existing Files**:
   - `upgrade.sh` was already present as an untracked file in the WarpX tree, causing `upgrade.sh: already exists in working directory`.

---

## 2. Changes Implemented

1. **Archived Missing Header**:
   - Copied [`docs/warpx_patches/IonImpactIonization.H`](file:///home/cspark/Work/projects/plasma-column/docs/warpx_patches/IonImpactIonization.H) into the repository so it is permanently tracked.

2. **Rebased and Regenerated Self-Contained Patch**:
   - Regenerated [`docs/warpx_patches/warpx_plasma_column_current.patch`](file:///home/cspark/Work/projects/plasma-column/docs/warpx_patches/warpx_plasma_column_current.patch) directly against WarpX `development` (`6b32fecc7`):
     - Adds `Source/Particles/Collision/BackgroundMCC/IonImpactIonization.H` as a new file in the patch.
     - Updates `BackgroundMCCCollision.H` & `BackgroundMCCCollision.cpp` with ion-impact ionization hooks and `get_nu_max` signature.
     - Updates `ScatteringProcess.H` & `ScatteringProcess.cpp` with `ION_IMPACT_IONIZATION` enum and robust `#` comment stripping.
     - Excludes `.gitignore` and `upgrade.sh` to prevent collisions.

3. **Updated Documentation**:
   - [`docs/warpx_customization.md`](file:///home/cspark/Work/projects/plasma-column/docs/warpx_customization.md): Documented step-by-step patch application, file verification, and compilation commands.

---

## 3. Verification

1. **Patch Application Verification**:
   - Ran `git apply --check docs/warpx_patches/warpx_plasma_column_current.patch` against clean WarpX `development`: Exited with code 0 (100% clean application, no rejects, no conflicts).
   - Ran `git apply --stat`: 5 files changed, 430 insertions(+), 11 deletions(-).
2. **Repository Unit & CI Tests**:
   - `pytest -q tests/test_warpx_patch_tracking.py`: Passed (3 passed, 1 skipped).
   - `bash scripts/check_github_actions.sh --fast`: Passed (workflow syntax, compileall, and test suite).
