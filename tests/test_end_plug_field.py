"""Analytic end-plug fields of the PIC driver (task 107) match the potential they are derived from."""

from __future__ import annotations

import numpy as np
import pytest


def _eval(expr: str, x: float, y: float, z: float) -> float:
    return float(eval(expr, {"exp": np.exp, "x": x, "y": y, "z": z}))


def test_end_plug_disabled_by_default():
    from scripts.plasma_column_mcc_picmi_v7 import PlasmaColumnConfig, end_plug_field_expressions

    assert end_plug_field_expressions(PlasmaColumnConfig(), 0.0, 0.2) == {}


@pytest.mark.parametrize("z", [-0.012, 0.004, 0.1, 0.193, 0.21])
def test_end_plug_fields_match_potential(z):
    from scripts.plasma_column_mcc_picmi_v7 import PlasmaColumnConfig, end_plug_field_expressions

    V, w, r = 300.0, 0.01, 0.002
    ex = end_plug_field_expressions(PlasmaColumnConfig(end_plug_voltage=V, end_plug_width=w, end_plug_offset=0.0), 0.0, 0.2)

    def phi(zz: float) -> float:
        return -V * sum(np.exp(-(zz - zk) ** 2 / (2 * w * w)) for zk in (0.0, 0.2))

    h = 1e-5
    ez_fd = -(phi(z + h) - phi(z - h)) / (2 * h)
    phi2_fd = (phi(z + h) - 2 * phi(z) + phi(z - h)) / h**2
    assert _eval(ex["Ez_expression"], 0.0, 0.0, z) == pytest.approx(ez_fd, rel=1e-5, abs=1e-6)
    assert _eval(ex["Ex_expression"], r, 0.0, z) == pytest.approx(0.5 * r * phi2_fd, rel=1e-4, abs=1e-2)
    assert _eval(ex["Ey_expression"], 0.0, r, z) == pytest.approx(0.5 * r * phi2_fd, rel=1e-4, abs=1e-2)


def test_end_plug_repels_electrons_outward_of_the_cell_end():
    # Just outside the downstream end, the force on an electron (-e E_z) points away from the plug (+z).
    from scripts.plasma_column_mcc_picmi_v7 import PlasmaColumnConfig, end_plug_field_expressions

    ex = end_plug_field_expressions(PlasmaColumnConfig(end_plug_voltage=300.0, end_plug_width=0.01, end_plug_offset=0.0), 0.0, 0.2)
    assert -_eval(ex["Ez_expression"], 0.0, 0.0, 0.205) > 0.0
    assert -_eval(ex["Ez_expression"], 0.0, 0.0, 0.195) < 0.0  # inside: pushed back into the cell


def test_default_plug_sits_outside_the_seeded_cell():
    # Default: width 5 mm, centres 15 mm outside the ends -> < 2 % of V at the cell ends.
    from scripts.plasma_column_mcc_picmi_v7 import PlasmaColumnConfig

    cfg = PlasmaColumnConfig(end_plug_voltage=300.0)
    frac = np.exp(-(cfg.end_plug_offset ** 2) / (2 * cfg.end_plug_width ** 2))
    assert frac < 0.02
