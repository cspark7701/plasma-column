# Notebook Workflow — Production Running Order

This document describes the correct sequential order for running all Jupyter
notebooks in the `plasma-column` project for a full production cycle, from
environment verification through simulation, analysis, and figure generation.

---

## Prerequisites

```bash
conda activate warpx-dev
cd ~/Work/projects/plasma-column

# Confirm package and environment are healthy
python scripts/print_environment.py
pytest -q          # → 101 passed, 0 warnings
```

---

## Overview: Three Stages

```
Stage 1 — Simulations (notebooks/runs/)
    ↓  writes to: runs/
Stage 2 — Analysis (notebooks/analysis/)
    ↓  reads from: runs/  writes to: plots/, paper/
Stage 3 — Cross-cutting (standalone)
    ↓  reads from: data/, runs/
```

---

## Stage 1 — Simulation Runs (`notebooks/runs/`)

Run these notebooks to execute WarpX simulations and produce raw output data.
Each notebook configures and launches one simulation case.

| Order | Notebook | Case | Script | Output Dir |
|---|---|---|---|---|
| 1 | [`nb_vacuum_reference.ipynb`](../notebooks/runs/nb_vacuum_reference.ipynb) | Vacuum reference (no neutralizer) | `plasma_column_mcc_picmi_v7.py` | `runs/vacuum_reference/` |
| 2 | [`nb_seeded_h2.ipynb`](../notebooks/runs/nb_seeded_h2.ipynb) | Seeded plasma, H₂ at 1×10⁻⁵ Torr | `plasma_column_mcc_picmi_v7.py` | `runs/seeded_H2_1e-5Torr/` |
| 3 | [`nb_seeded_kr.ipynb`](../notebooks/runs/nb_seeded_kr.ipynb) | Seeded plasma, Kr at 1×10⁻⁶ Torr | `plasma_column_mcc_picmi_v7.py` | `runs/seeded_Kr_1e-6Torr/` |
| 4 | [`nb_callback_h2.ipynb`](../notebooks/runs/nb_callback_h2.ipynb) | Python-callback source, H₂ | `plasma_column_callback_source_picmi_v3.py` | `runs/callback_H2_dynamic/` |
| 5 | [`nb_callback_kr.ipynb`](../notebooks/runs/nb_callback_kr.ipynb) | Python-callback source, Kr | `plasma_column_callback_source_picmi_v3.py` | `runs/callback_Kr_dynamic/` |
| 6 | [`nb_parameter_scan.ipynb`](../notebooks/runs/nb_parameter_scan.ipynb) | Multi-case parameter scan matrix | `run_scan.py` + `ScanMatrix` | `runs/<scan_name>/` |

> **Notes:**
> - Notebooks 1–5 are independent and can run in parallel if compute resources allow.
> - Notebook 6 (parameter scan) depends on cases defined in `cases/` YAML files
>   (`method_comparison.yaml`, `pressure_scan_h2_kr.yaml`, etc.) and internally
>   submits each case as a subprocess. It must be run **after** verifying the
>   baseline runs (1–5) complete successfully.
> - Each notebook has a `--dry_run` mode (set `DRY_RUN = True` in the config cell)
>   to validate parameters and write `metadata.json` without launching WarpX.

---

## Stage 2 — Analysis (`notebooks/analysis/`)

Run these notebooks **after** Stage 1 output directories are populated.

| Order | Notebook | Reads From | Produces |
|---|---|---|---|
| 7 | [`nb_analysis_plots.ipynb`](../notebooks/analysis/nb_analysis_plots.ipynb) | `runs/` (auto-discovers all cases) | Species populations, η(t), K_eff/K₀ curves → `plots/` |
| 8 | [`nb_local_neutralization_profiles.ipynb`](../notebooks/analysis/nb_local_neutralization_profiles.ipynb) | `runs/` (WarpX field arrays) | Radial density profiles, η(z) axial maps → `plots/` |
| 9 | [`nb_bunched_beam_perveance.ipynb`](../notebooks/analysis/nb_bunched_beam_perveance.ipynb) | `runs/` + `data/` | K_eff,peak/K₀ vs bunching factor, λ(z), E_r(r,z) → `plots/` |
| 10 | [`nb_cross_section_comparison.ipynb`](../notebooks/analysis/nb_cross_section_comparison.ipynb) | `warpx_proton_impact_cross_sections_linear/` | σ(E) comparison plots, 30 keV highlight → `plots/` |
| 11 | [`nb_parameter_scan_analysis.ipynb`](../notebooks/analysis/nb_parameter_scan_analysis.ipynb) | `runs/` (scan subdirs) | Scan comparison bars, heatmaps, η vs pressure → `plots/` |
| 12 | [`nb_extended_visualizations.ipynb`](../notebooks/analysis/nb_extended_visualizations.ipynb) | `runs/`, `plots/` | Extended transport, envelope Rx/Ry, schematic → `plots/` |

