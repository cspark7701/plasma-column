"""
tests/test_gas_cross_sections.py

Unit tests for gas properties, cross-section table parsing, and interpolation.
"""

import math
import sys
from pathlib import Path
import tempfile
import textwrap
import numpy as np
import pytest

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plasma_column.gas import (
    NeutralGas,
    gas_density_m3,
    ionization_tau_s,
    mean_free_path_m,
    transmission_fraction,
    multiple_scattering_rms_rad,
    lab_to_cm_energy,
    cm_to_lab_energy,
    load_cross_section_table,
    interpolate_cross_section,
    CrossSectionDatabase,
    MH2,
    MKR,
    MP,
)


def test_neutral_gas():
    gas_h2 = NeutralGas(species="H2", pressure_torr=1.0e-5, temperature_K=300.0)
    assert gas_h2.number_density > 3.0e17 and gas_h2.number_density < 3.5e17

    gas_kr = NeutralGas(species="Kr", pressure_torr=1.0e-6, temperature_K=300.0)
    assert gas_kr.number_density > 3.0e16 and gas_kr.number_density < 3.5e16

    with pytest.raises(ValueError):
        NeutralGas(species="Unknown").mass


def test_energy_frame_conversions():
    # 30 keV proton on H2 (m_target ~= 2 m_p)
    e_lab = 30000.0
    e_cm = lab_to_cm_energy(e_lab, MP, MH2)
    assert pytest.approx(e_cm, rel=1e-3) == 20000.0

    e_lab_back = cm_to_lab_energy(e_cm, MP, MH2)
    assert pytest.approx(e_lab_back) == e_lab


def test_cross_section_table_parsing_and_interp():
    content = textwrap.dedent("""\
        # Reaction: p + Test -> p + Test+ + e-
        # target_mass : 2.0
        0.00000000e+00 0.00000000e+00
        1.00000000e+04 1.00000000e-20
        2.00000000e+04 2.00000000e-20
        3.00000000e+04 1.50000000e-20
    """)
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".dat") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        energies, sigmas, meta = load_cross_section_table(tmp_path)
        assert len(energies) == 4
        assert len(sigmas) == 4
        assert "target_mass" in meta

        # Interpolation test
        sig_interp = interpolate_cross_section(energies, sigmas, 15000.0)
        assert pytest.approx(sig_interp) == 1.5e-20
    finally:
        tmp_path.unlink()


def test_database_lookup():
    db = CrossSectionDatabase()
    sig_h2 = db.get_proton_impact_cross_section("H2", 30000.0)
    sig_kr = db.get_proton_impact_cross_section("Kr", 30000.0)

    assert sig_h2 > 1.5e-20 and sig_h2 < 1.7e-20
    assert sig_kr > 8.0e-20 and sig_kr < 1.0e-19

def test_gas_density_and_ionization_tau():
    """Verify gas_density_m3 and ionization_tau_s functions in gas.py."""
    ng = gas_density_m3(1.0e-5, 300.0)
    assert 3.0e17 < ng < 3.5e17
    assert gas_density_m3(0.0) == 0.0

    tau = ionization_tau_s(ng, 1.6e-20, 2.4e6)
    assert 0.0 < tau < 1.0
    assert math.isinf(ionization_tau_s(0.0, 1.0, 1.0))


def test_mean_free_path_and_transmission():
    """Verify mean_free_path_m and transmission_fraction formulas."""
    ng = gas_density_m3(1.0e-5, 300.0)  # ~3.2e17 m^-3
    sigma = 1.6e-20                     # m^2

    mfp = mean_free_path_m(ng, sigma)
    # lambda = 1 / (3.2e17 * 1.6e-20) ~ 194 m
    assert 150.0 < mfp < 250.0
    assert math.isinf(mean_free_path_m(0.0, sigma))

    # Transmission over 0.20 m cell
    t_frac = transmission_fraction(ng, sigma, 0.20)
    assert 0.998 < t_frac < 1.0
    assert transmission_fraction(0.0, sigma, 0.20) == 1.0


def test_multiple_coulomb_scattering():
    """Verify multiple_scattering_rms_rad Highland formula for 30 keV protons in H2 and Kr."""
    # 30 keV protons in 1e-5 Torr H2 over 0.20 m cell
    theta_h2 = multiple_scattering_rms_rad(
        energy_keV=30.0,
        gas_species="H2",
        pressure_torr=1.0e-5,
        length_m=0.20,
    )
    assert 0.0 < theta_h2 < 0.001  # < 1 mrad (negligible scattering)

    # 30 keV protons in 1e-6 Torr Kr over 0.20 m cell
    theta_kr = multiple_scattering_rms_rad(
        energy_keV=30.0,
        gas_species="Kr",
        pressure_torr=1.0e-6,
        length_m=0.20,
    )
    assert 0.0 < theta_kr < 0.001

    # Vacuum / zero pressure -> 0.0 scattering angle
    assert multiple_scattering_rms_rad(30.0, "H2", 0.0, 0.20) == 0.0
    assert multiple_scattering_rms_rad(30.0, "none", 1.0e-5, 0.20) == 0.0

    # Invalid species raises ValueError
    with pytest.raises(ValueError, match="Unknown gas species"):
        multiple_scattering_rms_rad(30.0, "Argon", 1.0e-5, 0.20)


def test_mcc_script_interp_sigma_matches_gas_db():
    """Verify scripts/plasma_column_mcc_picmi_v7.py interp_sigma evaluates consistently with CrossSectionDatabase."""
    from scripts.plasma_column_mcc_picmi_v7 import interp_sigma, get_cross_section_dir, PlasmaColumnConfig

    cfg_h2 = PlasmaColumnConfig(gas="H2", beam_energy_keV=30.0)
    xsec_dir = get_cross_section_dir(cfg_h2)
    xsec_file = xsec_dir / "proton_impact_ionization.dat"

    if xsec_file.exists():
        e_cm_eV = 30000.0 * MH2 / (MP + MH2)
        sigma_mcc = interp_sigma(xsec_file, e_cm_eV)
        db = CrossSectionDatabase()
        sigma_db = db.get_proton_impact_cross_section("H2", 30000.0)
        assert math.isclose(sigma_mcc, sigma_db, rel_tol=1e-6)
        assert 1.0e-21 < sigma_mcc < 1.0e-19


if __name__ == "__main__":
    pytest.main([__file__])
