# 20-Minute Presentation Slide Outline

**Title**: Plasma-Assisted Neutralization for High-Current Cyclotron Axial Injection  
**Speaker**: Chong Shik Park
**Duration**: 20 Minutes (15 min presentation + 5 min Q&A)  

---

## Slide Breakdown and Figure List

### Slide 1: Title & Overview (1 min)
- Title, author affiliations, project context.
- High-current 30 keV proton beam injection into compact cyclotrons.

### Slide 2: Physics Motivation & Axial Injection Baseline (2 min)
- Space-charge blowup in LEBT lines.
- **Baseline Beamline Diagram**:
  `buncher -> plasma neutralizer -> solenoid -> Q1 -> Q2 -> inflector`
- *Figure Reference*: [`plots/axial_injection_layout.png`](file:///home/cspark/Work/projects/plasma-column/plots/axial_injection_layout.png)

### Slide 3: Neutralization Physics & Ionization Kinetics (2 min)
- Proton-impact ionization: $p^+ + \text{Gas} \rightarrow p^+ + \text{Gas}^+ + e^-$.
- Build-up time constant $\tau = 1 / (n_{\text{gas}} \sigma v_{\text{beam}})$.
- Definition of metrics: $\eta_{\text{electron\_only}}$, $\eta_{\text{net}}$, $K_{\text{eff}}/K_0 = 1 - \eta_{\text{net}}$.

### Slide 4: Gas Selection: $\text{H}_2$ vs $\text{Kr}$ Cross-Section Database (3 min)
- Comparison of collision energy in CM frame ($E_{\text{cm}} = 20.0\text{ keV}$ for $\text{H}_2$, $29.6\text{ keV}$ for $\text{Kr}$).
- Cross-section comparison: $\sigma_{\text{Kr}} = 8.96\text{ Å}^2$ vs $\sigma_{\text{H2}} = 1.61\text{ Å}^2$ ($5.56\times$ advantage for Kr).
- Pressure benefit: $10^{-6}\text{ Torr } \text{Kr}$ achieves neutralization equivalent to $10^{-5}\text{ Torr } \text{H}_2$.
- *Figure Reference*: [`plots/h2_kr_cross_sections.png`](file:///home/cspark/Work/projects/plasma-column/plots/h2_kr_cross_sections.png)

### Slide 5: RF-Bunched Beam Space-Charge Dilution (3 min)
- Upstream buncher effect: $I_{\text{peak}} = B_f I_{\text{avg}}$ ($B_f = 5$).
- Derivation: $K_{\text{eff,peak}}/K_{0,\text{peak}} \approx 1 - \eta_{\text{avg}}/B_f$.
- Key insight: Even at $90\%$ average plasma neutralization, $82\%$ of peak space charge remains active.
- *Figure Reference*: [`plots/bunched_beam_perveance.png`](file:///home/cspark/Work/projects/plasma-column/plots/bunched_beam_perveance.png)

### Slide 6: WarpX Particle-in-Cell Simulation Methods (3 min)
- Comparison of simulation models: Seeded compensation, dynamic Python callbacks, and full C++ MCC tracking.
- Diagnostic distinction: Global particle counts vs local core charge density.

### Slide 7: Summary & Conclusions (2 min)
- Neutralizer placement before main solenoid effectively controls envelope expansion.
- Kr provides strong ionization rate advantages at lower gas pressures.
- RF bunching space-charge dilution must be included in inflector matching optics design.
