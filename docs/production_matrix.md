# Production Matrix

Source: [`cases/production.yaml`](../cases/production.yaml) (`matrix_name: production`), repository commit `bc773d0`.
The table lists every case in the matrix once; a case that belongs to several stages is one
physical run, shared by those stages. Status as of 2026-10-26 13:22 KST: all 15 cases completed
23000 steps and were postprocessed. The pipeline (`run_full_production.sh medium production
--snapshots 10 --resume`, launched 2026-10-21 09:47 KST) finished all steps 1–8.

## Cases

| # | Case | Method | Gas | Pressure [Torr] | Stages | Status |
|--|-------------|-------------|---|-----|----|---------|
| 1 | `seeded_H2_1e-5Torr` | Seeded compensation | H2 | 1e-5 | A, B, C | done |
| 2 | `seeded_Kr_1e-6Torr` | Seeded compensation | Kr | 1e-6 | A, B, C | done |
| 3 | `cxx_mcc_H2_1e-5Torr` | C++ MCC (electron impact on seeded plasma) | H2 | 1e-5 | A, B | done |
| 4 | `cxx_mcc_Kr_1e-6Torr` | C++ MCC (electron impact on seeded plasma) | Kr | 1e-6 | A, B | done |
| 5 | `vacuum_reference` | Vacuum reference | none | — | B | done |
| 6 | `seeded_H2_1e-6Torr` | Seeded compensation | H2 | 1e-6 | B, C | done |
| 7 | `seeded_Kr_1e-5Torr` | Seeded compensation | Kr | 1e-5 | B, C | done |
| 8 | `seeded_H2_3e-6Torr` | Seeded compensation | H2 | 3e-6 | C | done |
| 9 | `seeded_H2_3e-5Torr` | Seeded compensation | H2 | 3e-5 | C | done |
| 10 | `seeded_H2_1e-4Torr` | Seeded compensation | H2 | 1e-4 | C | done |
| 11 | `seeded_H2_3e-4Torr` | Seeded compensation | H2 | 3e-4 | C | done |
| 12 | `seeded_Kr_3e-6Torr` | Seeded compensation | Kr | 3e-6 | C | done |
| 13 | `seeded_Kr_3e-5Torr` | Seeded compensation | Kr | 3e-5 | C | done |
| 14 | `seeded_Kr_1e-4Torr` | Seeded compensation | Kr | 1e-4 | C | done |
| 15 | `seeded_Kr_3e-4Torr` | Seeded compensation | Kr | 3e-4 | C | done |

Totals: 15 cases — 12 seeded, 2 C++ MCC, 1 vacuum.

## Results

Run windows are KST in 2026 (start of the case to its last reduced-diagnostic write; 8 cores, about
8.3–9.4 h per case). Local values are beam-core averages (r <= 2 mm, 0 <= z <= 0.20 m, beam-filled
cells) at the last snapshot, t = 218 ns, from `results/production/stage_*/stage_summary.csv`. The
global column is the domain-wide ParticleNumber ratio (Ne − Ni)/Np, a sanity check only. No case is
overcompensated (local eta_net <= 1).

| # | Case | Run window [MM-DD hh:mm] | η_e local | η_net local | K_eff/K0 local | η_net global |
|--|-------------|----------------|---|---|---|---|
| 1 | `seeded_H2_1e-5Torr` | 10-16 14:07 – 10-16 22:55 (task 94, reused) | 1.132 | 0.958 | 0.042 | 0.172 |
| 2 | `seeded_Kr_1e-6Torr` | 10-21 09:47 – 10-21 18:41 | 2.003 | 0.497 | 0.503 | -0.026 |
| 3 | `cxx_mcc_H2_1e-5Torr` | 10-21 18:42 – 10-22 03:38 | 1.127 | 0.946 | 0.054 | 0.170 |
| 4 | `cxx_mcc_Kr_1e-6Torr` | 10-22 03:39 – 10-22 13:04 | 1.994 | 0.501 | 0.499 | -0.028 |
| 5 | `vacuum_reference` | 10-22 13:05 – 10-22 21:20 | 0.000 | 0.000 | 1.000 | 0.000 |
| 6 | `seeded_H2_1e-6Torr` | 10-22 21:20 – 10-23 06:22 | 0.582 | 0.406 | 0.594 | 0.111 |
| 7 | `seeded_Kr_1e-5Torr` | 10-23 06:22 – 10-23 15:09 | 2.337 | 0.569 | 0.431 | -0.037 |
| 8 | `seeded_H2_3e-6Torr` | 10-23 15:09 – 10-23 23:54 | 0.849 | 0.736 | 0.264 | 0.171 |
| 9 | `seeded_H2_3e-5Torr` | 10-23 23:55 – 10-24 08:39 | 1.184 | 0.956 | 0.044 | 0.176 |
| 10 | `seeded_H2_1e-4Torr` | 10-24 08:39 – 10-24 17:21 | 1.197 | 0.964 | 0.036 | 0.175 |
| 11 | `seeded_H2_3e-4Torr` | 10-24 17:21 – 10-25 02:04 | 1.196 | 0.957 | 0.043 | 0.172 |
| 12 | `seeded_Kr_3e-6Torr` | 10-25 02:04 – 10-25 10:48 | 2.318 | 0.575 | 0.425 | -0.037 |
| 13 | `seeded_Kr_3e-5Torr` | 10-25 10:48 – 10-25 19:32 | 2.360 | 0.583 | 0.417 | -0.036 |
| 14 | `seeded_Kr_1e-4Torr` | 10-25 19:33 – 10-26 04:17 | 2.330 | 0.574 | 0.426 | -0.036 |
| 15 | `seeded_Kr_3e-4Torr` | 10-26 04:18 – 10-26 13:03 | 2.295 | 0.574 | 0.426 | -0.036 |

- Seeded and C++ MCC agree at the baseline pressures (H2 1e-5 Torr: 0.958 vs 0.946; Kr 1e-6 Torr:
  0.497 vs 0.501), as the small-grid check predicted (task 97 §3): electron-impact MCC adds no
  measurable ionization in 218 ns.
- H2: local η_net rises from 0.41 (1e-6 Torr) to 0.74 (3e-6 Torr) and stays at 0.96 from 1e-5 to
  3e-4 Torr. The seeded plasma density is itself set from the pressure (Notes below), so this trend
  reflects the prescribed compensation plus the beam/plasma response to it.
- Kr: local η_net stays at 0.50–0.58 from 1e-6 to 3e-4 Torr. The core holds about twice the beam
  density in electrons (η_e = 2.0–2.4) together with a large ion density, and the global η_net is
  slightly negative (ions outnumber electrons in the domain). Why Kr does not follow the H2 trend is
  not yet analyzed.
- These are seeded-source results: the compensating plasma is prescribed from the analytic build-up
  law, not produced by self-consistent proton-impact ionization. The beam is DC; peak-bunch values
  for an RF-bunched beam are lower (K_eff,peak/K0,peak ≈ 1 − η_avg/B_f).

Stage figures: `results/production/stage_<stage>/local_eta_by_case.{png,pdf}` and, for stages B and C,
`eta_vs_pressure.{png,pdf}`.

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
