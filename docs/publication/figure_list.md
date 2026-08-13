# Publication Figure List

All figures are generated in both `.png` (300 DPI) and `.pdf` formats under `paper/figures/` with accompanying machine-readable `.json` metadata files:

1. **`fig01_axial_injection_concept`**: Baseline compact-cyclotron axial injection beamline layout (`buncher -> neutralizer -> solenoid -> Q1 -> Q2 -> inflector`).
2. **`fig02_plasma_neutralizer_module`**: Schematic of gas cell, H2/Kr inlet, electron/ion production, solenoid, and beam path.
3. **`fig03_analytical_neutralization_time`**: Analytical neutralization build-up time $\tau$ vs gas pressure ($10^{-6} - 10^{-4}\text{ Torr}$) for $\text{H}_2$ and $\text{Kr}$.
4. **`fig04_local_plasma_density_profiles`**: Local beam-core radial density profiles $n_p(r), n_e(r), n_i(r)$.
5. **`fig05_local_Keff_over_K0_vs_time`**: Time evolution of electron-only vs net-charge local effective perveance ratio $K_{\text{eff,local}}/K_0$.
6. **`fig06_bunched_beam_interpretation`**: Peak-bunch perveance reduction ratio $K_{\text{eff,peak}}/K_{0,\text{peak}}$ as a function of bunching factor $B_f$.
7. **`fig07_beam_envelope_to_inflector`**: Beam envelope trajectories $R_x(z), R_y(z)$ comparing vacuum, $\text{H}_2$, and $\text{Kr}$ cases from buncher exit to inflector entrance.
8. **`fig08_inflector_acceptance_transmission`**: Transverse phase space $(x, x')$ at inflector entrance and transmission efficiency comparison.
9. **`fig09_parameter_scan_summary`**: Summary bar chart of parameter scan across method matrix and pressure settings.
10. **`fig10_numerical_validation`**: Verification comparison of custom ion-impact MCC ionization rate against analytical $dN_e/dt$.

## Extended Analysis Figures (notebooks/analysis/nb_extended_visualizations.ipynb)
- `keff_vs_eta_parametric.{png,pdf}`: K_eff,peak/K₀,peak vs average neutralization η for bunching factors B_f = 1–10.
- `K0_vs_current_energy_family.{png,pdf}`: Generalized perveance K₀ vs beam current (1–50 mA) for beam energies 15, 20, 30, 50 keV.
- `rf_bunch_sensitivity.{png,pdf}`: Two-panel RF bunch sensitivity — bunch length vs RF frequency and required η_avg vs bunching factor.
- `tau_vs_pressure.{png,pdf}`: Ionization time constant τ vs gas pressure for H₂ and Kr (log-log).
- `eta_buildup_h2_pressures.{png,pdf}`: Neutralization build-up η(t) for H₂ at five pressures with colormap.
- `neutralization_2d_pressure_length.{png,pdf}`: 2-D heatmap of η vs gas pressure × plasma column length.
- `transverse_density_slice.{png,pdf}`: Transverse (x–y) density slices of n_e, n_p, and local η at beam midplane.
- `eta_z_h2_kr_comparison.{png,pdf}`: Axial neutralization profile η(z) along column for H₂ vs Kr.
- `phase_space_before_after.{png,pdf}`: Transverse phase-space portrait before (η=0) and after (η=0.7) space-charge compensation.
