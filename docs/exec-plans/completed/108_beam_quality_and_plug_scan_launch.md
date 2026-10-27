# Execution Plan Summary: Beam Quality in the Cell and Plug-Scan Launch

**Task Index**: 108  
**Date**: 2026-10-27  
**Subject**: Tasks C3 and C4 of `docs/physics_notes/simulation_strategy_tasks.md`. Measure how
the cell settings (solenoid field, end plugs, seed temperature) change the beam at the cell exit
(C3), and launch the end-plug voltage/width scan (C4) with the best confinement setting of task 107.

Repository state at start: `main` at `86e5bea`, with the uncommitted C3/C4/CW1 scripts.

---

## 1. Changes

- `src/plasma_column/beam_quality.py` (new): reads beam_protons from a plotfile (yt; empty arrays
  before injection) and gives weighted rms size, divergence (p_u/p_z), normalized rms emittance
  and mean kinetic energy in a z-slab.
- `scripts/analyze_beam_quality.py` (new, `--dry_run`, `--scan_dir`): per case, averages the slab
  moments over the snapshots with t >= half the run; slabs at injection, mid-cell, cell end and
  exit (3 plug widths past the downstream plug). Outputs `beam_quality.csv/.json` and
  `beam_quality_exit.{png,pdf}` in `<scan_dir>/analysis/` (git-ignored).
- `scripts/run_plug_scan.py` (new, `--dry_run`): C4, at 0.15 T and 1 eV seed (best of task 107):
  no plugs, 300 V / 5 mm, 100 and 300 V at 10 and 20 mm widths; plug centres 3 widths outside the
  cell ends; z domain [-0.12, 0.32] m (nz = 432, dz 1.02 mm) so the beam is injected outside every
  plug; 650 ns; 6 cases at once on 4 threads each, disjoint cores. Reuses
  `run_confinement_scan.command/run_case/core_slots`.
- `tests/test_beam_quality.py` (2 tests): Gaussian beam size, divergence and emittance; correlated
  beam; slab selection; empty slab.
- Docs: C3 results in `neutralizer_efficiency_strategy.md`; C3 done and C4 running in
  `simulation_strategy_tasks.md`.

## 2. Results (C3)

| Case | r_rms exit | r'_rms exit | eps_n,rms exit | Energy in the cell |
|---|---|---|---|---|
| 0 T, 1 eV, no plugs | 3.4 mm | 13.2 mrad | 0.014 pi mm mrad | 29.99 keV |
| 0 T, 1 eV, 300 V plugs | 5.0 mm | 24.0 mrad | 0.021 pi mm mrad | 29.81 keV |
| 0.15 T, 1 eV, no plugs | 2.5 mm | 7.6 mrad | 0.041 pi mm mrad | 29.99 keV |
| 0.15 T, 1 eV, 300 V plugs | 4.6 mm | 23.9 mrad | 0.16 pi mm mrad | 29.81 keV |

- The 5 mm, 300 V plugs roughly triple the exit divergence in every case; the growth starts after
  the upstream plug. With the confinement loss of task 107, these plugs are harmful as modeled.
- The 0.18 keV energy deficit comes from injecting the beam inside the upstream plug potential
  (domain starts 5 mm before the plug centre): an artifact that C4 removes.
- The C4 launch: 2026-10-27 11:06 KST, 6 cases, ~0.27 s/step at start (expected 6–8 h).
  Output `results/plug_scan/` (git-ignored); analysis with
  `analyze_confinement_scan.py --scan_dir results/plug_scan` and
  `analyze_beam_quality.py --scan_dir results/plug_scan`.

## 3. Verification

- `pytest -q`: 179 passed, 1 skipped. Dry runs of `analyze_beam_quality.py` and
  `run_plug_scan.py`; driver dry run with the long domain and 10 mm plugs.
- All 6 C4 cases started and stepping.

## 4. Limitations

- Projected x-x' emittance; in the solenoid it includes x-y coupling from the beam rotation.
- Slab moments average over the beam in a 1–2 cm slab and over 10 snapshots; no halo analysis.
- Seeded plasma (analytic source estimate); analytic plugs valid only for r << w.
