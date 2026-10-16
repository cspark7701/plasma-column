# Execution Plan Summary: Fix ~1e45 Local Neutralization When the Beam Is Not in the Column

**Task Index**: 92  
**Date**: 2026-10-16  
**Subject**: Every `diagnostics_summary.json` reported `np_core_avg = 0.0`, `eta_net_local ~ 1.4e45–1.7e45`
and `keff_over_k0_local ~ -1.7e45`.

---

## 1. Diagnosis

- The plotfiles hold total `rho` only, so `load_plotfile_densities` bins particles into densities. That path works.
- The plotfile particle headers put every beam proton in the first grid box. Sampling the binary data
  (`diag1010000/beam_protons`) gives the same result for `seeded_H2_1e-5Torr`, `callback_H2_dynamic` and
  `cxx_mcc_H2_baseline`: 20.59 M macroparticles (weight 10.24), `z` from -0.0200 to -0.0119 m, `r_max = 2.5 mm`.
- 30 keV protons: `v = 2.397e6 m/s`. `dt = 3.379e-13 s` (electromagnetic solver, `cfl = 0.5`), so 10 000 steps
  = 3.38 ns, which is **8.1 mm** of travel. The beam front never reaches the column (`z = 0 … 0.20 m`).
- `np_core_avg = 0` was therefore correct. The bug: `safe_eta` returned `ne / (0 + 1e-30)` = 1e45, which was
  reported as overcompensation, and `compute_beam_envelope` was run with eta = 1e45.
- The `.old` plotfile was not the cause (cases without `.old` gave the same values). Separately, `find_plotfiles`
  did rank `diag1010000.old.N` above `diag1010000` and also returned the `diags` folder itself.

## 2. Changes

`src/plasma_column/diagnostics.py`:
1. `compute_local_core_neutralization` averages only core cells inside the column that contain beam
   (`np > 0`). It adds `beam_in_core`, `core_beam_fill_fraction` and `beam_z_max_m`. If no core cell
   contains beam, eta and K_eff/K0 are NaN and `overcompensated` is False.
2. `compute_local_neutralization_vs_z`: z slices without beam give NaN.
3. `postprocess_case_directory`: when local eta is undefined, it stores and prints a warning with the beam
   front position, does not write `beam_envelope.csv` (and removes an old one), and writes NaN as JSON `null`.
   The summary records `local_plotfile`.

`src/plasma_column/warpx_io.py`: `find_plotfiles` keeps only `diag<step>` / `plt<step>` directories, sorted by step.

`tests/test_local_neutralization_masks.py`: 3 new tests (beam upstream of column, partial fill, `.old` plotfiles).

`docs/physics_notes/local_neutralization_diagnostics.md`: beam-occupied core definition, undefined case, beam
transit time; corrected the description of `local_neutralization_vs_t.csv`.

## 3. Verification

- `python -m pytest -q` → 132 passed, 1 skipped.
- `postprocess_case.py` on a scratch copy of `results/method_comparison/seeded_H2_1e-5Torr` (plotfile
  symlinked, results directory untouched) → `beam_in_core: false`, `beam_z_max_m: -0.0124`, eta/K_eff `null`,
  warning stored, no `beam_envelope.csv`.

## 4. Usage

Re-postprocess finished cases (only the diagnostics change; no simulation):

```bash
for c in results/method_scan/*/ results/method_comparison/*/; do
  python3 scripts/postprocess_case.py --case-dir "$c"
done
```

## 5. Limitations and open issues

- **The existing 10 000-step production runs contain no beam–plasma interaction in the column.** Local
  neutralization cannot be obtained from them, and global `N_e/N_p` from them compares a column-length
  pre-loaded plasma with an 8 mm beam segment. Reaching the column end needs about 2.7e5 steps at the present
  `dt`. The matrix comments ("20000 steps = 2.7 beam transits", "120000 steps = 16.2 transits") are wrong
  (20 000 steps = 16 mm, 120 000 steps = 97 mm).
- At the present beam weight (10.24), a beam filling the 0.26 m domain would need about 6.6e8 macroparticles.
  Longer runs need a larger beam macroparticle weight and/or a larger time step (e.g. an electrostatic solver);
  not changed here.
- `local_neutralization_vs_t.csv` still holds global ratios under `*_local` column names.
- `ni_core_avg` is about 1 m^-3 while `ne_core_avg` is about 1.7e15 m^-3 in the seeded cases; the ion seeding was
  not investigated.
- `plots/axial_injection_layout.{pdf,png}` reappeared as modified during this task (source not identified;
  `pytest` alone does not change them) and were restored with `git checkout` as requested in task 91.
