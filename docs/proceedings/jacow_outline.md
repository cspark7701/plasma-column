# JACOW Conference Proceeding Outline

**Title**: Numerical and Analytical Modeling of a Compact Plasma Neutralizer for Cyclotron Axial Injection  
**Authors**: Chong Shik Park et al.  

---

## Section Outline

### I. INTRODUCTION
- Motivation: High-current proton beam space-charge divergence in compact cyclotron axial injection.
- Baseline layout: $\text{buncher} \rightarrow \text{plasma neutralizer} \rightarrow \text{solenoid} \rightarrow \text{quadrupoles} \rightarrow \text{inflector}$.
- Role of the neutralizer: Reduce effective perveance $K_{\text{eff}}$ prior to solenoid matching.

### II. PHYSICS MODEL AND SPECIES CROSS SECTIONS
- Ionization kinetics: $p^+ + \text{Gas} \rightarrow p^+ + \text{Gas}^+ + e^-$.
- Comparison of $\text{H}_2$ ($\sigma_{\text{ion}} = 1.61\text{ Å}^2$) and $\text{Kr}$ ($\sigma_{\text{ion}} = 8.96\text{ Å}^2$) at $30\text{ keV}$.
- Gas pressure and differential pumping constraints: Kr reaches the build-up rate of $10^{-5}\text{ Torr } \text{H}_2$ at $1.8\times10^{-6}$ Torr, not at $10^{-6}$ Torr ($\sigma$ ratio 5.56 < pressure ratio 10).

### III. RF-BUNCHED BEAM SPACE-CHARGE DILUTION
- Impact of upstream RF bunching ($f_{\text{RF}} = 50\text{ MHz}, B_f = 5$).
- Derivation of peak-bunch perveance reduction: $K_{\text{eff,peak}}/K_{0,\text{peak}} \approx 1 - \eta_{\text{avg}}/B_f$.
- Interpretation of space-charge dilution during micro-bunch passage.
- PIC check: electrons do not follow strong bunches; the peak-bunch compensation equals $\eta_{\text{avg}}/B_f$ (line section, $B_f$ = 3 and 5.7); $B_f$ = 5 empties the cell trap in 0.12 $\mu$s.

### IV. WARPX PIC SIMULATION COMPARISON
- Methodologies: static seeded plasma (analytic source estimate), Python-callback source (one run rescaled x1000), WarpX electron-impact MCC on the seeded plasma. The custom proton-impact MCC is not validated and is not used.
- Global species population tracking vs local beam-core charge density ratios.
- Seeded results: H$_2$ core $\eta_{\text{net}}$ = 0.96 (ions expelled), Kr 0.50–0.58 (ions retained).
- Electron confinement: cell solenoid and $\geq$ 10 mm end plugs give $\tau_c$ = 4.2 $\mu$s, $\eta_{\text{net}}$ = 0.91; 5 mm plugs shorten $\tau_c$ and triple the divergence.
- Transport to the inflector: $T \geq 0.9$ needs downstream compensation 0.69–0.9; residual gas at $10^{-5}$ Torr gives $\leq$ 0.04 in the solenoid and quadrupoles.

### V. CONCLUSION AND OUTLOOK
- H$_2$ outperforms Kr in seeded PIC because its ions leave the beam; Kr has no pressure advantage at equal build-up rate.
- Electron confinement, in the cell and downstream, sets the achievable compensation; the steady state at the design pressure is bracketed, not simulated (self-consistent build-up needs a validated proton-impact source).
- Implications for compact cyclotron injection optics design: compensation must continue along the solenoid and quadrupoles; a bunched beam gains over DC only with late or sawtooth bunching (alternative-placement study).
