# Downstream Injection-Line Transport and Optics Model

## 1. Beamline Layout

The compact-cyclotron axial injection line layout is:

$$\text{buncher exit} \rightarrow \text{plasma neutralizer} \rightarrow \text{solenoid} \rightarrow \text{quadrupole Q1} \rightarrow \text{quadrupole Q2} \rightarrow \text{spiral inflector entrance}$$

The baseline neutralizer MUST NOT be placed downstream of the main solenoid.

---

## 2. Envelope Model (task 106, `plasma_column.transport`)

KV (uniform-density) edge envelopes, integrated with fixed-step RK4 on a 1 mm grid:

```text
R_x'' = -k_x(z) R_x + 2 K(z) / (R_x + R_y) + eps^2 / R_x^3      (same for y)
solenoid   : k_x = k_y = (B / 2 B rho)^2
quadrupole : k_x = -k_y = G / B rho,   B rho = 0.02503 T m (30 keV protons)
```

Perveance along the line, eta = eta_cell for z <= L_cell and eta_downstream after it:

```text
DC beam                              K = K0 (1 - eta)
bunched peak slice, "average"        K = K0 (B_f(z) - eta)          (physical)
bunched peak slice, "per_slice"      K = K0 B_f(z) (1 - eta)         (upper bound only)
```

The electrons are created in tau_ion ~ 80 us, far longer than T_RF = 20 ns, and the electron
plasma frequency (~28 MHz) is below f_RF = 50 MHz. They therefore cancel only the RF-averaged
charge, and the peak slice keeps K_peak/K0,peak = 1 - eta_avg/B_f (AGENTS.md). B_f(z) comes from
the ballistic sine buncher set for the inflector (620 V, task 105): 1.02–1.36 in the cell and 5.7
at the inflector.

Beam at the buncher exit: 30 keV, 10 mA, a = 2 mm, parallel (as in the PIC runs); normalized edge
emittance 0.25, 0.5 and 1.0 pi mm mrad.

For each scenario the solenoid field (0–0.6 T) and both quadrupole gradients (+-1.5 T/m) are
matched by differential evolution to maximize the transmission estimate:

```text
T = T_pipe x T_aperture x T_divergence
T_pipe       : smallest fraction of the beam ellipse inside the 10 mm pipe along the line
T_aperture   : fraction inside the 5 mm inflector aperture
T_divergence : min(1, 50 mrad / theta) per plane at the inflector entrance
```

This is a geometric estimate for a uniform beam; halo, nonlinear fields and particle loss
upstream of the clipping point are not modeled.

`InjectionLine` defaults are now the matched optics of the uncompensated DC beam at
1 pi mm mrad: solenoid 0.23 T, Q1 -0.28 T/m, Q2 0.85 T/m. The earlier defaults (0.15 T,
5 and -4.5 T/m; k L ~ 1.7 per quadrupole) overfocused and gave envelope radii of ~0.8 m.

---

## 3. Results (matched optics, transmission estimate T)

eta_cell = 0.958 (PIC beam-core eta_net, seeded H2 1e-5 Torr, DC beam).

| Scenario | eps_n 0.25 | eps_n 0.5 | eps_n 1.0 |
|---|---|---|---|
| DC, no compensation | 0.17 | 0.13 | 0.08 |
| DC, cell only | 0.20 | 0.16 | 0.10 |
| DC, whole line (eta = 0.958) | 1.00 | 0.62 | 0.17 |
| Bunched, no compensation | 0.004 | 0.004 | 0.004 |
| Bunched, cell only (average) | 0.001 | 0.001 | 0.004 |
| Bunched, cell + 0.5 downstream (average) | 0.001 | 0.002 | 0.005 |
| Bunched, whole line (average) | 0.001 | 0.003 | 0.007 |
| Bunched, whole line (per-slice upper bound) | 0.99 | 0.58 | 0.17 |

- **DC beam.** A 10 mA, 30 keV beam is space-charge dominated: without compensation it grows to
  24–36 mm before the solenoid and only 8–17% reaches the inflector. Compensating the 20 cm cell
  alone adds only 2–3 points, because the beam blows up again in the uncompensated drift and
  solenoid. Compensation along the whole line (residual gas) gives T = 1.0 at 0.25 pi mm mrad.
- **Emittance.** At 1 pi mm mrad, a 2 mm parallel beam is emittance-dominated (about 19 mm after
  the 0.3 m to the solenoid even without space charge), so compensation cannot help; the beam
  must be launched with a larger, converging envelope. Initial conditions are an open design
  parameter.
- **Bunched beam.** With the physical (RF-averaged) compensation, the peak slice keeps
  K ~ 4.7 K0 at the inflector and T < 0.01 in every case. The cell does not change this. The
  per-slice values show what would be needed: every slice compensated by the same fraction along
  the whole line, which the electrons cannot do at 50 MHz.
- Differences below about 0.005 are within the optimizer's noise (for example bunched cell-only
  below uncompensated at 0.25 pi mm mrad).

Run: `python scripts/transport_to_inflector.py` (outputs in `results/transport_to_inflector/`,
git-ignored: `transport_summary.csv/.json`, `envelopes.csv`, `envelopes_matched.png/.pdf`).

The transmission claims of the earlier version of this note (T > 98% with cell-only
compensation) came from the unphysical quadrupole settings and are withdrawn.
