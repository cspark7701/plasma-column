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

### Task C3 result: beam quality at the cell exit (task 108)

Beam rms size, divergence and normalized rms emittance from the particle data of the confinement
scan, averaged over the second half of each run (`scripts/analyze_beam_quality.py`). Injected beam:
r_rms = 1.45 mm, r'_rms = 0.17 mrad.

| Case | r_rms at exit | r'_rms at exit | eps_n,rms at exit | Energy in the cell |
|---|---|---|---|---|
| 0 T, 1 eV, no plugs | 3.4 mm | 13.2 mrad | 0.014 pi mm mrad | 29.99 keV |
| 0 T, 1 eV, 300 V plugs | 5.0 mm | 24.0 mrad | 0.021 pi mm mrad | 29.81 keV |
| 0.15 T, 1 eV, no plugs | 2.5 mm | 7.6 mrad | 0.041 pi mm mrad | 29.99 keV |
| 0.15 T, 1 eV, 300 V plugs | 4.6 mm | 23.9 mrad | 0.16 pi mm mrad | 29.81 keV |

- Without plugs the beam leaves the 0.15 T cell smallest (2.5 mm, 7.6 mrad); the residual space
  charge, not the plasma, sets the growth from the injected 1.45 mm.
- The 5 mm, 300 V plugs triple the exit divergence and quadruple the emittance at 0.15 T. Most of
  the growth appears already at mid-cell, after the upstream plug, consistent with its strong
  paraxial radial field and with injection inside that plug (the beam starts 0.18 keV low).
- The projected x-x' emittance in the solenoid includes x-y coupling from the beam rotation, so it
  overstates the intrinsic growth at 0.15 T.

### Task C4 result: end-plug voltage and width scan (task 109)

0.15 T, 1 eV seed, 650 ns, small grid, z domain [-0.12, 0.32] m so the beam is injected 3 widths
outside the upstream plug for every width (`scripts/run_plug_scan.py`). Plug centres 3 widths
outside the cell ends. Beam moments in the last slab inside the cell (z = 0.18–0.20 m), where
all cases use the same slab:

| Case | tau_c (second half / last quarter) | eta_ss lower bound | r_rms | r'_rms | eps_n,rms |
|---|---|---|---|---|---|
| no plugs | 3.4 / 3.2 us | 0.040 | 6.8 mm | 29 mrad | 0.48 pi mm mrad |
| 300 V, 5 mm | 1.1 / 1.0 us | 0.013 | 8.3 mm | 35 mrad | 0.71 |
| 100 V, 10 mm | 4.8 / 4.7 us | 0.057 | 8.0 mm | 33 mrad | 0.66 |
| 300 V, 10 mm | 7.2 / 6.4 us | 0.077 | 8.2 mm | 33 mrad | 0.69 |
| 100 V, 20 mm | 4.7 / 5.5 us | 0.048 | 7.8 mm | 32 mrad | 0.61 |
| 300 V, 20 mm | 9.3 / 16.6 us | 0.085 | 8.0 mm | 32 mrad | 0.66 |

- Plugs at least 10 mm wide do confine: 300 V plugs keep 89–90% of the cell electrons at 650 ns
  against 69% without plugs, and double to triple tau_c. The 5 mm plugs still shorten tau_c
  without the injection artifact, so their failure in task 107 was the radial field of the narrow
  analytic potential.
- 300 V at 10 mm and at 20 mm give the same electron curve; the tau_c difference is within the
  fit noise over 650 ns. **Selected for CW1: 300 V, 10 mm** (fits a shorter domain with less
  uncompensated drift before the cell; a 10 mm wide potential matches a ~10 mm electrode aperture).
- The plugs cost beam quality: +10–15% divergence and +30–40% emittance at the cell end relative to
  no plugs, much less than the 3–4x of the 5 mm plugs in task C3.
- Even 16 us is ~5x short of tau_ion = 80 us: the trap alone gives eta_ss of order 0.1, not
  steady-state compensation. Task C2 (orbit tracking to 100 us) decides whether tau_c keeps rising.
