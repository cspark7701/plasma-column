# $\text{H}_2$ and $\text{Kr}$ Cross-Section Database and Validation

## 1. Physical Context

Proton-impact ionization is the dominant electron generation mechanism in space-charge neutralization cells for $30\text{ keV}$ proton beams:

$$p^+ + \text{Gas} \rightarrow p^+ + \text{Gas}^+ + e^-$$

Because target neutral masses differ ($\text{H}_2 \approx 2\text{ amu}$ vs $\text{Kr} \approx 83.8\text{ amu}$), collision kinematics and cross-section magnitudes differ significantly between $\text{H}_2$ and $\text{Kr}$.

---

## 2. Energy Frames: Laboratory vs Center-of-Mass

Cross-section datasets are evaluated as functions of center-of-mass energy $E_{\text{cm}}$:

$$E_{\text{cm}} = E_{\text{lab}} \cdot \left(\frac{m_{\text{target}}}{m_{\text{projectile}} + m_{\text{target}}}\right)$$

For a $30\text{ keV}$ ($E_{\text{lab}} = 30,000\text{ eV}$) proton beam:
- **$\text{H}_2$ Target** ($m_{\text{target}} \approx 2 m_p$):
  $$E_{\text{cm}} = 30,000 \cdot \frac{2}{1+2} = 20,000\text{ eV} = 20.00\text{ keV}$$
- **$\text{Kr}$ Target** ($m_{\text{target}} \approx 83.8 m_p$):
  $$E_{\text{cm}} = 30,000 \cdot \frac{83.8}{1+83.8} \approx 29,644\text{ eV} = 29.64\text{ keV}$$

---

## 3. Tabular Data and Operating Points

Cross-section data files are stored in `warpx_proton_impact_cross_sections_linear/MCC_cross_sections/`:
- `H2/proton_impact_ionization.dat`
- `Kr/proton_impact_ionization.dat`

### Interpolated $30\text{ keV}$ Proton Operating Values
| Target Gas | $E_{\text{lab}}$ [keV] | $E_{\text{cm}}$ [keV] | $\sigma_{\text{ion}}$ [$\text{m}^2$] | $\sigma_{\text{ion}}$ [$\text{Å}^2$] | Relative Ratio ($\sigma_{\text{Kr}} / \sigma_{\text{H2}}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **$\text{H}_2$** | $30.0$ | $20.00$ | $1.6135 \times 10^{-20}$ | $1.61$ | $1.00\times$ |
| **$\text{Kr}$** | $30.0$ | $29.64$ | $8.9648 \times 10^{-20}$ | $8.96$ | **$5.56\times$** |

---

## 4. Key Physics Insights

1. **Higher Cross Section for Krypton**: Krypton's proton-impact ionization cross section at $30\text{ keV}$ is **$5.56\times$ larger** than that of $\text{H}_2$.
2. **Pressure Reduction Capability**: Because $\sigma_{\text{Kr}} \approx 5.56 \sigma_{\text{H2}}$, a Krypton gas cell achieves equivalent ionization buildup at a lower neutral pressure ($10^{-6}\text{ Torr}$ $\text{Kr}$ vs $10^{-5}\text{ Torr}$ $\text{H}_2$).
3. **Collision Mean Free Path & Transmission Loss**:
   $$\lambda_{\text{mfp}} = \frac{1}{n_{\text{gas}} \sigma_{\text{ion}}}$$
   $$T = \exp(-n_{\text{gas}} \sigma_{\text{loss}} L)$$
   For $10^{-5}\text{ Torr } \text{H}_2$ over $L = 0.20\text{ m}$, $\lambda_{\text{mfp}} \approx 194\text{ m}$ and $T > 99.8\%$, showing negligible transmission loss.
4. **Multiple Coulomb Scattering (MCS)**:
   Calculated using the Highland / Lynch–Dahl formulation with radiation lengths $X_{0,\text{H2}} = 63.05\text{ g/cm}^2$ and $X_{0,\text{Kr}} = 35.34\text{ g/cm}^2$:
   $$\theta_0 \approx \frac{13.6\text{ MeV}}{\beta p c} z_p \sqrt{\frac{x}{X_0}} \left[1 + 0.038 \ln\left(\frac{x}{X_0}\right)\right]$$
   For $30\text{ keV}$ protons in $10^{-5}\text{ Torr } \text{H}_2$, $\theta_0 \approx 0.13\text{ mrad} \ll 1\text{ mrad}$, confirming that gas scattering does not degrade beam emittance.

---

## 5. Verification Commands

To plot the cross-section curves and verify operating points:
```bash
python scripts/make_plots.py --cross-sections
```
Outputs:
- `plots/cross_section_comparison.png`
- `plots/cross_section_comparison.pdf`
