"""Hard-edge quadrupole fields of the PIC driver (task CW3 section model)."""

from __future__ import annotations

import pytest


def _eval(expr: str, x: float, y: float, z: float) -> float:
    return float(eval(expr, {"x": x, "y": y, "z": z}))


def test_no_quadrupoles_gives_zero_fields():
    from scripts.plasma_column_mcc_picmi_v7 import quadrupole_field_expressions

    assert quadrupole_field_expressions("") == {"Bx_expression": "0.0", "By_expression": "0.0"}


@pytest.mark.parametrize("z, g", [(0.5, -0.28), (0.7, 0.85), (0.62, 0.0), (0.9, 0.0)])
def test_quadrupole_gradients_inside_and_outside(z, g):
    from scripts.plasma_column_mcc_picmi_v7 import quadrupole_field_expressions

    f = quadrupole_field_expressions("0.47:0.59:-0.28;0.67:0.79:0.85")
    x, y = 0.003, -0.002
    assert _eval(f["Bx_expression"], x, y, z) == pytest.approx(g * y)
    assert _eval(f["By_expression"], x, y, z) == pytest.approx(g * x)


def test_positive_gradient_focuses_protons_in_x():
    from scripts.plasma_column_mcc_picmi_v7 import quadrupole_field_expressions

    f = quadrupole_field_expressions("0.0:1.0:1.0")
    x, vz = 0.004, 2.4e6
    By = _eval(f["By_expression"], x, 0.0, 0.5)
    Fx = -vz * By  # F = q v x B, x-component = q (v_y B_z - v_z B_y), q > 0
    assert Fx < 0


def test_hard_edge_solenoid_unchanged():
    from scripts.plasma_column_mcc_picmi_v7 import solenoid_field_expressions

    f = solenoid_field_expressions(0.15, 0.0, 0.2, 0.0)
    assert f["Bx_expression"] == "0.0"
    assert _eval(f["Bz_expression"], 0, 0, 0.1) == pytest.approx(0.15)
    assert _eval(f["Bz_expression"], 0, 0, 0.3) == 0.0


def test_fringe_solenoid_is_divergence_free_paraxially():
    import math

    from scripts.plasma_column_mcc_picmi_v7 import solenoid_field_expressions

    f = solenoid_field_expressions(0.23, 0.10, 0.35, 0.02)
    ev = lambda e, x, y, z: float(eval(e, {"x": x, "y": y, "z": z, "tanh": math.tanh}))
    assert ev(f["Bz_expression"], 0, 0, 0.225) == pytest.approx(0.23, rel=1e-3)
    assert ev(f["Bz_expression"], 0, 0, 0.10) == pytest.approx(0.115, rel=1e-3)
    h, x, z = 1e-6, 0.003, 0.11
    div = ((ev(f["Bx_expression"], x + h, 0, z) - ev(f["Bx_expression"], x - h, 0, z)) / (2 * h)
           + (ev(f["By_expression"], x, h, z) - ev(f["By_expression"], x, -h, z)) / (2 * h)
           + (ev(f["Bz_expression"], x, 0, z + h) - ev(f["Bz_expression"], x, 0, z - h)) / (2 * h))
    dbz = (ev(f["Bz_expression"], 0, 0, z + h) - ev(f["Bz_expression"], 0, 0, z - h)) / (2 * h)
    assert abs(div) < 1e-6 * abs(dbz)
    # Entrance (dB_z/dz > 0): B_r < 0, as for a real solenoid.
    assert ev(f["Bx_expression"], x, 0, z) < 0
