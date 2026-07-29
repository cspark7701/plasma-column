# AGENTS.md — Plasma Column Neutralizer Simulation Project

## Project

Repository:

- Remote: `https://github.com/cspark7701/plasma_column.git`
- Local working copy: `/home/cspark/Work/projects/plasma_column`
- WarpX source tree used for this project: `/home/cspark/Work/simulation_codes-working/warpx`
- Python environment: conda environment with WarpX/PICMI available

This project develops simulation, theory, diagnostics, and plotting workflows for a compact plasma-assisted space-charge neutralizer for high-current compact-cyclotron axial injection.

The baseline axial-injection layout is:

```text
buncher -> plasma neutralizer -> solenoid -> quadrupole Q1 -> quadrupole Q2 -> spiral inflector
```

Do not describe the baseline neutralizer as being between the solenoid and the inflector. That geometry may be tested only as an explicit alternative-placement study.

## Physics goal

Model whether a compact beam-ionized H2/Kr plasma column can reduce the effective perveance of a 30 keV, multi-mA proton beam before the main solenoid and downstream matching elements.

Primary quantities of interest:

```text
N_p(t), N_e(t), N_i(t)
eta_electron_only = N_e / N_p
eta_net = (N_e - N_i) / N_p
K_eff,electron_only / K0 = 1 - N_e / N_p
K_eff,net / K0 = 1 - (N_e - N_i) / N_p
beam rms size, divergence, emittance, transmission, and loss
```

For a bunched beam, distinguish clearly between:

- average neutralization over the RF period,
- instantaneous peak-bunch neutralization,
- local neutralization inside the plasma-cell volume,
- global particle-count ratios over the full simulation domain.

A global `ParticleNumber` ratio is useful for sanity checks, but it is not sufficient to claim local space-charge neutralization in the beam core.

## Present simulation status and caution

The current public repository contains Python and notebook workflows for plasma-column analysis, particle-number diagnostics, PICMI/WarpX seeded compensation, Python-callback source studies, and C++/MCC-oriented comparisons.

Important limitation to preserve in documentation and code comments:

- WarpX built-in MCC impact ionization is primarily suitable for electron-impact ionization workflows.
- True proton-impact ionization, `p+ + H2 -> p+ + H2+ + e-`, requires either a validated custom source/collision extension or an external source model.
- If using a seeded-compensation model, clearly label it as an analytic/data-driven source estimate, not fully self-consistent proton-impact MCC.

## General development rules

1. Start each task by recording the repository state:

   ```bash
   cd /home/cspark/Work/projects/plasma_column
   git status --short
   git branch --show-current
   git log --oneline -5
   ```

2. Do not overwrite notebooks or scripts without first identifying their role and current outputs.

3. Keep notebooks as front-end analysis and presentation tools. Put reusable physics, I/O, diagnostics, and plotting logic in Python modules.

4. Run WarpX simulations from subprocess calls where practical. Avoid repeatedly constructing multiple WarpX simulations inside one persistent notebook kernel because PyWarpX/WarpX can retain global simulation state.

5. Do not commit large simulation outputs, plotfiles, checkpoint directories, conda environments, or WarpX build artifacts.

6. Do not move or modify the external WarpX source tree unless the task explicitly asks for WarpX-source work.

7. Any change to the modified WarpX source tree must be documented as a patch, with a clear diff against upstream/local baseline.

8. All scripts must support `--dry_run` or an equivalent light test mode.

9. Every production run must write a machine-readable metadata file containing:
   - git commit hash of this repository,
   - path and git commit/diff status of the WarpX source tree,
   - conda environment name,
   - command line,
   - gas species,
   - pressure,
   - column geometry,
   - solenoid field,
   - electrode settings if modeled,
   - beam energy/current/bunch parameters,
   - grid and time-step parameters.

10. Do not silently rescale physics curves. If a plot uses artificial scaling, label it as rescaled or illustrative.

## Recommended repository organization

Adopt the following structure incrementally:

