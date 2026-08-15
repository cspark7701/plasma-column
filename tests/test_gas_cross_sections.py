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


if __name__ == "__main__":
    pytest.main([__file__])