- Caveat: with injection 0.12 m before the cell the uncompensated 10 mA beam blows up to
  r_rms ~5–7 mm in the cell and fills much of the +-10 mm box (part of it is lost transversely), so
  the absolute beam numbers and tau_c (3.4 us without plugs here vs 2.15 us in task 107) are not
  comparable with tasks 107/108; only the comparison between C4 cases is. The local core eta at
  650 ns is not meaningful for the same reason. The exit slab (behind the downstream plug) is only
  4 mm long for the 20 mm plugs and is not used.

### Task CW1 result: best configuration at production resolution (task 111)

0.15 T, 1 eV seed, -300 V / 10 mm end plugs (task 109), seeded H2 1e-5 Torr (analytic source
estimate), DC 10 mA, 64x64x672 (production dx, dz), z in [-0.07, 0.27] m, electron-impact MCC,
975 ns (the restart ran past the planned 650 ns, see task 111).

| Quantity | 227 ns | 650 ns | 975 ns |
|---|---|---|---|
| N_e in the cell / N_e(0) | 0.97 | 0.87 | 0.81 |
| N_i in the cell / N_i(0) | 0.98 | 0.65 | 0.52 |
| Beam-core eta_net | 0.27 (transient) | 0.81 | 0.93 |

- Beam-core eta_net rings for ~400 ns after the beam arrives (0.27–1.7), then stays at
  0.91 on average (0.81–1.00) from 490 to 975 ns. The trap keeps the core compensated for ~1 us
  from the seed, at the level of the 218 ns production matrix (0.96).
- tau_c = 4.2 us (2-sigma lower bound 4.1 us; last quarter 3.9 us), so eta_ss >= 0.05 against
  tau_ion = 80 us. Ions leave twice as fast as electrons; the cell turns net negative
  ((N_e - N_i)/N_p = 0.5 over the cell at 975 ns), and the seed still decays.
- Beam: injected at x_rms 1.0 mm; 1.7 mm and 15 mrad at the cell entrance, 4.7 mm and 21 mrad at
  the cell end, cell-end slab r_rms 6.9 mm, eps_n,rms 0.51 pi mm mrad. Most of the divergence is
  made before the cell: in the uncompensated 7 cm drift and the upstream plug. Without that drift
  (task 107 domain, injection 2 cm before the cell, no plugs) the beam stays at x_rms 1.0–1.7 mm,
  <= 5 mrad through the cell. In the plug scan the upstream 300 V / 10 mm plug added about
  10 mrad at the cell entrance (22 vs 12 mrad).
- Conclusion for the CW track: the cell holds eta ~0.9 in the core, but the beam must arrive
  compensated. An uncompensated drift of a few cm before the cell (and the plug lens) already
  costs more beam quality than the cell recovers, consistent with the transport result (task
  106): compensation along the whole line, including the buncher-to-cell drift.

### Task CW2 result: transmission vs downstream compensation (task 112)

Matched KV envelope (task 106 model), DC beam, eta_cell = 0.91 from CW1, compensation eta_down
after the cell (drift, main solenoid, Q1, Q2), optics rematched at each point
(`scripts/transmission_vs_downstream.py`). Transmission estimate T:

| eta_down | 0 | 0.3 | 0.5 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|---|
| 0.25 pi mm mrad | 0.22 | 0.33 | 0.51 | 0.93 | 1.00 | 1.00 |
| 0.5 pi mm mrad | 0.16 | 0.27 | 0.39 | 0.48 | 0.54 | 0.56 |
| 1.0 pi mm mrad | 0.10 | 0.12 | 0.14 | 0.16 | 0.16 | 0.16 |

- At 0.25 pi mm mrad: T >= 0.5 needs eta_down >= 0.49, T >= 0.9 needs eta_down >= 0.69.
- At 0.5 pi mm mrad T saturates at ~0.56 above eta_down ~ 0.8 (emittance and the 5 mm / 50 mrad
  inflector acceptance limit it); at 1.0 pi mm mrad the beam is emittance-dominated (T <= 0.16)
  and compensation hardly matters.
- Target for the CW line: eta_down of about 0.7 along the solenoid and quadrupoles, and a source
  emittance near 0.25 pi mm mrad. Task CW3 tests whether residual-gas electrons can stay there.

### Task B3 result: late-bunching layout (task 113, ALTERNATIVE-PLACEMENT STUDY)