```text
plasma_column/
  AGENTS.md
  README.md
  docs/
    physics_notes/
    literature/
    proceedings/
    slides/
    antigravity_tasks/
  notebooks/
    runs/
      nb_vacuum_reference.ipynb
      nb_seeded_h2.ipynb
      nb_seeded_kr.ipynb
      nb_callback_h2.ipynb
      nb_callback_kr.ipynb
    analysis/
      nb_analysis_plots.ipynb
      nb_bunched_beam_perveance.ipynb
      nb_cross_section_comparison.ipynb
      nb_local_neutralization_profiles.ipynb
  src/
    plasma_column/
      __init__.py
      constants.py
      beam.py
      gas.py
      neutralization.py
      diagnostics.py
      plotting.py
      warpx_io.py
      run_matrix.py
  scripts/
    run_case.py
    run_scan.py
    postprocess_case.py
    make_plots.py
    audit_repo.py
  cases/
    baseline_h2.yaml
    baseline_kr.yaml
    vacuum.yaml
  runs/                 # ignored
  plots/                # generated; usually ignored unless selected figures are copied to docs
  tests/
```

Do not force this refactor in one commit. Preserve working scripts first, then move logic gradually.

## File and data conventions

Use case names that encode the simulation method and gas:

```text
vacuum_reference
seeded_H2_pressure_1e-5Torr
seeded_Kr_pressure_1e-6Torr
callback_H2_dynamic
callback_Kr_dynamic
cxx_H2_mcc
cxx_Kr_mcc
```

Each case directory should contain:

```text
config.yaml
metadata.json
run.log
neutralization_model.csv
neutralization_from_particle_number.csv
local_neutralization.csv
beam_envelope.csv
plots/
```

For notebook-generated plots, always save both:

```text
figure_name.png
figure_name.pdf
```

## Physics checks required before trusting a result

For each simulation case, verify:

1. beam velocity is consistent with 30 keV proton energy,
2. macroparticle weights are physically meaningful,
3. species ordering in `ParticleNumber` is correct,
4. electron and ion counts increase/decrease for the correct physics reason,
5. local neutralization is computed only inside the plasma cell and near the beam core,
6. `K_eff/K0` never becomes negative unless explicitly labeled overcompensation,
7. beam envelope changes are consistent with the sign and magnitude of compensation,
8. neutralization of an RF-bunched beam is not overstated relative to peak-bunch charge,
9. H2 and Kr cross sections are interpolated at the correct collision energy,
10. gas pressure and interaction length do not introduce unacceptable scattering or loss.

## Bunched-beam requirement

The buncher is upstream of the neutralizer. Include an RF-bunched beam model in the physics plan.

Use these definitions:

```text
I_avg      = average beam current
B_f        = bunching factor
I_peak     = B_f * I_avg
T_RF       = 1 / f_RF
Delta_t_b  = bunch phase width / (2*pi*f_RF)
Delta_z_b  = beta*c*Delta_t_b
```

If the plasma reaches only average neutralization, the approximate peak-bunch effective perveance is:

```text
K_eff,peak / K0,peak ~= 1 - eta_avg / B_f
```

This is an important interpretation limit for any H2/Kr neutralization result.

## Coding style

- Use Python 3.10+ compatible syntax unless the conda environment is confirmed to be newer.
- Prefer `pathlib.Path`, `dataclasses`, and explicit units in variable names.
- Avoid hidden global state in reusable modules.
- Use type hints for public functions.
- Use NumPy/Pandas/Matplotlib for analysis.
- Jupyter notebooks are first-class production tools for simulation runs and analysis; use them freely.
- Keep plotting functions deterministic and scriptable.
- Use clear figure labels with units.

## Testing

Add lightweight tests first:

```bash
python -m compileall scripts src tests
pytest -q
python scripts/audit_repo.py --root .
python scripts/run_case.py --case cases/vacuum.yaml --dry_run
python scripts/postprocess_case.py --case-dir runs/example --dry_run
```

For WarpX-specific tests, add a `--small_test` case with very few cells, few steps, and reduced diagnostics only.

## Documentation priorities

Maintain these documents:

```text
README.md
docs/physics_notes/neutralization_model.md
docs/physics_notes/bunched_beam_neutralization.md
docs/physics_notes/h2_kr_cross_sections.md
docs/literature/literature_review.md
docs/warpx_customization.md
docs/proceedings/jacow_outline.md
docs/slides/20min_talk_outline.md
```

## Definition of done for most tasks

A task is complete only when:

1. code changes are committed-ready,
2. dry-run or small test has been executed,
3. generated output path is documented,
4. notebook-facing usage example is provided,
5. physics limitations are stated,
6. a short summary is added to the relevant docs file.
