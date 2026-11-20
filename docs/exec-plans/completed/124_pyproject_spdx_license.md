# Execution Plan Summary: SPDX License in pyproject.toml

**Task Index**: 124  
**Date**: 2026-11-07  
**Subject**: Remove the setuptools deprecation warning for `project.license` during `pip install -e .`.
setuptools says builds using the TOML-table form will stop being supported by 2027-02-18.

Renumbered from 111 when merged into `main` (index 111 is the CW1 result).

---

## 1. Repository State

`main` @ `f84439b`, clean working tree.

## 2. Changes

`pyproject.toml`:

- `license = {text = "MIT"}` → `license = "MIT"` plus `license-files = ["LICENSE"]`. `LICENSE` is MIT.
- `build-system.requires`: `setuptools>=61.0` → `setuptools>=77.0`, the first version that accepts
  an SPDX string.

## 3. Verification

Editable install with `pip install -v --no-deps -e .` in a scratch venv (Python 3.13, setuptools 84.2.1):

| Tree | License warning | Result |
|---|---|---|
| `f84439b` | Yes (3 times) | Installed |
| This change | None | Installed; `License-Expression: MIT`, `License-File: LICENSE` |

`pytest -q`: 179 passed, 1 skipped.

## 4. Not Reproduced

The pasted log also shows "License classifiers are deprecated" and an "Editable installation" notice.
Neither appeared here with the same or the original `pyproject.toml`. This repository has no license
classifier in `pyproject.toml`, and there is no `setup.py` or `setup.cfg`.

The pasted warnings use the class name `BuildBackendWarning`; the setuptools 84.2.1 here prints
`SetuptoolsDeprecationWarning`, so the machine that produced the log runs a different setuptools.

## 5. Note

`--no-build-isolation` (`docs/warpx_customization.md`) uses the setuptools already in the environment
and does not install the `requires` minimum. That path needs setuptools >= 77 in the environment.

No physics or simulation code changed.
