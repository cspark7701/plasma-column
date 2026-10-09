# Execution Plan Summary: Fix LD_LIBRARY_PATH Conda/GLib Conflict in setup.sh

**Task Index**: 89  
**Date**: 2026-10-09  
**Subject**: `evince paper/manuscript/plasma_column_prab.pdf` failed after `source ./setup.sh` with
`libgobject-2.0.so.0: failed to map segment from shared object`.

---

## 1. Diagnosis

- The PDF was valid (`pdfinfo` reads it); the failure happened in the dynamic loader.
- `setup.sh` prepended `$CONDA_PREFIX/lib` to `LD_LIBRARY_PATH`. The `warpx-dev` env ships its own
  GLib/GObject/Cairo, so system programs loaded conda's copies:

  | `LD_LIBRARY_PATH` | `libgobject-2.0.so.0` used by `/usr/bin/evince` |
  |---|---|
  | as set by old `setup.sh` | `.../miniforge3/envs/warpx-dev/lib/` (fails) |
  | unset | `/lib/x86_64-linux-gnu/` (works, 0 missing libs) |

- Conda binaries find their libraries through RPATH, so exporting the conda lib directory is not needed.
- Secondary issue: the WarpX lib path appeared 2–3 times. Both `setup.sh` and the env's activation hook
  `envs/warpx-dev/etc/conda/activate.d/env_vars.sh` prepend it, and `setup.sh` did so before activation.

## 2. Changes (`setup.sh` only)

1. Removed the block that prepended `$CONDA_PREFIX/lib`; replaced it with a comment explaining why.
2. Added a cleanup step that removes a leftover `$CONDA_PREFIX/lib` entry (from shells that sourced the
   old script) and drops duplicate and empty entries (an empty entry means the current directory).
3. Moved the WarpX `lib` addition after conda activation and made it idempotent.

The conda activation hook outside the repository was **not** modified. It still writes a trailing `:`
(an empty entry) when `LD_LIBRARY_PATH` starts empty, and `setup.sh` now removes that entry.

## 3. Verification

Fresh `env -i` shells, `setup.sh` sourced twice:

| Check | Clean shell | Shell carrying old `LD_LIBRARY_PATH` + empty entry |
|---|---|---|
| Final `LD_LIBRARY_PATH` | `.../warpx/install/lib` (once) | `.../warpx/install/lib` (once) |
| evince → libgobject / libglib | `/lib/x86_64-linux-gnu/` | `/lib/x86_64-linux-gnu/` |
| evince missing libraries | 0 | 0 |
| `import pywarpx, amrex.space3d; from pywarpx import picmi` | OK | OK |
| `import matplotlib, numpy, pandas, scipy` | OK | OK |

Under the new `setup.sh`: `python -m pytest -q` → 129 passed, 1 skipped;
`python scripts/run_case.py --case cases/vacuum.yaml --dry_run` → success;
`python scripts/plasma_column_mcc_picmi_v7.py --dry_run` → success. `bash -n setup.sh` → OK.

## 4. Usage

Open a new terminal (or re-source in the existing one), then:

```bash
source ./setup.sh
evince paper/manuscript/plasma_column_prab.pdf
```

## 5. Limitations

No production WarpX run was executed. Only imports and dry runs were checked. A compiled `warpx.3d`
binary launched outside Python relies on its own RPATH, which this change does not affect.
