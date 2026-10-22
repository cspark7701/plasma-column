# Production Matrix

Source: [`cases/production.yaml`](../cases/production.yaml) (`matrix_name: production`), repository commit `bc773d0`.
The table lists every case in the matrix once; a case that belongs to several stages is one
physical run, shared by those stages. Fill in **Status** as runs progress
(e.g. `queued`, `running (machine)`, `done`, `failed`, `postprocessed`).

## Cases

| # | Case | Method | Gas | Pressure [Torr] | Stages | Status |
|--|-------------|-------------|---|-----|----|---------|
| 1 | `seeded_H2_1e-5Torr` | Seeded compensation | H2 | 1e-5 | A, B, C | |
| 2 | `seeded_Kr_1e-6Torr` | Seeded compensation | Kr | 1e-6 | A, B, C | |
| 3 | `cxx_mcc_H2_1e-5Torr` | C++ MCC (electron impact on seeded plasma) | H2 | 1e-5 | A, B | |
| 4 | `cxx_mcc_Kr_1e-6Torr` | C++ MCC (electron impact on seeded plasma) | Kr | 1e-6 | A, B | |
| 5 | `vacuum_reference` | Vacuum reference | none | — | B | |
| 6 | `seeded_H2_1e-6Torr` | Seeded compensation | H2 | 1e-6 | B, C | |
| 7 | `seeded_Kr_1e-5Torr` | Seeded compensation | Kr | 1e-5 | B, C | |
| 8 | `seeded_H2_3e-6Torr` | Seeded compensation | H2 | 3e-6 | C | |
| 9 | `seeded_H2_3e-5Torr` | Seeded compensation | H2 | 3e-5 | C | |
| 10 | `seeded_H2_1e-4Torr` | Seeded compensation | H2 | 1e-4 | C | |
| 11 | `seeded_H2_3e-4Torr` | Seeded compensation | H2 | 3e-4 | C | |
| 12 | `seeded_Kr_3e-6Torr` | Seeded compensation | Kr | 3e-6 | C | |
| 13 | `seeded_Kr_3e-5Torr` | Seeded compensation | Kr | 3e-5 | C | |
| 14 | `seeded_Kr_1e-4Torr` | Seeded compensation | Kr | 1e-4 | C | |
| 15 | `seeded_Kr_3e-4Torr` | Seeded compensation | Kr | 3e-4 | C | |

Totals: 15 cases — 12 seeded, 2 C++ MCC, 1 vacuum.

## Stages

| Stage | Name | Cases | Members |
|---|-----------|---|-------------------|
| A | `A_method_scan` | 4 | `seeded_H2_1e-5Torr`, `seeded_Kr_1e-6Torr`, `cxx_mcc_H2_1e-5Torr`, `cxx_mcc_Kr_1e-6Torr` |
| B | `B_method_comparison` | 7 | `vacuum_reference`, `seeded_H2_1e-6Torr`, `seeded_H2_1e-5Torr`, `seeded_Kr_1e-6Torr`, `seeded_Kr_1e-5Torr`, `cxx_mcc_H2_1e-5Torr`, `cxx_mcc_Kr_1e-6Torr` |
| C | `C_pressure_scan` | 12 | `seeded_H2_1e-6Torr`, `seeded_H2_3e-6Torr`, `seeded_H2_1e-5Torr`, `seeded_H2_3e-5Torr`, `seeded_H2_1e-4Torr`, `seeded_H2_3e-4Torr`, `seeded_Kr_1e-6Torr`, `seeded_Kr_3e-6Torr`, `seeded_Kr_1e-5Torr`, `seeded_Kr_3e-5Torr`, `seeded_Kr_1e-4Torr`, `seeded_Kr_3e-4Torr` |

## Common settings (`defaults` in the matrix file)

| Setting | Value |
|------|-------------|
| Beam | 30 keV, 10 mA, radius 2 mm (DC) |
| Solenoid B_z | 0.15 T |
| Grid | 64×64×512, x,y ∈ ±10 mm, z ∈ [-2, 24] cm |
| Solver | es (electrostatic FFT, open boundaries) |
| Steps | 23000 (checkpoint every 11500) |
| Macroparticles per cell | beam 4, plasma 16 (vacuum: 0) |
| Diagnostics | full every 2300 steps, reduced every 50 steps |

## Notes on interpreting the methods

- **Seeded compensation** initializes the compensating electrons/ions from the analytic build-up
  law with a prescribed steady-state fraction (`--neutralization -1`). Its η is an input, so these
  runs show the beam response to a given compensation, not the compensation the gas achieves.
- **C++ MCC** cases (`method_category: full_self_consistent_cxx_mcc` in the YAML) run WarpX
  built-in *electron-impact* MCC on top of the same seeded plasma (`--mcc electron_impact`). They
  do not use the custom proton-impact ionization extension, so they are not a self-consistent
  proton-impact model. H2 uses the atomic-H table (task 95).
- Python-callback cases are not in this matrix (task 96); see `cases/callback_h2_accelerated.yaml`.
- The matrix includes no bunched-beam runs (`cases/bunched_*.yaml`) or MCC verification runs
  (`cases/verification/`).

## Commands

See [`full_production_pipeline.md`](full_production_pipeline.md) § "Production matrix (task 97)".

```bash
# Validate (writes nothing into finished case directories)
bash scripts/run_full_production.sh dry-run production --skip_step 5,5b,6,6b,7,7b,8
# Run everything; --resume (default) skips finished cases, restarts unfinished ones from checkpoints
bash scripts/run_full_production.sh medium production --snapshots 10
# Stage summaries at any time
python3 scripts/postprocess_stages.py --matrix cases/production.yaml --results_dir results/production
```

Outputs: `results/production/<case_name>/` per case and `results/production/stage_<stage>/` per stage.
