# Limitations and Assumptions of the Study

To maintain strict scientific integrity, the following limitations must be stated explicitly in journal publications:

1. **Global vs Local Neutralization**:
   Global particle-number ratios ($N_e/N_p, (N_e-N_i)/N_p$) reflect total domain counts and do not guarantee local space-charge compensation. All primary publication claims in this paper are based on volume-averaged local beam-core metrics ($\eta_{\text{local,net}}$) inside $r \le 2\text{ mm}$ within the plasma cell.

2. **RF-Bunched Beam Peak Compensation**:
   The plasma neutralizer is modeled as providing steady-state average background compensation over many RF periods. For a bunched beam with $B_f = 5$, peak-bunch perveance reduction is $K_{\text{eff,peak}}/K_{0,\text{peak}} \approx 1 - \eta_{\text{avg}}/B_f \approx 0.82$, rather than the average $90\%$ reduction.

3. **WarpX Ion-Impact MCC Model & Verification Status**:
   Standard WarpX built-in MCC handles electron-impact ionization. Proton-impact ionization ($p^+ + \text{Gas} \rightarrow p^+ + \text{Gas}^+ + e^-$) uses custom C++ source extensions. The current verification suite in `scripts/run_mcc_verification.py` evaluates **analytical collision-rate expectations** and placeholder rate benchmarks. The published paper must clearly label analytic rate expectations vs full 3D PIC tracking output. Full C++ PIC collision kernel runs must be completed before claiming validated self-consistent WarpX C++ PIC benchmarks in journal submission.

4. **Gas Scattering and Vacuum Load**:
   While $\text{Kr}$ operates at lower pressure ($10^{-6}\text{ Torr}$) due to a larger cross section, high-$Z$ gas scattering ($Z=36$) can contribute to small-angle beam emittance growth. Gas stripping and differential pumping requirements at $10^{-5}\text{ Torr}$ must be managed in practical injection line designs.

5. **Downstream Optics Modeling**:
   Downstream transport through the solenoid and quadrupole doublet is evaluated via space-charge envelope integration ($R_x(z), R_y(z)$) with effective perveance $K_{\text{eff}}$. Full 3D PIC tracking from buncher to inflector entrance can be performed for final machine commissioning.
