# Journal Manuscript Structure: Compact Plasma-Assisted Space-Charge Neutralizer for High-Current Cyclotron Axial Injection

**Target Journal**: *Physical Review Accelerators and Beams* (PRAB) / *Nuclear Instruments and Methods in Physics Research A* (NIMA)  
**Author**: Chong Shik Park  
**Affiliation**: Department of Accelerator Science and Center for Accelerator Research, Korea University, Sejong, 30019 Republic of Korea  

---

## Abstract
- High-current compact cyclotron axial injection challenge (space-charge beam blowup).
- Application of a compact beam-ionized $\text{H}_2/\text{Kr}$ plasma neutralizer located upstream of the main solenoid.
- Analytical kinetics, PICMI/WarpX PIC simulations, and custom MCC ion-impact analytical benchmarks.
- Local volume-averaged beam-core perveance reduction $K_{\text{eff,local}}/K_0$.
- RF-bunched beam interpretation ($K_{\text{eff,peak}}/K_{0,\text{peak}} \approx 1 - \eta_{\text{avg}}/B_f$).
- Downstream envelope transport from buncher through solenoid and quadrupole doublet to spiral inflector, demonstrating $\sim 100\%$ transmission efficiency.

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
  2. `Static seeded PIC` (`seeded_H2` / `seeded_Kr`)
  3. `Python callback dynamic source` (`callback_H2` / `callback_Kr`)
  4. `Custom ion-impact MCC` (`cxx_H2_mcc_or_custom` / `cxx_Kr_mcc_or_custom`)
- Diagnostics and local compensation metrics ($\eta_{\text{local,net}}$, $K_{\text{eff,local}}/K_0$).

---

## 5. Verification
- Cross-section interpolation (center-of-mass energy conversion).
- Fixed-rate ionization benchmark.
- Time-step convergence ($\Delta t, \Delta t/2, \Delta t/4$).
- Macroparticle-weight consistency ($N_{\text{phys}} = w \cdot N_{\text{macro}}$).

---

## 6. Results
- $\text{H}_2$ vs $\text{Kr}$ neutralization build-up time and steady-state density.
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
