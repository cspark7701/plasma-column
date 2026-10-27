# Strategy for a More Efficient Plasma Neutralizer

Status: 2026-10-26. Based on the production PIC matrix (`docs/production_matrix.md`, task 102),
the manuscript estimates (`paper/manuscript/plasma_column_prab.tex`, task 103) and the
feasibility table in `docs/production_matrix.md`. Numbers are for the design point: 30 keV,
10 mA, a = 2 mm, 20 cm cell, 50 MHz RF.

## 1. What beam reaches the column

- The ion source delivers a DC beam. The cyclotron accepts only particles near the right RF
  phase (a window of a few tens of degrees out of 360°).
- Without a buncher, the DC beam goes straight into the inflector and most of it is lost.
- With a buncher, the gap imposes a velocity modulation. Density bunches form during the
  downstream drift and are focused onto the inflector and first accelerating gap.
- So in the baseline layout (buncher → neutralizer → solenoid → Q1 → Q2 → inflector), the beam in
  the neutralizer is velocity-modulated but only partly density-bunched. The effective bunching
  factor in the column can be well below the B_f = 5 used as the reference value. That value
  applies near the bunch focus, downstream of the column.
- "CW" describes the macro time structure: the cyclotron runs a continuous train of RF bunches.
  It is not the opposite of "bunched".

### Local bunching factor along the line (task 105)

`python scripts/analyze_bunching_along_line.py` (module `plasma_column.bunching`). Model: ballistic
drift from a thin buncher gap at the buncher exit (z = 0) to the inflector entrance
(z = 1.12 m, `InjectionLine`), with no space charge and a 5 eV rms source energy spread.
B_f(z) is the beam fraction inside the best 36° acceptance window divided by 36/360, so DC = 1.
The buncher voltage is set to maximize B_f at the inflector entrance.

| Buncher | Voltage | B_f at cell entrance | B_f at cell exit (z = 0.20 m) | Cell mean | B_f at inflector |
|------|-----|-----|-----|-----|-----|
| Sine (single harmonic) | 620 V | 1.02 | 1.36 | 1.16 | 5.70 |
| Ideal sawtooth (upper bound) | 1178 V | 1.02 | 1.22 | 1.11 | 10.0 (all in window) |

- Inside the plasma cell the beam is nearly DC (B_f = 1.0–1.4). The bunch forms in the
  solenoid–Q1–Q2 section and peaks at the inflector.
- With the PIC core eta_avg = 0.96 (seeded H2, 1e-5 Torr), the static-background estimate at the
  cell exit is K_eff,peak/K0,peak ~ 1 - 0.96/1.36 = 0.29. Using B_f = 5.7 (inflector) gives
  0.83. So the peak-bunch penalty is small inside the cell.
- The real limit moves downstream: from the solenoid to the inflector, B_f rises to 5.7–10, but
  the compensating electrons stay in the cell (they are confined by the cell solenoid and do
  not travel with the beam). The beam must be compensated there by other means (a longer or
  second compensated section, residual-gas compensation in the line), or that space charge must
  be handled by the optics.
- Space charge opposes longitudinal bunching at multi-mA, so the real B_f values are lower than
  these ballistic ones. Compensating the beam upstream may help the buncher reach its design
  bunching.
- Figure and data: `results/bunching_along_line/` (git-ignored; regenerate with the command
  above).

## 2. What limits the neutralization

Particle balance in the cell (manuscript Eq. 6):

```text
eta_ss ~ min(1, tau_c / tau_ion)
```

- tau_ion = 80 us (H2, 1e-5 Torr) and 145 us (Kr, 1e-6 Torr): set by the ionization rate.
- tau_c: electron confinement time in the beam core. Free axial escape of a 10 eV electron
  from the 20 cm cell takes about 107 ns, so eta is about 1e-3 without confinement. (The PIC
  confinement scan shows that the beam potential well alone holds electrons for ~0.7 us; see below.)
- The net value also needs the ions to leave. In the PIC runs, 13% of the seeded H2+ density is
  left in the core after 218 ns (eta_net = 0.96), but 80% of the Kr+ density (eta_net = 0.50–0.58).

Confinement and ion removal matter more than the ionization rate.

## 3. Strategies, in order of impact

