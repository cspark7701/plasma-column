# Local Neutralization Diagnostics and Beam-Core Metrics

## 1. Physics Motivation

In space-charge neutralization of intense ion beams using plasma columns, global particle-number ratios such as

$$\eta_{\text{global,electron}} = \frac{N_e}{N_p}, \quad \eta_{\text{global,net}} = \frac{N_e - N_i}{N_p}$$

are necessary sanity checks, but **insufficient** to claim space-charge reduction inside the beam.

If plasma electrons accumulate outside the beam envelope or are displaced transversely due to stray magnetic fields or asymmetric potential walls, global particle counts may suggest near-full neutralization ($\eta_{\text{global}} \approx 1$), while the beam core experiences zero effective field reduction. Therefore, journal-quality analysis must evaluate **local volume-averaged charge compensation within the beam core inside the plasma cell**.

---

## 2. Mathematical Definitions

### 2.1 Beam-Core Spatial Mask

The local beam core is defined by a cylindrical spatial mask:

$$\text{Mask}_{\text{core}}(x,y,z) = \left\{ \sqrt{x^2 + y^2} \le r_{\text{core}} \quad \text{and} \quad z_{\text{min,cell}} \le z \le z_{\text{max,cell}} \right\}$$

where $r_{\text{core}} \approx 2\sigma_r$ (typically $2\text{ mm}$) and $z \in [0.0\text{ m}, 0.20\text{ m}]$.

### 2.2 Local Neutralization Fractions

Within the mask, local volume-averaged number densities for protons ($\langle n_p \rangle$), electrons ($\langle n_e \rangle$), and ions ($\langle n_i \rangle$) are computed. The local neutralization fractions are:

- **Electron-Only Neutralization**:
  $$\eta_{\text{local,electron\_only}}(z,t) = \frac{\langle n_e \rangle_{\text{core}}(z,t)}{\langle n_p \rangle_{\text{core}}(z,t)}$$

- **Net Charge Neutralization**:
  $$\eta_{\text{local,net}}(z,t) = \frac{\langle n_e \rangle_{\text{core}}(z,t) - \langle n_i \rangle_{\text{core}}(z,t)}{\langle n_p \rangle_{\text{core}}(z,t)}$$

### 2.3 Effective Perveance Ratio

The local space-charge reduction ratio is defined as:

$$\frac{K_{\text{eff,local}}}{K_0} = 1 - \eta_{\text{local,net}}$$

If $\eta_{\text{local,net}} > 1$, $K_{\text{eff,local}}/K_0 < 0$, indicating **overcompensation** (focusing field from excess electron charge). Overcompensated regimes are flagged explicitly in machine-readable metadata.

---

## 3. Displaced Cloud Effect

A key diagnostic requirement in `plasma_column` is testing against displaced electron clouds. If the electron distribution is shifted transversely by $\Delta x$:

$$n_e(x,y,z) = n_{e,0} \exp\left(-\frac{(x - \Delta x)^2 + y^2}{2\sigma_r^2}\right)$$

the overlap integral with the beam core ($r \le r_{\text{core}}$) drops exponentially with $\Delta x/\sigma_r$. Although global particle count $N_e$ remains unchanged, $\eta_{\text{local,net}} \to 0$ and $K_{\text{eff,local}}/K_0 \to 1$.

---

## 4. Diagnostics Output Pipeline

When `scripts/postprocess_case.py` processes a simulation case directory (`runs/<case_name>/`), it outputs:

1. **`global_particle_number.csv`**: Time series of total particle counts $N_p, N_e, N_i$ and global ratios.
2. **`local_neutralization_vs_t.csv`**: Beam-core time series with one row per plotfile (step, time, `beam_in_core`, `core_beam_fill_fraction`, core-averaged $n_p, n_e, n_i$, local $\eta$ and $K_{\text{eff,local}}/K_0$), using the same core definition as `diagnostics_summary.json`. Snapshots before the beam reaches the core have NaN $\eta$. Empty (header only) when the case has no plotfiles. Before task 99 this file held the global `ParticleNumber` ratios under `*_local` names.
3. **`local_neutralization_vs_z.csv`**: Slice-by-slice $z$-profile of beam-core neutralization fractions along the beam axis.
4. **`radial_density_profiles.csv`**: Radially-binned species densities $n_p(r), n_e(r), n_i(r)$ and net charge density $\rho_{\text{net}}(r)$.
5. **`beam_core_charge_density.csv`**: Beam-core charge densities ($\text{C/m}^3$) for protons, electrons, ions, and net charge.
6. **`diagnostics_summary.json`**: Machine-readable JSON recording diagnostic availability, core averages, and explicit warning flags if local fields are missing.

### Beam-occupied core and undefined neutralization

The core average uses only cells inside $r \le r_{\text{core}}$, $z_{\text{min}} \le z \le z_{\text{max}}$ that contain beam
protons ($n_p > 0$). Cells the beam front has not reached would otherwise dilute $n_p$ while keeping the pre-loaded
plasma, which inflates $\eta$. `diagnostics_summary.json` records `beam_in_core`, `core_beam_fill_fraction`
(beam-occupied share of the core volume) and `beam_z_max_m` (beam front position).

If no core cell contains beam, $\eta_{\text{local}}$ and $K_{\text{eff,local}}/K_0$ are undefined: they are written as
`null` (JSON) / `NaN` (CSV), a warning is stored, and `beam_envelope.csv` is not written. In
`local_neutralization_vs_z.csv`, slices without beam are `NaN`. Before this check, $\eta = n_e/(0 + 10^{-30})$ was
reported as $\sim 10^{45}$.

A 30 keV proton moves at $v = 2.40\times10^{6}$ m/s. With the production time step $\Delta t = 3.38\times10^{-13}$ s,
10 000 steps (3.38 ns) move the beam front only 8.1 mm from the injection plane at $z = -0.02$ m, so it does not
reach the column at $z = 0$. Reaching the column end ($z = 0.20$ m) takes $\approx 9.2\times10^{-8}$ s
($\approx 2.7\times10^{5}$ steps).

---

## 5. Standard Diagnostic Figures

The visualization script `scripts/make_local_neutralization_plots.py` generates 5 standard figure pairs (`.png` and `.pdf`):

- `plots/local_Keff_over_K0_vs_time.png` / `.pdf`: Beam-core effective perveance ratio evolution.
- `plots/local_eta_vs_time.png` / `.pdf`: Electron-only vs net local neutralization comparison.
- `plots/radial_density_profiles.png` / `.pdf`: Radial species density profiles $n(r)$.
- `plots/z_resolved_neutralization.png` / `.pdf`: Longitudinal neutralization profile $\eta_{\text{local}}(z)$.
- `plots/global_particle_number_sanity_check.png` / `.pdf`: Sanity check plot comparing global particle counts over time.
