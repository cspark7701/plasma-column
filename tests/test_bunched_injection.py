"""RF-bunched beam injection profile of the PIC driver (task B2 of docs/physics_notes/simulation_strategy_tasks.md)."""

from __future__ import annotations

import math

import numpy as np
import pytest


def _profile(cfg, t):
    from scripts.plasma_column_mcc_picmi_v7 import bunched_flux_expression

    expr = bunched_flux_expression(cfg, 1.0)
    return eval(expr, {"exp": np.exp, "cos": np.cos, "t": t})


def test_dc_beam_has_no_bunching():
    from scripts.plasma_column_mcc_picmi_v7 import bunch_profile_kappa

    assert bunch_profile_kappa(1.0, 36.0) == 0.0


@pytest.mark.parametrize("bf", [2.0, 5.0, 8.0])
def test_bunched_profile_keeps_average_current_and_window_fraction(bf):
    from scripts.plasma_column_mcc_picmi_v7 import PlasmaColumnConfig

    cfg = PlasmaColumnConfig(beam_bunching_factor=bf, rf_frequency_hz=50e6, bunch_acceptance_deg=36.0)
    T = 1.0 / cfg.rf_frequency_hz
    t = (np.arange(36000) + 0.5) / 36000 * T - 0.5 * T  # one period centred on the bunch
    f = _profile(cfg, t)
    assert f.mean() == pytest.approx(1.0, rel=1e-6)  # average current unchanged
    window = np.abs(t) <= (18.0 / 360.0) * T
    frac = f[window].sum() / f.sum()
    assert frac / (36.0 / 360.0) == pytest.approx(bf, rel=1e-3)  # B_f inside the 36 deg acceptance