| # | Strategy | Why it helps | Expected effect | Cost / risk |
|---|-----------|-------------|-------------|-------------|
| 1 | Electron trap: cell solenoid plus negatively biased end electrodes (Penning/Gabor-lens-like column) | Raises tau_c from ~100 ns toward tau_ion, the condition for eta → 1 | From eta ~1e-3 (free escape) to the 0.9+ reached in PIC when electrons are held | End-electrode fields act on the beam; bias below the ~158 V beam potential well |
| 2 | Active filling (electron gun, hot filament or small plasma source) instead of beam ionization | Removes the 80–145 us build-up and the pressure dependence. The seeded PIC runs model this starting state. | Compensation within ~100 ns, at lower gas load | Density control needed to avoid overcompensation |
| 3 | Light gas (H2), so ions leave the core | Ions set the net value: H2+ leaves in ~44 ns, Kr+ stays (expulsion ~283 ns) | Kr → H2 raises eta_net from ~0.55 to ~0.96 (PIC) | None; Kr gives no build-up advantage at the quoted pressures |
| 4 | Pressure at the plateau, about 1e-5 Torr H2 | PIC eta_net is flat from 1e-5 to 3e-4 Torr; more gas only adds loss and gas load | Same eta, less charge exchange and scattering | Short, differentially pumped gas cell |
| 5 | Column where the beam is least density-bunched, with enough length | Compensation works best on a nearly DC density; the peak-bunch limit is about 1 - eta_avg/B_f | Avoids most of the peak-bunch penalty | Placement before the buncher is an alternative-placement study, labeled as such |
| 6 | Transverse field >= ~53 mT through the 18 ns bunch gap | Without it, electrons cross the beam in 1.1 ns and are lost every gap | Keeps the electron column between bunches | The 0.15 T in the PIC runs meets this; check with bunched-beam PIC |
| 7 | Overcompensation control | Electrons alone reach 1.1–2.4 n_b; net eta stays <= 1 only while ions are removed | Avoids a net focusing error | Matters most with active filling (#2) |

Recommended configuration: an H2 cell at about 1e-5 Torr inside the 0.15 T solenoid, with
negatively biased end electrodes and an optional small electron or plasma source for a fast
start. It sits close to the buncher, where the beam is still nearly DC.

For a CW beam the cell trap is the main lever. For an RF-bunched beam the peak space charge builds
up downstream (B_f 1.3 in the cell, 5.7 at the inflector), and electrons compensate only the
RF-averaged charge, so compensation must extend along the line and bunching should happen late.
Configurations for both beams and the simulation task list:
[simulation_strategy_tasks.md](simulation_strategy_tasks.md)
(figure `figures/recommended_configurations.png`).

## 4. Test plan in this repository

| Step | Task | Purpose | Cost |
|---|-----------|-------------|---------|
| 1 | Bunching factor along buncher → column → inflector (analytic, ballistic drift) | Real B_f in the column (strategy 5) | Minutes |
| 2 | Confinement scan with the seeded driver: end-electrode bias, B_z = 0, 0.05, 0.15 T, runs longer than 218 ns | Measure tau_c directly (strategies 1, 6) | Driver change, a few ~9 h runs |
| 3 | Bunched-beam PIC with the best configuration from step 2 | RF-averaged and peak-bunch eta (strategies 5, 6) | New beam injection, several runs |
| 4 | Fix the envelope transport model (`compute_beam_envelope`, task 103 open item), then transmission into the inflector | The result that decides the design | Model work |

### Step 2 result: confinement scan (task 107)

Seeded H2 at 1e-5 Torr, DC 10 mA beam, 650 ns, 32x32x256 grid (`scripts/run_confinement_scan.py`,
`scripts/analyze_confinement_scan.py`). tau_c is the exponential fit of the electrons in the cell
over 325–650 ns; eta_ss uses its 2-sigma lower bound and tau_ion = 80 us.

| Cell B_z | Seed T_e | tau_c, no plugs | tau_c, 300 V plugs (w 5 mm) | core eta_net at 650 ns, no plugs / plugs |
|---|---|---|---|---|
| 0 | 1 eV | 0.70 us | 0.32 us | 0.79 / 0.67 |
| 0 | 10 eV | 0.97 us | 0.40 us | 0.71 / 0.57 |
| 0.05 T | 1 eV | 1.55 us | 0.35 us | 0.84 / 0.64 |
| 0.05 T | 10 eV | 1.23 us | 0.44 us | 0.76 / 0.56 |
| 0.15 T | 1 eV | **2.15 us** | 0.47 us | **0.90** / 0.67 |
| 0.15 T | 10 eV | 1.88 us | 0.43 us | 0.82 / 0.51 |

- The beam's own potential well already holds electrons for ~0.7 us with no field, far longer than
  the 107 ns free-escape estimate of section 2. The cell solenoid triples this to 2.15 us at
  0.15 T. Best case: 0.15 T, 1 eV seed, no plugs (69% of the electrons left after 650 ns).
- Even 2.15 us is ~40x short of tau_ion = 80 us, so eta_ss >= 0.026 is all this trap guarantees
  in steady state. Reaching eta -> 1 needs tau_c ~ 100 us: strategies #1 (much better trap) or #2
  (active filling) remain necessary.
- The 300 V, 5 mm analytic plugs shorten tau_c about 4x. They hold the electrons better during the
  first ~200 ns, but then pull the ions out (negative potential) and the electron loss accelerates
  (late-quarter tau_c 0.3–0.6 us). Their paraxial radial field, ~V r / (2 w^2) (6 MV/m at r = 1 mm),
  is far stronger than a real electrode with a ~10 mm aperture would give, and the upstream plug
  sat 5 mm from the injection plane. Wider plugs in a longer domain are tested in task C4.

### Step 4 result: transport to the inflector (task 106)

Matched KV envelope transport ([injection_line_transport.md](injection_line_transport.md)),
eta_cell = 0.958, transmission estimate T at 0.25 / 0.5 / 1.0 pi mm mrad:

| Scenario | T |
|---|---|
| DC, no compensation | 0.17 / 0.13 / 0.08 |
| DC, cell only | 0.20 / 0.16 / 0.10 |
| DC, whole line | 1.00 / 0.62 / 0.17 |
| Bunched, whole line, RF-averaged compensation | 0.001 / 0.003 / 0.007 |
| Bunched, whole line, per-slice (upper bound) | 0.99 / 0.58 / 0.17 |

The cell alone does little for transmission: the beam blows up again in the uncompensated drift
and solenoid. For a DC beam the compensation must extend along the line. For a bunched beam the
electrons compensate only the RF-averaged charge, so the peak slice is not transported in this
layout with any compensation; bunching must happen close to the inflector.

## 5. Limitations

- Strategy effects other than #3 and #4 are analytic estimates, not simulated yet.
- All PIC results start from a seeded plasma (analytic source estimate), not self-consistent
  proton-impact ionization, and cover a DC beam for 218 ns.
