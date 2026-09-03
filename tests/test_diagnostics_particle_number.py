"""
tests/test_diagnostics_particle_number.py

Unit tests for particle number diagnostic parsing and local core neutralization metrics.
"""

import sys
from pathlib import Path
import tempfile
import textwrap
import numpy as np
import pandas as pd
import pytest

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plasma_column.diagnostics import (
    load_particle_number_diagnostic,
    compute_particle_number_metrics,
    compute_local_core_neutralization,
    warn_global_count_limitation,
    safe_eta,
)


def test_safe_eta_scalar_and_vector():
    """Verify safe_eta handles scalars and NumPy arrays with zero-division guard."""
    # Scalar normal
    eta_e, eta_net = safe_eta(100.0, 20.0, 100.0)
    assert eta_e == pytest.approx(1.0)
    assert eta_net == pytest.approx(0.8)

    # Scalar zero proton (guard prevents division by zero)
    eta_e_0, eta_net_0 = safe_eta(10.0, 0.0, 0.0)
    assert eta_e_0 > 0.0

    # Vector
    ne = np.array([0.0, 50.0, 90.0])
    ni = np.array([0.0, 10.0, 20.0])
    np_arr = np.array([100.0, 100.0, 100.0])
    eta_e_vec, eta_net_vec = safe_eta(ne, ni, np_arr)
    np.testing.assert_allclose(eta_e_vec, [0.0, 0.5, 0.9])
    np.testing.assert_allclose(eta_net_vec, [0.0, 0.4, 0.7])


def test_particle_number_parsing():
    content = textwrap.dedent("""\
        # step time species0_macro species1_macro species2_macro Np Ne Ni
        0 0.0 100 0 0 1000 0 0
        1 1e-9 100 50 10 1000 500 100
        2 2e-9 100 90 20 1000 900 200
    """)
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        df = load_particle_number_diagnostic(tmp_path)
        assert len(df) == 3
        assert "Np" in df.columns or "col_0" in df.columns
    finally:
        tmp_path.unlink()


def test_particle_number_metrics():
    data = {
        "step": [0, 1, 2],
        "time": [0.0, 1e-9, 2e-9],
        "Np": [1000.0, 1000.0, 1000.0],
        "Ne": [0.0, 500.0, 900.0],
        "Ni": [0.0, 100.0, 200.0],
    }
    df = pd.DataFrame(data)

    with pytest.warns(UserWarning, match="Global particle-number ratios"):
        res = compute_particle_number_metrics(df)

    assert "eta_electron_only" in res.columns
    assert "eta_net" in res.columns
    assert "keff_over_k0" in res.columns

    # Row 2 check: Ne=900, Ni=200, Np=1000 -> eta_electron=0.9, eta_net=0.7, K_eff/K0=0.3
    assert res.loc[2, "eta_electron_only"] == 0.9
    assert res.loc[2, "eta_net"] == 0.7
    assert pytest.approx(res.loc[2, "keff_over_k0"]) == 0.3


def test_local_core_neutralization():
    x = np.linspace(-0.005, 0.005, 10)
    y = np.linspace(-0.005, 0.005, 10)
    z = np.linspace(-0.05, 0.25, 20)

    shape = (len(x), len(y), len(z))
    np_3d = np.ones(shape) * 1.0e15
    ne_3d = np.ones(shape) * 0.9e15
    ni_3d = np.ones(shape) * 0.1e15

    res = compute_local_core_neutralization(
        ne_3d, ni_3d, np_3d, x, y, z, z_min_col=0.0, z_max_col=0.20, r_core=0.002
    )

    assert res["np_core_avg"] == 1.0e15
    assert res["ne_core_avg"] == 0.9e15
    assert res["ni_core_avg"] == 0.1e15
    assert pytest.approx(res["eta_net_local"]) == 0.8
    assert pytest.approx(res["keff_over_k0_local"]) == 0.2


if __name__ == "__main__":
    pytest.main([__file__])


def test_load_particle_number_diagnostic_restart_deduplication():
    import tempfile, shutil
    from plasma_column.diagnostics import load_particle_number_diagnostic

    td = Path(tempfile.mkdtemp())
    try:
        rdir = td / "reducedfiles"
        rdir.mkdir()
        pn_file = rdir / "particle_number.txt"
        # Simulate an appended/restarted file with overlapping steps
        content = (
            "#[0]step() [1]time(s) [2]tot_macro [3]p_macro [4]e_macro [5]p_phys [6]e_phys [7]i_phys\n"
            "0 0.0 10 10 0 1e8 0 0\n"
            "1 1e-12 10 10 0 1e8 0 0\n"
            "2 2e-12 10 10 0 1e8 0 0\n"
            "# restart\n"
            "2 2e-12 10 10 0 1e8 0 0\n"
            "3 3e-12 10 10 0 1e8 0 0\n"
            "4 4e-12 10 10 0 1e8 0 0\n"
        )
        pn_file.write_text(content)
        df = load_particle_number_diagnostic(pn_file)
        assert not df.empty
        assert len(df) == 5  # steps 0, 1, 2, 3, 4 without duplicates
        assert list(df["step"]) == [0, 1, 2, 3, 4]
    finally:
        shutil.rmtree(td)
