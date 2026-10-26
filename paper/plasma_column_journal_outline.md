# Journal Manuscript Structure: Compact Plasma-Assisted Space-Charge Neutralizer for High-Current Cyclotron Axial Injection

**Target Journal**: *Physical Review Accelerators and Beams* (PRAB) / *Nuclear Instruments and Methods in Physics Research A* (NIMA)  
**Author**: Chong Shik Park  
**Affiliation**: Department of Accelerator Science and Center for Accelerator Research, Korea University, Sejong, 30019 Republic of Korea  

---

## Abstract
- High-current compact cyclotron axial injection challenge (space-charge beam blowup).
- Application of a compact beam-ionized $\text{H}_2/\text{Kr}$ plasma neutralizer located upstream of the main solenoid.
- Analytical kinetics and 3D electrostatic PICMI/WarpX simulations of a DC beam in a seeded plasma column (production matrix, 15 cases).
- Local volume-averaged beam-core perveance reduction $K_{\text{eff,local}}/K_0$.
- RF-bunched beam interpretation ($K_{\text{eff,peak}}/K_{0,\text{peak}} \approx 1 - \eta_{\text{avg}}/B_f$).
- Ion expulsion decides the result within 218 ns: H2 core $\eta_{\text{net}} \approx 0.96$, Kr $\approx 0.50$–$0.58$ (Kr$^+$ retained).
- Downstream transport to the spiral inflector and transmission: pending (not yet computed from PIC output).

---

## 1. Introduction
- High-current compact cyclotron injection limit (space-charge bottleneck for 30 keV multi-mA proton beams).
- Axial injection layout:
  $$\text{buncher} \rightarrow \text{plasma neutralizer} \rightarrow \text{solenoid} \rightarrow \text{quadrupole Q1} \rightarrow \text{quadrupole Q2} \rightarrow \text{spiral inflector}$$
- Residual-gas compensation and electron-column background.
- Motivation for a compact neutralizer before the main solenoid.

---

## 2. Plasma Neutralizer Concept
- $\text{H}_2$ baseline neutralizer column.
- $\text{Kr}$ seeding for high cross-section ionization at lower gas pressure.
- Controlled-pressure short gas cell ($L_{\text{cell}} = 20\text{ cm}$).
- Optional local solenoid / electrode confinement.

---

## 3. Analytical Model
- Ionization rate $R_{\text{ion}} = n_{\text{gas}} \sigma_i v_p$.
- Neutralization time constant $\tau_{\text{ion}} = 1 / (n_{\text{gas}} \sigma_i v_p)$.
- Effective perveance $K_{\text{eff}}/K_0 = 1 - \eta_{\text{net}}$.
- Bunched-beam correction ($K_{\text{eff,peak}}/K_{0,\text{peak}} \approx 1 - \eta_{\text{avg}}/B_f$).

---

## 4. Simulation Methods
- Taxonomy of model levels:
  1. `Vacuum reference` (`vacuum_reference`)
  2. `Static seeded PIC` (`seeded_H2_<p>Torr` / `seeded_Kr_<p>Torr`, pressure scan 1e-6 to 3e-4 Torr)
  3. `Python callback dynamic source`: not in production (tau_ion >> run); one run with the rate x1000, labeled rescaled (`callback_H2_accel_x1000_rescaled`)
  4. `Seeded + WarpX electron-impact MCC` (`cxx_mcc_H2_1e-5Torr` / `cxx_mcc_Kr_1e-6Torr`); custom proton-impact MCC pending validation
- Numerics: 64x64x512, electrostatic FFT solver, 0.15 T cell solenoid, dt = 9.48 ps, 23000 steps (218 ns).
- Diagnostics and local compensation metrics ($\eta_{\text{local,net}}$, $K_{\text{eff,local}}/K_0$).

---

## 5. Verification
- Cross-section interpolation (center-of-mass energy conversion).
- Fixed-rate ionization benchmark.
- Time-step convergence ($\Delta t, \Delta t/2, \Delta t/4$).
- Macroparticle-weight consistency ($N_{\text{phys}} = w \cdot N_{\text{macro}}$).
- Status: proton-impact MCC tests pending; ES vs EM solver check done (1% global, ~10% local).

---

## 6. Results
- $\text{H}_2$ vs $\text{Kr}$ neutralization build-up time (analytic) and seeded-plasma PIC response (Table II, Figs. 6–8 of the manuscript).
- Ion retention: H2+ expelled (13% of seed left in core), Kr+ retained (80%).
- Local beam-core effective perveance ratio $K_{\text{eff,local}}/K_0$.
- Beam envelope reduction ($R_x(z), R_y(z)$).
- Bunched-beam peak perveance ($K_{\text{eff,peak}}/K_{0,\text{peak}}$ vs $B_f$).
- Downstream inflector acceptance and transmission efficiency ($T\%$).

---

## 7. Discussion
- Placement before solenoid vs alternative downstream placements.
- Gas pressure and scattering trade-off ($\text{H}_2$ at $10^{-5}\text{ Torr}$ vs $\text{Kr}$ at $10^{-6}\text{ Torr}$).
- Overcompensation risk ($K_{\text{eff,local}}/K_0 < 0$).
- Experimental implementation requirements (differential pumping, gas cell design).

---

## 8. Conclusion
- Summary of compact plasma column neutralizer performance and injection optics enhancement.
