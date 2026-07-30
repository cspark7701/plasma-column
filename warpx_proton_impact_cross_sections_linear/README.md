# Proton-impact ionization cross sections for WarpX MCC

This package contains WarpX-style two-column cross-section files with **equally spaced**
center-of-mass energies:

- `MCC_cross_sections/H2/proton_impact_ionization.dat`
- `MCC_cross_sections/Kr/proton_impact_ionization.dat`

Reactions:

- `p + H2 -> p + H2+ + e-`
- `p + Kr -> p + Kr+ + e-`

Columns:

1. center-of-mass collision energy [eV]
2. total ionization/electron-production cross section [m^2]

The data are generated from the Rudd semi-empirical proton-impact ionization model:
M. E. Rudd et al., Rev. Mod. Phys. 64, 441 (1992).

The files use a linear, equally spaced center-of-mass energy grid from 0 to 1 MeV
with 10001 points.
