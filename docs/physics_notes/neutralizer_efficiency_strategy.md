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

The local bunching factor along the line is computed in task 105
(`scripts/analyze_bunching_along_line.py`).

## 2. What limits the neutralization

Particle balance in the cell (manuscript Eq. 6):

```text
eta_ss ~ min(1, tau_c / tau_ion)
```

- tau_ion = 80 us (H2, 1e-5 Torr) and 145 us (Kr, 1e-6 Torr): set by the ionization rate.
- tau_c: electron confinement time in the beam core. Free axial escape of a 10 eV electron
  from the 20 cm cell takes about 107 ns, so eta is about 1e-3 without confinement.
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

## 4. Test plan in this repository

| Step | Task | Purpose | Cost |
|---|-----------|-------------|---------|
| 1 | Bunching factor along buncher → column → inflector (analytic, ballistic drift) | Real B_f in the column (strategy 5) | Minutes |
| 2 | Confinement scan with the seeded driver: end-electrode bias, B_z = 0, 0.05, 0.15 T, runs longer than 218 ns | Measure tau_c directly (strategies 1, 6) | Driver change, a few ~9 h runs |
| 3 | Bunched-beam PIC with the best configuration from step 2 | RF-averaged and peak-bunch eta (strategies 5, 6) | New beam injection, several runs |
| 4 | Fix the envelope transport model (`compute_beam_envelope`, task 103 open item), then transmission into the inflector | The result that decides the design | Model work |

## 5. Limitations

- Strategy effects other than #3 and #4 are analytic estimates, not simulated yet.
- All PIC results start from a seeded plasma (analytic source estimate), not self-consistent
  proton-impact ionization, and cover a DC beam for 218 ns.
