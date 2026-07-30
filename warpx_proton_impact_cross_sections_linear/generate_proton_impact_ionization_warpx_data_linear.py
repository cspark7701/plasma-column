#!/usr/bin/env python3
"""
generate_proton_impact_ionization_warpx_data_linear.py

Generate WarpX-style two-column cross-section files for:
    p + H2 -> p + H2+ + e-
    p + Kr -> p + Kr+ + e-

Output format required by WarpX MCC:
    column 1: equally spaced center-of-mass collision energy [eV]
    column 2: total ionization/electron-production cross section [m^2]

The cross sections are generated from the Rudd semi-empirical proton-impact
ionization model:
    M. E. Rudd et al., Rev. Mod. Phys. 64, 441 (1992).
"""

from __future__ import annotations

from pathlib import Path
import argparse
import math
import numpy as np

A0 = 5.29177210903e-11
RY = 13.605693122994
ME = 9.1093837015e-31
MP = 1.67262192369e-27
AMU = 1.66053906660e-27

RUDD_PARAMS = {
    "H2": (0.96, 2.6, 0.38, 0.23, 2.2, 1.04, 5.9, 1.15, 0.20, 0.87),
    "Kr": (1.46, 5.7, 0.65, -0.55, 1.0, 1.30, 22.0, 0.95, -1.00, 0.78),
}

TARGETS = {
    "H2": {"mass": 2.01588 * AMU, "N": 2.0, "I_eV": 15.43,
           "reaction": "p + H2 -> p + H2+ + e-"},
    "Kr": {"mass": 83.798 * AMU, "N": 8.0, "I_eV": 14.00,
           "reaction": "p + Kr -> p + Kr+ + e-"},
}


def rudd_total_sigma_lab(E_lab_eV: float, target: str, n_w: int = 12000) -> float:
    A1, B1, C1, D1, E1, A2, B2, C2, D2, alpha = RUDD_PARAMS[target]
    N = TARGETS[target]["N"]
    I = TARGETS[target]["I_eV"]
    m_t = TARGETS[target]["mass"]

    E_thr_lab = I * (MP + m_t) / m_t
    if E_lab_eV <= E_thr_lab:
        return 0.0

    T = (ME / MP) * E_lab_eV
    if T <= 0.0:
        return 0.0

    v = math.sqrt(T / I)

    H1 = A1 * math.log(1.0 + v**2) / (v**2 + B1 / v**2)
    L1 = C1 * v**D1 / (1.0 + E1 * v**(D1 + 4.0))
    F1 = L1 + H1

    H2 = A2 / v**2 + B2 / v**4
    L2 = C2 * v**D2
    F2 = L2 * H2 / (L2 + H2)

    wc = 4.0 * v**2 - 2.0 * v - RY / (4.0 * I)
    S = 4.0 * math.pi * A0**2 * N * (RY / I)**2

    w_max = max(100.0, wc + 40.0 * max(v, 1.0) / alpha)
    w = np.logspace(-10.0, math.log10(w_max), n_w)

    with np.errstate(over="ignore", invalid="ignore"):
        dsdW = (S / I) * (F1 + F2 * w) / (1.0 + w)**3
        dsdW /= (1.0 + np.exp(alpha * (w - wc) / v))

    sigma = np.trapz(dsdW * I, w)
    return float(max(sigma, 0.0))


def cm_to_lab(E_cm_eV: np.ndarray | float, target: str):
    mt = TARGETS[target]["mass"]
    return np.asarray(E_cm_eV) * (MP + mt) / mt


def lab_to_cm(E_lab_eV: np.ndarray | float, target: str):
    mt = TARGETS[target]["mass"]
    return np.asarray(E_lab_eV) * mt / (MP + mt)


def write_table(path: Path, target: str, e_cm_max=1.0e6, n=10001):
    path.parent.mkdir(parents=True, exist_ok=True)
    E_cm = np.linspace(0.0, e_cm_max, n)
    E_lab = cm_to_lab(E_cm, target)
    sigma = np.array([rudd_total_sigma_lab(float(E), target) for E in E_lab])

    ecm_30keV = float(lab_to_cm(3.0e4, target))
    sig_30keV = rudd_total_sigma_lab(3.0e4, target)

    header = f"""# WarpX MCC cross-section file
# Reaction: {TARGETS[target]["reaction"]}
# Columns:
#   1: center-of-mass collision energy [eV]
#   2: total ionization/electron-production cross section [m^2]
# Energy grid:
#   equally spaced, as required by WarpX MCC
# Source/model:
#   Rudd semi-empirical proton-impact ionization model,
#   M. E. Rudd et al., Rev. Mod. Phys. 64, 441 (1992).
# Target parameters:
#   target = {target}
#   N_effective = {TARGETS[target]["N"]}
#   I = {TARGETS[target]["I_eV"]} eV
#   target_mass = {TARGETS[target]["mass"]:.16e} kg
# 30 keV lab diagnostic:
#   E_cm = {ecm_30keV:.8e} eV
#   sigma = {sig_30keV:.8e} m^2
"""
    with path.open("w") as f:
        f.write(header)
        for e, s in zip(E_cm, sigma):
            f.write(f"{e:.8e} {s:.8e}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output_dir", default="MCC_cross_sections")
    p.add_argument("--e_cm_max", type=float, default=1.0e6)
    p.add_argument("--n", type=int, default=10001)
    args = p.parse_args()

    out = Path(args.output_dir)
    write_table(out / "H2" / "proton_impact_ionization.dat", "H2",
                e_cm_max=args.e_cm_max, n=args.n)
    write_table(out / "Kr" / "proton_impact_ionization.dat", "Kr",
                e_cm_max=args.e_cm_max, n=args.n)


if __name__ == "__main__":
    main()
