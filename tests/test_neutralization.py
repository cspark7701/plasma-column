"""
tests/test_neutralization.py

Unit tests for analytical neutralization physics module.
"""

import sys
from pathlib import Path
import math
import numpy as np
import pytest

# Ensure src/ directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plasma_column.neutralization import (
    gas_density_m3,
    proton_beta_gamma_speed,
    ionization_tau_s,
    neutralization_fraction,
    keff_over_k0_from_eta,
    bunch_length_s,
    bunch_length_m,
    peak_keff_over_k0_from_average_eta,
    compute_neutralization_ratios,
)


def test_gas_density_deprecation():
    with pytest.warns(DeprecationWarning, match="gas_density_m3 has moved to plasma_column.gas"):
        n_gas = gas_density_m3(1.0e-5, 300.0)
    assert n_gas > 3.0e17 and n_gas < 3.5e17
    with pytest.warns(DeprecationWarning):
        assert gas_density_m3(0.0) == 0.0


def test_proton_kinematics_deprecation():
    with pytest.warns(DeprecationWarning, match="proton_beta_gamma_speed is deprecated"):
        beta, gamma, speed = proton_beta_gamma_speed(30.0)
    assert gamma > 1.0 and gamma < 1.001
    assert beta > 0.0075 and beta < 0.0085
    assert speed > 2.3e6 and speed < 2.5e6


def test_ionization_tau_deprecation():
    with pytest.warns(DeprecationWarning):
        n_gas = gas_density_m3(1.0e-5, 300.0)
        beta, gamma, speed = proton_beta_gamma_speed(30.0)
        sigma = 1.0e-20  # 1 A^2 cross section
        tau = ionization_tau_s(n_gas, sigma, speed)
    assert tau > 0 and not math.isinf(tau)


def test_neutralization_fraction():
    tau = 1.0e-4
    assert neutralization_fraction(0.0, tau) == 0.0
    val_at_tau = neutralization_fraction(tau, tau, eta_ss=1.0)
    assert math.isclose(val_at_tau, 1.0 - math.exp(-1.0), rel_tol=1e-5)

    t_arr = np.array([0.0, tau, 2.0 * tau])
    arr_res = neutralization_fraction(t_arr, tau)
    assert len(arr_res) == 3
    assert arr_res[0] == 0.0


def test_keff_over_k0():
    assert keff_over_k0_from_eta(0.0) == 1.0
    assert math.isclose(keff_over_k0_from_eta(0.9), 0.1, rel_tol=1e-5)


def test_bunch_length_deprecation():
    f_rf = 50.0e6  # 50 MHz
    phi = 36.0     # 36 degrees
    with pytest.warns(DeprecationWarning, match="bunch_length_s is deprecated"):
        dt = bunch_length_s(f_rf, phi)
    assert math.isclose(dt, 2.0e-9, rel_tol=1e-5)  # 2 ns

    with pytest.warns(DeprecationWarning):
        _, _, speed = proton_beta_gamma_speed(30.0)
        dz = bunch_length_m(speed, f_rf, phi)
    assert dz > 0.004 and dz < 0.006


def test_peak_perveance():
    # eta_avg = 0.9, bunching factor B_f = 5
    k_peak = peak_keff_over_k0_from_average_eta(0.9, 5.0)
    assert math.isclose(k_peak, 0.82, rel_tol=1e-5)

    with pytest.raises(ValueError):
        peak_keff_over_k0_from_average_eta(0.9, 0.0)


def test_neutralization_ratios_helper():
    eta_e, eta_net, k_e, k_net = compute_neutralization_ratios(100.0, 80.0, 10.0)
    assert math.isclose(eta_e, 0.8)
    assert math.isclose(eta_net, 0.7)
    assert math.isclose(k_e, 0.2)
    assert math.isclose(k_net, 0.3)


if __name__ == "__main__":
    pytest.main([__file__])
