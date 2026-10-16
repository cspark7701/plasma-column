"""
tests/test_local_neutralization_masks.py

Unit tests for local beam-core compensation masks, displaced electron clouds,
overcompensation detection, and z-resolved profile diagnostics.
"""

import sys
from pathlib import Path
import numpy as np
import pytest

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plasma_column.diagnostics import (
    compute_local_core_neutralization,
    compute_local_neutralization_vs_z,
    compute_radial_density_profiles,
    compute_beam_core_charge_density,
    warn_global_count_limitation,
    GLOBAL_WARNING_MSG,
)
from plasma_column._testing import generate_synthetic_3d_grid


def test_uniform_density_neutralization():
    """Verify uniform proton/electron density gives exact expected local eta."""
    ne_3d, ni_3d, np_3d, x, y, z = generate_synthetic_3d_grid(
        n_proton_peak=1.0e15, eta_target=0.8, displaced_x=0.0, overcompensated=False
    )

    res = compute_local_core_neutralization(ne_3d, ni_3d, np_3d, x, y, z, r_core=0.002)

    assert res["np_core_avg"] > 0.0
    assert 0.75 < res["eta_net_local"] < 0.85
    assert 0.15 < res["keff_over_k0_local"] < 0.25
    assert not res["overcompensated"]


def test_displaced_electron_cloud_poor_compensation():
    """Verify displaced electron cloud gives low beam-core compensation despite high electron count."""
    # Centered beam with electron cloud displaced laterally by 10 mm (well outside r_core = 2 mm)
    ne_3d, ni_3d, np_3d, x, y, z = generate_synthetic_3d_grid(
        n_proton_peak=1.0e15, eta_target=1.0, displaced_x=0.010
    )

    res = compute_local_core_neutralization(ne_3d, ni_3d, np_3d, x, y, z, r_core=0.002)

    # Core electron density should be near zero because of 10 mm displacement
    assert res["eta_net_local"] < 0.05
    assert res["keff_over_k0_local"] > 0.95


def test_overcompensation_flagging():
    """Verify overcompensation gives negative K_eff/K0 and sets overcompensated flag."""
    ne_3d, ni_3d, np_3d, x, y, z = generate_synthetic_3d_grid(
        n_proton_peak=1.0e15, eta_target=1.2, overcompensated=True
    )

    res = compute_local_core_neutralization(ne_3d, ni_3d, np_3d, x, y, z, r_core=0.002)

    assert res["eta_net_local"] > 1.0
    assert res["keff_over_k0_local"] < 0.0
    assert res["overcompensated"] is True


def test_missing_local_diagnostics_warning(capsys):
    """Verify missing local diagnostics emits explicit limitation warning."""
    with pytest.warns(UserWarning, match="Global particle-number ratios"):
        warn_global_count_limitation()
    captured = capsys.readouterr()
    assert GLOBAL_WARNING_MSG in captured.out


def test_z_resolved_and_radial_profiles():
    """Verify z-resolved and radial profile DataFrames are structured correctly."""
    ne_3d, ni_3d, np_3d, x, y, z = generate_synthetic_3d_grid()

    df_z = compute_local_neutralization_vs_z(ne_3d, ni_3d, np_3d, x, y, z, r_core=0.002)
    assert len(df_z) == len(z)
    assert "eta_net_local_z" in df_z.columns
    assert "keff_over_k0_local_z" in df_z.columns

    df_r = compute_radial_density_profiles(ne_3d, ni_3d, np_3d, x, y, z, n_bins=20)
    assert len(df_r) == 20
    assert "np_r" in df_r.columns
    assert "rho_net_r" in df_r.columns

    charge_density = compute_beam_core_charge_density(ne_3d, ni_3d, np_3d, x, y, z)
    assert "rho_p" in charge_density
    assert "rho_e" in charge_density
    assert "rho_net" in charge_density


