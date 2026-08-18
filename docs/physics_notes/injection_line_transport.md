# Downstream Injection-Line Transport and Optics Model

## 1. Beamline Layout

The compact-cyclotron axial injection line layout is:

$$\text{buncher exit} \rightarrow \text{plasma neutralizer} \rightarrow \text{solenoid} \rightarrow \text{quadrupole Q1} \rightarrow \text{quadrupole Q2} \rightarrow \text{spiral inflector entrance}$$

The baseline neutralizer MUST NOT be placed downstream of the main solenoid.

---

## 2. Space-Charge Envelope Equations & Region-Dependent Perveance $K_{\text{eff}}(z)$

Transverse beam envelope evolution $R_x(z)$ and $R_y(z)$ is calculated using the coupled 2D envelope ODEs:

$$\frac{d^2 R_x}{dz^2} + k_x^2(z) R_x - \frac{2 K_{\text{eff}}(z)}{R_x + R_y} - \frac{\epsilon_{x,n}^2}{\beta^2 \gamma^2 R_x^3} = 0$$

$$\frac{d^2 R_y}{dz^2} + k_y^2(z) R_y - \frac{2 K_{\text{eff}}(z)}{R_x + R_y} - \frac{\epsilon_{y,n}^2}{\beta^2 \gamma^2 R_y^3} = 0$$

where:
- $K_{\text{eff}}(z)$ is the region-dependent space-charge perveance separating the plasma neutralizer cell from downstream high vacuum:
  $$K_{\text{eff}}(z) = \begin{cases} K_0 (1 - \eta_{\text{cell}}), & z \le L_{\text{cell}} \\ K_0 (1 - \eta_{\text{downstream}}), & z > L_{\text{cell}} \end{cases}$$
  In baseline operation, $\eta_{\text{cell}} \approx 0.90$ and $\eta_{\text{downstream}} = 0.0$ (vacuum drift/matching).
- $k_x(z), k_y(z)$ are magnetic focusing strengths from the solenoid ($B_z = 0.15\text{ T}$) and quadrupole doublet Q1 ($G_1 = 5.0\text{ T/m}$) and Q2 ($G_2 = -4.5\text{ T/m}$).
- $\epsilon_{x,n}, \epsilon_{y,n}$ are normalized transverse emittances ($1.0\text{ mm}\cdot\text{mrad}$).

---

## 3. Inflector Acceptance Cut and Transmission Efficiency

The spiral inflector entrance is modeled with an aperture radius $r_{\text{aperture}} = 5.0\text{ mm}$ and angular acceptance $\theta_{\text{ap}} = 25\text{ mrad}$.

Transmission efficiency is evaluated as:

$$T = \min\left(1.0, \frac{r_{\text{aperture}}^2}{0.5(R_x^2 + R_y^2)}\right) \times 100\%$$

### Case Comparison:
1. **Vacuum Reference ($\eta = 0.0$)**: Uncompensated space-charge blowup causes envelope expansion, leading to aperture clipping at the inflector entrance ($T \approx 32\%$).
2. **$\text{H}_2$ Neutralized Cell ($\eta_{\text{cell}} = 0.90$, $\eta_{\text{downstream}} = 0.0$)**: Perveance reduction in the initial $20\text{ cm}$ prevents early beam blowout, enabling the solenoid and quadrupole doublet to focus the beam into the $5\text{ mm}$ inflector entrance aperture with $T > 98\%$.
3. **$\text{Kr}$ Neutralized Cell ($\eta_{\text{cell}} = 0.95$, $\eta_{\text{downstream}} = 0.0$)**: Rapid neutralization buildup ($\tau \sim 0.3\ \mu\text{s}$) provides tight envelope control and low divergence entering matching optics.
