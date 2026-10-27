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

## Feasibility of space-charge compensation

Assessment combining these production results with the analytical estimates of the manuscript
(`paper/manuscript/plasma_column_prab.tex`, task 103). Verdicts: **Feasible**, **Partial**,
**Not feasible**, **Unknown** (not yet simulated or validated).

| Condition | Verdict | Evidence | Caveat |
|-----------|------|-------------|-------------|
| DC beam, H2 >= 1e-5 Torr, 0.15 T cell solenoid | **Feasible** | PIC core eta_net = 0.96, K_eff/K0 = 0.04; flat from 1e-5 to 3e-4 Torr | Seeded plasma; ionization build-up not simulated |
| DC beam, H2 1e-6 to 3e-6 Torr | **Partial** | eta_net = 0.41 (1e-6) and 0.74 (3e-6) | Too little gas for a dense enough plasma |
| DC beam, Kr 1e-6 to 3e-4 Torr | **Partial** | eta_net = 0.50–0.58 at every pressure | Kr+ ions stay in the core (80% after 218 ns); later or gradual build-up not tested |
| Kr instead of H2 for faster build-up | **Not feasible** (no advantage) | Kr 1e-6 Torr builds up slower than H2 1e-5 Torr (145 vs 80 us) | Kr matches H2 only at 1.8e-6 Torr, and its ions leave more slowly |
| Time to establish compensation | **Feasible** for CW, **not** for short pulses | Build-up time 80 us (H2), 145 us (Kr); steady state after a few hundred us | Pulses shorter than about 0.3 ms are not compensated |
| No axial confinement (no solenoid or end electrodes) | **Not feasible** | PIC (task 107): the beam potential well holds electrons for tau_c ~ 0.7 us, so eta_ss ~ 0.01 (free escape alone: ~107 ns) | A cell solenoid and/or electrostatic end plugs are needed |
| Steady-state compensation with a 0.15 T cell solenoid | **Not feasible** with this trap alone | PIC (task 107): tau_c = 2.15 us at best, ~40x short of tau_ion = 80 us, so eta_ss >= 0.026; core eta_net is still 0.90 at 650 ns from the seed | Seeded start; 5 mm analytic plugs shorten tau_c (radial field too strong). Task 109: 300 V plugs >= 10 mm wide raise tau_c to 7–9 us (eta_ss ~0.08), still ~10x short |
| RF-bunched beam, peak bunch inside the cell | **Feasible** (nearly DC there) | Task 105: B_f = 1.0–1.4 in the cell (sine buncher set for the inflector), so K_peak/K0 ~ 0.29 at the cell exit with eta_avg = 0.96 | Ballistic model, no space charge |
| Bunched beam downstream (solenoid → inflector) | **Not feasible** with the cell alone | B_f rises to 5.7 (sine) – 10 (sawtooth) at the inflector; with B_f = 5.7, even eta_avg = 0.96 would give only K_peak/K0 = 0.83, and the cell electrons do not travel with the beam. Matched transport (task 106): T < 0.01 with cell-only or whole-line RF-averaged compensation | Main limit; needs bunching close to the inflector (alternative-placement study) or optics that handle the space charge |
| Holding electrons through the 18 ns bunch gap | **Unknown** (needs B_z >= 53 mT) | Without it, electrons cross the beam in 1.1 ns and are lost each gap | No bunched-beam PIC runs yet |
| Overcompensation (net focusing) | **Feasible** (no problem) | Electrons alone exceed n_b, but net eta <= 1 in every case | — |
| Beam envelope and transmission into the inflector | **Partial** (DC: only with whole-line compensation) | Matched KV envelopes (task 106), 0.25 pi mm mrad: DC T = 0.17 uncompensated, 0.20 cell only, 1.0 whole line; bunched T < 0.01 | Geometric estimate, no particle tracking; 2 mm parallel launch is emittance-limited at 1 pi mm mrad |
| Self-consistent proton-impact ionization | **Unknown** | Custom proton-impact MCC not run or verified | All production results use the seeded model |
| Beam loss from charge exchange and scattering in the gas | **Unknown** | Not assessed | May limit how high the pressure can go |

Summary:

- **Promising:** a compact H2 cell at about 1e-5 Torr inside a solenoid can, in principle,
  cancel almost all of the space charge in the core of a continuous beam. Use H2 rather than Kr.
- **Limited:** in the baseline layout the beam arrives bunched, so even perfect average
  compensation removes only about 1/B_f of the peak-bunch space charge (about 18% at B_f = 5),
  and electrons must be held through each inter-bunch gap.
- **Not yet shown:** that the plasma actually builds up, that it survives the bunch gaps, and
  that the beam gets through the inflector. The matched envelope model (task 106) shows that
  cell-only compensation barely helps transmission; a DC beam needs compensation along the whole
  line, and a bunched beam is not transported in this layout. Next simulations: confinement and
  plug scans, then the best configuration on the production grid
  ([`physics_notes/simulation_strategy_tasks.md`](physics_notes/simulation_strategy_tasks.md)).

Strategies for a more efficient column, and the test plan, are in
[`physics_notes/neutralizer_efficiency_strategy.md`](physics_notes/neutralizer_efficiency_strategy.md).

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