def test_radial_density_profile_vectorization():
    """Verify vectorized binned_statistic preserves peak on-axis density and monotonic decay."""
    ne_3d, ni_3d, np_3d, x, y, z = generate_synthetic_3d_grid(
        n_proton_peak=1.0e15, eta_target=0.8, displaced_x=0.0
    )
    df_r = compute_radial_density_profiles(ne_3d, ni_3d, np_3d, x, y, z, n_bins=30)
    assert len(df_r) == 30
    assert df_r["np_r"].iloc[0] > df_r["np_r"].iloc[-1]
    assert df_r["ne_r"].iloc[0] > df_r["ne_r"].iloc[-1]
    assert not df_r.isna().any().any()


def test_vectorized_neutralization_vs_z_equivalence():
    """Verify vectorized compute_local_neutralization_vs_z produces valid profiles and handles empty masks."""
    ne_3d, ni_3d, np_3d, x, y, z = generate_synthetic_3d_grid(
        nx=24, ny=24, nz=128, n_proton_peak=1.0e15, eta_target=0.85
    )

    df_z = compute_local_neutralization_vs_z(ne_3d, ni_3d, np_3d, x, y, z, r_core=0.002)
    assert len(df_z) == 128
    assert np.all(df_z["eta_net_local_z"] > 0.5)
    assert np.all(df_z["keff_over_k0_local_z"] < 0.5)
    assert not df_z.isna().any().any()

    # Edge case: zero radius core (empty mask)
    df_empty = compute_local_neutralization_vs_z(ne_3d, ni_3d, np_3d, x, y, z, r_core=0.0)
    assert len(df_empty) == 128
    assert np.all(df_empty["eta_net_local_z"] == 0.0)
    assert np.all(df_empty["keff_over_k0_local_z"] == 1.0)


def test_beam_not_in_column_gives_undefined_eta():
    """Beam front upstream of the column: eta must be NaN and flagged, not ne/eps (~1e45)."""
    ne_3d, ni_3d, np_3d, x, y, z = generate_synthetic_3d_grid(z_min=-0.02, z_max=0.24, nz=105)
    np_3d[:, :, z > -0.012] = 0.0  # beam front at z = -12 mm, column starts at z = 0

    res = compute_local_core_neutralization(ne_3d, ni_3d, np_3d, x, y, z, r_core=0.002)

    assert res["beam_in_core"] is False
    assert np.isnan(res["eta_net_local"])
    assert np.isnan(res["keff_over_k0_local"])
    assert not res["overcompensated"]
    assert res["beam_z_max_m"] < 0.0

    df_z = compute_local_neutralization_vs_z(ne_3d, ni_3d, np_3d, x, y, z, r_core=0.002)
    assert df_z.loc[df_z["z"] > -0.012, "eta_net_local_z"].isna().all()
    assert df_z.loc[df_z["z"] < -0.013, "eta_net_local_z"].notna().all()


def test_partial_beam_fill_averages_only_beam_cells():
    """Beam halfway into the column: eta uses only cells the beam occupies."""
    ne_3d, ni_3d, np_3d, x, y, z = generate_synthetic_3d_grid(eta_target=0.8)
    np_3d[:, :, z > 0.10] = 0.0

    res = compute_local_core_neutralization(ne_3d, ni_3d, np_3d, x, y, z, r_core=0.002)

    assert res["beam_in_core"] is True
    assert 0.75 < res["eta_net_local"] < 0.85
    assert 0.3 < res["core_beam_fill_fraction"] < 0.7


def test_find_plotfiles_ignores_old_and_sorts_by_step(tmp_path):
    """'diag1010000.old.6486587' (from a repeated run) must not be picked as the latest plotfile."""
    from plasma_column.warpx_io import find_plotfiles

    for name in ["diag1000000", "diag1009875", "diag1010000", "diag1010000.old.6486587"]:
        (tmp_path / "diags" / name).mkdir(parents=True)

    names = [p.name for p in find_plotfiles(tmp_path)]
    assert names == ["diag1000000", "diag1009875", "diag1010000"]