Sine buncher moved from its baseline position (upstream of the neutralizer) to the middle of each
downstream drift, voltage set for the best 36 deg window B_f at the inflector (ballistic), peak
slice matched with RF-averaged compensation K = K0 (B_f - eta), eta_cell = 0.91
(`scripts/late_bunching_layout.py`). Accepted-current gain over an unbunched beam with the same
compensation, G = B_f T_peak / T_DC (T_DC from CW2):

| Buncher position (drift to inflector) | Voltage | B_f | G, eta_down 0 / 0.5 / 0.9 (0.25 pi mm mrad) |
|---|---|---|---|
| baseline, before the cell (1.12 m) | 0.62 kV | 5.7 | 0.025 / 0.014 / 0.009 |
| after the cell (0.87 m) | 0.80 kV | 5.7 | 0.029 / 0.016 / 0.010 |
| between solenoid and Q1 (0.52 m) | 1.34 kV | 5.7 | 1.03 / 0.54 / 0.33 |
| between Q1 and Q2 (0.31 m) | 2.25 kV | 5.7 | 1.77 / 0.97 / 0.63 |
| between Q2 and inflector (0.075 m) | 8.74 kV | 5.6 | 5.1 / 4.3 / 5.3 |

- With the baseline buncher the peak bunch is lost (G ~ 0.01–0.06): bunching through the cell and
  solenoid costs far more than the factor 5.7 it gains.
- Bunching pays only over the last ~0.3 m. Over 0.075 m the full B_f gain survives, but the gap
  voltage (8.7 kV, a +-29% energy modulation of the 30 keV beam) is far outside the ballistic model
  and the inflector's energy acceptance; it marks a limit, not a design. Between Q1 and Q2
  (2.25 kV, +-7.5%) the gain is 1.8 without downstream compensation and falls below 1 with it,
  because compensation helps the DC reference more than the RF-averaged-compensated peak slice.
- Conclusion: in this layout the buncher position, not the plasma, decides the bunched-beam
  current. A buncher close to the inflector (alternative placement) with modest voltage, or a
  shorter buncher-to-inflector line, is required; tasks B5/B6 refine this with slices and a
  sawtooth.

### Task C2 result: test electrons in the static trap to 100 us (task 114)

Guiding-centre test electrons (`plasma_column.electron_trap`, `scripts/trap_orbit_tracking.py`):
analytic plugs (w = 10 mm, as CW1), uniform cell solenoid, static net beam well (1 - eta) phi_b,
elastic e-H2 collisions at 1e-5 Torr (approximate cross section), Coulomb heating by the 10 mA
beam (0.04 eV/us); 2000 electrons per case, 100 us.

| Plugs | B_z | Surviving at 100 us | tau_c | Mean energy at 100 us (born at 1 / 10 eV) |
|---|---|---|---|---|
| none | 0.05, 0.15 T | 0 (all axial) | 1.5–2.7 us | – |
| 100 V | 0.05, 0.15 T | 0.999–1.000 | >> 100 us | 5.0–5.3 / 16–18 eV |
| 300 V | 0.05, 0.15 T | 1.000 | >> 100 us | 4.9–5.4 / 16–18 eV |

Same for eta = 0.5 and 0.9; no radial loss in any case; a dt / 2.5 check agrees.

- A static, quiescent trap with >= 100 V plugs holds electrons far longer than tau_ion = 80 us:
  classical collisions (one per ~30 us, guiding-centre steps of ~10 um) and beam heating
  (~4 eV in 100 us) do not reach the plug barrier or the wall. The classical bound on eta_ss is 1.
- Without plugs the electrons stream out in ~2 us, in line with the no-plug PIC values
  (0.7–2.2 us, task 107).
- The PIC tau_c of 4–9 us with plugs (tasks 109, 111) is therefore not a single-particle loss:
  it comes from self-consistent effects absent here (ions leaving so the cell turns net negative,
  the electron cloud's own space charge, fluctuations) or from numerical heating at the low
  particle counts of those runs. Two consequences: (1) a PIC convergence check of tau_c
  (nppc, grid) is needed before trusting the PIC numbers; (2) with ions leaving and electrons
  held, the trap fills until the electron space charge reaches the plug barrier, so the steady
  state may overcompensate (eta > 1) rather than undercompensate. Both are open.

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
