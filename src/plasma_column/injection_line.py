"""
src/plasma_column/injection_line.py

Downstream axial-injection optics line and space-charge beam envelope model:
buncher -> plasma neutralizer -> solenoid -> quadrupole Q1 -> quadrupole Q2 -> spiral inflector
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence, Union
import numpy as np
from scipy.integrate import solve_ivp

from plasma_column.beam import ProtonBeam, RFFocusedBeam
from plasma_column.constants import C, QE, MP


@dataclass
class Element:
    name: str
    length: float  # [m]


@dataclass
class Drift(Element):
    pass


@dataclass
class Solenoid(Element):
    Bz: float  # [T]


@dataclass
class Quadrupole(Element):
    gradient: float  # [T/m] (positive = focusing in X, negative = focusing in Y)


@dataclass
class InjectionLine:
    """
    Compact-cyclotron axial injection beamline layout:
    buncher exit -> plasma neutralizer -> solenoid -> Q1 -> Q2 -> inflector entrance
    """
    plasma_cell_length: float = 0.20
    drift1_length: float = 0.10
    solenoid_length: float = 0.25
    solenoid_field_T: float = 0.15
    drift2_length: float = 0.10
    q1_length: float = 0.12
    q1_gradient_Tm: float = 5.0
    drift3_length: float = 0.08
    q2_length: float = 0.12
    q2_gradient_Tm: float = -4.5
    drift4_length: float = 0.15

    @property
    def total_length(self) -> float:
        return (
            self.plasma_cell_length
            + self.drift1_length
            + self.solenoid_length
            + self.drift2_length
            + self.q1_length
            + self.drift3_length
            + self.q2_length
            + self.drift4_length
        )

    def get_element_at(self, z: float) -> tuple[str, float, float]:
        """
        Returns (element_name, Kx_focusing_k2, Ky_focusing_k2) at position z [m].
        """
        z_curr = 0.0

        # Plasma cell
        if z < z_curr + self.plasma_cell_length:
            return "plasma_neutralizer", 0.0, 0.0
        z_curr += self.plasma_cell_length

        # Drift 1
        if z < z_curr + self.drift1_length:
            return "drift1", 0.0, 0.0
        z_curr += self.drift1_length

        # Solenoid
        if z < z_curr + self.solenoid_length:
            return "solenoid", 0.0, 0.0  # Handled separately via Solenoid matrix/k_sol
        z_curr += self.solenoid_length

        # Drift 2
        if z < z_curr + self.drift2_length:
            return "drift2", 0.0, 0.0
        z_curr += self.drift2_length

        # Q1
        if z < z_curr + self.q1_length:
            return "quad_Q1", self.q1_gradient_Tm, -self.q1_gradient_Tm
        z_curr += self.q1_length

        # Drift 3
        if z < z_curr + self.drift3_length:
            return "drift3", 0.0, 0.0
        z_curr += self.drift3_length

        # Q2
        if z < z_curr + self.q2_length:
            return "quad_Q2", self.q2_gradient_Tm, -self.q2_gradient_Tm
        z_curr += self.q2_length

        # Drift 4
        return "drift4_to_inflector", 0.0, 0.0


def compute_beam_envelope(
    beam: ProtonBeam,
    injection_line: InjectionLine,
    eta_net: Optional[float] = None,
    eta_cell: Optional[float] = None,
    eta_downstream: float = 0.0,
    keff_func: Optional[Callable[[float], float]] = None,
    r0_m: float = 0.002,
    rp0_rad: float = 0.0,
    emittance_n_mrad: float = 1.0e-6,
    n_points: int = 500,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Integrates 2D beam envelope equations (Rx, Ry) from buncher exit to inflector entrance.

    Supports:
    1. Region-dependent neutralization:
       - eta_cell: Neutralization fraction inside the plasma neutralizer cell (0 <= z <= L_cell).
       - eta_downstream: Neutralization fraction in downstream drift and matching elements (z > L_cell).
         Defaults to 0.0 (high-vacuum downstream transport).
    2. Arbitrary z-dependent perveance function keff_func(z) -> K_eff.
    3. Backwards compatibility: if eta_net is provided and eta_cell is None, eta_cell is set to eta_net.

    Returns:
        tuple of (z_eval, Rx_arr, Ry_arr) in meters and radians.
    """
    beta = beam.beta
    gamma = beam.gamma
    p_momentum = gamma * MP * beam.velocity
    K0 = beam.perveance_K0
    emittance_geom = emittance_n_mrad / (beta * gamma)

    # Resolve neutralization parameters
    if eta_cell is None:
        if eta_net is not None:
            eta_c = float(eta_net)
        else:
            eta_c = 0.0
    else:
        eta_c = float(eta_cell)

    eta_d = float(eta_downstream)
    L_cell = injection_line.plasma_cell_length

    # Solenoid focusing parameter k_sol = e * B / (2 * p)
    k_sol = (QE * injection_line.solenoid_field_T) / (2.0 * p_momentum)

    # Quadrupole magnetic rigidity focal strength factor: e / p
    quad_factor = QE / p_momentum

    def get_keff(z: float) -> float:
        if keff_func is not None:
            return float(keff_func(z))
        if z <= L_cell:
            return float(K0 * max(0.0, 1.0 - eta_c))
        else:
            return float(K0 * max(0.0, 1.0 - eta_d))

    def envelope_ode(z: float, state: np.ndarray) -> list[float]:
        Rx, dRx, Ry, dRy = state
        Rx = max(Rx, 1.0e-6)
        Ry = max(Ry, 1.0e-6)

        elem_name, g_x, g_y = injection_line.get_element_at(z)
        K_eff_local = get_keff(z)

        # Focusing terms
        kx2 = 0.0
        ky2 = 0.0

        if elem_name == "solenoid":
            kx2 = k_sol**2
            ky2 = k_sol**2
        elif elem_name.startswith("quad"):
            kx2 = g_x * quad_factor
            ky2 = g_y * quad_factor

        # Envelope ODEs
        d2Rx = -kx2 * Rx + (2.0 * K_eff_local) / (Rx + Ry) + (emittance_geom**2) / (Rx**3)
        d2Ry = -ky2 * Ry + (2.0 * K_eff_local) / (Rx + Ry) + (emittance_geom**2) / (Ry**3)

        return [dRx, d2Rx, dRy, d2Ry]

    z_eval = np.linspace(0.0, injection_line.total_length, n_points)
    initial_state = [r0_m, rp0_rad, r0_m, rp0_rad]

    sol = solve_ivp(envelope_ode, (0.0, injection_line.total_length), initial_state, t_eval=z_eval, method="RK45")

    Rx_arr = sol.y[0]
    Ry_arr = sol.y[2]

    return z_eval, Rx_arr, Ry_arr