> **Notes:**
> - Notebooks 7–10 are independent and can run in any order once Stage 1 is complete.
> - Notebook 11 (scan analysis) requires notebook 6 (parameter scan) to have completed.
> - Notebook 12 (extended visualizations) should run last in Stage 2 — it may reference
>   figures already produced by notebooks 7–10.

---

## Stage 3 — Consolidated Pipeline (Optional)

The consolidated pipeline notebook runs the full sequence (environment audit →
scan → post-processing → figures → tables → transport → audit) in a single session:

| Notebook | Purpose |
|---|---|
| [`nb_full_production_pipeline.ipynb`](../notebooks/nb_full_production_pipeline.ipynb) | End-to-end pipeline: mirrors all 8 steps of `scripts/run_full_production.sh` |

Run this as an alternative to Stages 1 + 2 above when a fully automated,
single-session execution is preferred.

---

## Full Running Order at a Glance

```
[Environment Check]
  → pytest -q + print_environment.py

[Stage 1: Simulations]
  1. nb_vacuum_reference     (runs/vacuum_reference/)
  2. nb_seeded_h2            (runs/seeded_H2_1e-5Torr/)
  3. nb_seeded_kr            (runs/seeded_Kr_1e-6Torr/)
  4. nb_callback_h2          (runs/callback_H2_dynamic/)
  5. nb_callback_kr          (runs/callback_Kr_dynamic/)
  6. nb_parameter_scan       (runs/<scan_name>/)        ← after 1–5

[Stage 2: Analysis]
  7.  nb_analysis_plots
  8.  nb_local_neutralization_profiles
  9.  nb_bunched_beam_perveance
  10. nb_cross_section_comparison
  11. nb_parameter_scan_analysis                        ← after 6
  12. nb_extended_visualizations                        ← after 7–10

[OR: Single-session alternative]
  nb_full_production_pipeline   (covers all stages above)
```

---

## Output Directory Summary

| Directory | Produced By | Contents |
|---|---|---|
| `runs/<case>/` | Stage 1 notebooks | WarpX diagnostics, `metadata.json`, `particle_number.txt` |
| `plots/` | Stage 2 analysis notebooks | PNG + PDF publication figures |
| `paper/figures/` | `make_paper_figures.py` / pipeline | Vector paper figures (fig01–fig05) |
| `paper/tables/` | `make_paper_tables.py` / pipeline | CSV summary tables |
| `paper/data/` | `freeze_publication_dataset.py` | Frozen canonical dataset + manifest |
| `logs/` | Pipeline script | Verbose execution logs per step |

---

## Case Configuration Files (`cases/`)

| YAML File | Used By | Description |
|---|---|---|
| `vacuum.yaml` | nb_vacuum_reference | Baseline beam transport, no gas |
| `baseline_h2.yaml` | nb_seeded_h2 | 30 keV, 10 mA, H₂ at 1×10⁻⁵ Torr |
| `baseline_kr.yaml` | nb_seeded_kr | 30 keV, 10 mA, Kr at 1×10⁻⁶ Torr |
| `bunched_h2.yaml` | nb_bunched_beam_perveance | RF-bunched H₂ beam |
| `bunched_kr.yaml` | nb_bunched_beam_perveance | RF-bunched Kr beam |
| `method_comparison.yaml` | nb_parameter_scan | Full method matrix (seeded/callback/cxx) |
| `pressure_scan_h2_kr.yaml` | nb_parameter_scan | Pressure sweep H₂ + Kr |
| `method_scan_baseline.yaml` | nb_parameter_scan | Method comparison at baseline pressure |
