# Execution Plan Summary: Late-Bunching Layout (Alternative-Placement Study)

**Task Index**: 113  
**Date**: 2026-11-15  
**Subject**: Task B3 of `docs/physics_notes/simulation_strategy_tasks.md`. Buncher voltage and
position versus the bunched-beam current accepted by the inflector. Any buncher position other
than upstream of the neutralizer is an ALTERNATIVE-PLACEMENT STUDY (baseline: buncher ->
neutralizer -> solenoid -> Q1 -> Q2 -> inflector).

Repository state at start: `main` at `f369572`; uncommitted B2/C2/CW3 work in the tree.

---

## 1. Changes

- `src/plasma_column/bunching.py`: `bunching_with_buncher_at` (B_f = 1 upstream of the buncher,
  ballistic bunching downstream).
- `tests/test_bunching.py`: profile shift test.
- `scripts/late_bunching_layout.py` (new, `--dry_run`): 5 buncher positions (baseline at the cell
  entrance, middle of drift1–drift4), sine voltage from `optimal_voltage_V` for the inflector,
  peak-slice envelope with K = K0 (B_f - eta), eta_cell 0.91, eta_down 0 / 0.5 / 0.9, 0.25 and
  0.5 pi mm mrad; gain B_f T_peak / T_DC with T_DC from CW2 (task 112). Outputs in
  `results/late_bunching_layout/` (git-ignored), labeled as an alternative-placement study.
- Docs: "Task B3 result" in `neutralizer_efficiency_strategy.md`; B3 done in
  `simulation_strategy_tasks.md`.

## 2. Results (0.25 pi mm mrad; G = B_f T_peak / T_DC at eta_down 0 / 0.5 / 0.9)

| Position | Drift to inflector | Voltage | G |
|---|---|---|---|
| baseline (cell entrance) | 1.12 m | 0.62 kV | 0.025 / 0.014 / 0.009 |
| drift1 | 0.87 m | 0.80 kV | 0.029 / 0.016 / 0.010 |
| drift2 (solenoid–Q1) | 0.52 m | 1.34 kV | 1.03 / 0.54 / 0.33 |
| drift3 (Q1–Q2) | 0.31 m | 2.25 kV | 1.77 / 0.97 / 0.63 |
| drift4 (Q2–inflector) | 0.075 m | 8.74 kV | 5.1 / 4.3 / 5.3 |

- The baseline buncher loses the peak bunch (G ~ 0.01–0.06 at both emittances).
- Bunching pays only over the last ~0.3 m; the 8.7 kV case (+-29% energy modulation) is outside
  the ballistic model and the inflector energy acceptance, so it is a limit, not a design.
- Run: 30 matches, 2 processes on CPUs 10 and 22, about 50 min.

## 3. Verification

- `pytest -q tests/test_bunching.py`; dry run and full run; the baseline voltage (618 V) and
  B_f (5.7) reproduce task 105.

## 4. Limitations

- Ballistic bunching without longitudinal space charge (which opposes bunching at 10 mA) and
  without energy-spread effects in the solenoid/quadrupoles or the inflector acceptance.
- Peak-slice KV envelope: T_peak is a lower bound for the window current (task B5 resolves
  slices); geometric transmission estimate.
- The buncher must physically fit in each drift; gap length and transit-time factor not modeled.
