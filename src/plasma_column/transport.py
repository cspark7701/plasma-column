"""
src/plasma_column/transport.py

Matched envelope transport from the buncher exit to the spiral-inflector entrance
(buncher -> plasma neutralizer -> solenoid -> Q1 -> Q2 -> spiral inflector), with a z-dependent
perveance K(z) for compensation and longitudinal bunching (task 106).

Model:
    KV (uniform-density) envelope equations for the edge radii,
        R_x'' = -k_x(z) R_x + 2 K(z) / (R_x + R_y) + eps^2 / R_x^3     (same for y),
    with hard-edge solenoid (k = (B / 2 Brho)^2 in both planes) and quadrupoles (k = +-G / Brho).
    Fixed-step RK4 on a 1 mm grid, aligned with the element edges of InjectionLine.
    Peak slice of a bunched beam: K(z) = K0 * (B_f(z) - eta(z)) when the electrons compensate only
    the RF-averaged charge (default), or K0 * B_f(z) * (1 - eta(z)) as a per-slice upper bound
    (B_f = 1 for DC, where both agree).

Transmission estimate (KV beam, approximate):
    pipe       : fraction of the uniform beam ellipse inside the pipe radius, minimum along z;
    inflector  : fraction inside the inflector aperture at the entrance, times
                 min(1, theta_max / theta) per plane, theta = sqrt(R'^2 + (eps / R)^2).
    This is a geometric estimate, not particle tracking; halo and nonlinear forces are ignored.

Optics are matched per scenario (solenoid field and both quadrupole gradients within bounds), so
that compensation scenarios are compared at their own best tune.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Callable

import numpy as np
from scipy.optimize import differential_evolution

from plasma_column.beam import ProtonBeam
from plasma_column.constants import MP, QE
from plasma_column.injection_line import InjectionLine

_RNG = np.random.default_rng(12345)
_UNIT_DISK = None


def _unit_disk(n: int = 20000) -> np.ndarray:
    global _UNIT_DISK
    if _UNIT_DISK is None:
        r = np.sqrt(_RNG.random(n))
        a = 2.0 * math.pi * _RNG.random(n)
        _UNIT_DISK = np.stack([r * np.cos(a), r * np.sin(a)])
    return _UNIT_DISK


def ellipse_fraction_inside_circle(rx: float, ry: float, radius: float) -> float:
    """Fraction of a uniformly filled ellipse (semi-axes rx, ry) inside a centred circle."""
    if rx <= radius and ry <= radius:
        return 1.0
    u, v = _unit_disk()
    return float(np.mean((rx * u) ** 2 + (ry * v) ** 2 <= radius**2))


@dataclass(frozen=True)
class Optics:
    solenoid_B_T: float
    q1_gradient_Tm: float
    q2_gradient_Tm: float


@dataclass(frozen=True)
class TransportBeam:
    """Beam at the buncher exit (edge quantities of a KV beam)."""

    energy_keV: float = 30.0
    current_mA: float = 10.0
    r0_m: float = 0.002
    rp0_rad: float = 0.0
    emittance_n_edge_m_rad: float = 1.0e-6

    @property
    def proton(self) -> ProtonBeam:
        return ProtonBeam(energy_keV=self.energy_keV, current_mA=self.current_mA, radius_m=self.r0_m)

    @property
    def rigidity_Tm(self) -> float:
        b = self.proton
        return b.gamma * MP * b.velocity / QE

    @property
    def emittance_geom_m_rad(self) -> float:
        b = self.proton
        return self.emittance_n_edge_m_rad / (b.beta * b.gamma)


def element_strengths(line: InjectionLine, optics: Optics, rigidity_Tm: float, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Focusing functions k_x(z), k_y(z) [1/m^2] on the grid z."""
    kx = np.zeros_like(z)
    ky = np.zeros_like(z)
    edges = np.cumsum([0.0, line.plasma_cell_length, line.drift1_length, line.solenoid_length, line.drift2_length,
                       line.q1_length, line.drift3_length, line.q2_length, line.drift4_length])
    sol = (edges[2] <= z) & (z < edges[3])
    q1 = (edges[4] <= z) & (z < edges[5])
    q2 = (edges[6] <= z) & (z < edges[7])
    ks = (optics.solenoid_B_T / (2.0 * rigidity_Tm)) ** 2
    kx[sol] = ky[sol] = ks
    kx[q1], ky[q1] = optics.q1_gradient_Tm / rigidity_Tm, -optics.q1_gradient_Tm / rigidity_Tm
    kx[q2], ky[q2] = optics.q2_gradient_Tm / rigidity_Tm, -optics.q2_gradient_Tm / rigidity_Tm
    return kx, ky


def envelope(
    beam: TransportBeam,
    line: InjectionLine,
    optics: Optics,
    perveance_of_z: Callable[[np.ndarray], np.ndarray],
    dz_m: float = 1.0e-3,
) -> dict[str, np.ndarray]:
    """Edge envelope R_x, R_y and slopes from z = 0 to the inflector entrance (fixed-step RK4)."""
    n = int(round(line.total_length / dz_m))
    z = np.linspace(0.0, n * dz_m, n + 1)
    zh = z[:-1] + 0.5 * dz_m
    kx, ky = element_strengths(line, optics, beam.rigidity_Tm, z[:-1])
    K = np.asarray(perveance_of_z(zh), float)
    eps2 = beam.emittance_geom_m_rad**2

    def rhs(s: np.ndarray, kxi: float, kyi: float, Ki: float) -> np.ndarray:
        rx, rxp, ry, ryp = s
        rx, ry = max(rx, 1e-7), max(ry, 1e-7)
        sc = 2.0 * Ki / (rx + ry)
        return np.array([rxp, -kxi * rx + sc + eps2 / rx**3, ryp, -kyi * ry + sc + eps2 / ry**3])

    out = np.empty((n + 1, 4))
    s = np.array([beam.r0_m, beam.rp0_rad, beam.r0_m, beam.rp0_rad], float)
    out[0] = s
    for i in range(n):
        # Element strengths are piecewise constant on each step (edges lie on the 1 mm grid).
        a, b, c = kx[i], ky[i], K[i]
        k1 = rhs(s, a, b, c)
        k2 = rhs(s + 0.5 * dz_m * k1, a, b, c)
        k3 = rhs(s + 0.5 * dz_m * k2, a, b, c)
        k4 = rhs(s + dz_m * k3, a, b, c)
        s = s + dz_m / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
        out[i + 1] = s
    return {"z_m": z, "Rx_m": out[:, 0], "Rxp_rad": out[:, 1], "Ry_m": out[:, 2], "Ryp_rad": out[:, 3]}


def transmission(
    env: dict[str, np.ndarray],
    beam: TransportBeam,
    pipe_radius_m: float = 0.010,
    inflector_aperture_m: float = 0.005,
    inflector_max_divergence_rad: float = 0.050,
) -> dict[str, float]:
    """Geometric KV transmission estimate (pipe clipping, inflector aperture and divergence)."""
    rx, ry = env["Rx_m"], env["Ry_m"]
    over = np.flatnonzero((rx > pipe_radius_m) | (ry > pipe_radius_m))
    t_pipe = 1.0 if over.size == 0 else min(ellipse_fraction_inside_circle(rx[i], ry[i], pipe_radius_m)
                                            for i in over[:: max(1, over.size // 50)])
    rxe, rye = rx[-1], ry[-1]
    eps = beam.emittance_geom_m_rad
    th_x = math.hypot(env["Rxp_rad"][-1], eps / rxe)
    th_y = math.hypot(env["Ryp_rad"][-1], eps / rye)
    t_ap = ellipse_fraction_inside_circle(rxe, rye, inflector_aperture_m)
    t_div = min(1.0, inflector_max_divergence_rad / th_x) * min(1.0, inflector_max_divergence_rad / th_y)
    return {
        "max_R_mm": float(max(rx.max(), ry.max()) * 1e3),
        "Rx_inflector_mm": float(rxe * 1e3),
        "Ry_inflector_mm": float(rye * 1e3),
        "theta_x_inflector_mrad": th_x * 1e3,
        "theta_y_inflector_mrad": th_y * 1e3,
        "T_pipe": t_pipe,
        "T_inflector_aperture": t_ap,
        "T_inflector_divergence": t_div,
        "T_total": t_pipe * t_ap * t_div,
    }


def match_optics(
    beam: TransportBeam,
    line: InjectionLine,
    perveance_of_z: Callable[[np.ndarray], np.ndarray],
    bounds: tuple[tuple[float, float], ...] = ((0.0, 0.6), (-1.5, 1.5), (-1.5, 1.5)),
    seeds: tuple[int, ...] = (1, 2),
    maxiter: int = 60,
    popsize: int = 25,
    starts: tuple[Optics, ...] = (),
    **trans_kw: float,
) -> tuple[Optics, dict[str, float]]:
    """
    Solenoid field [T] and Q1/Q2 gradients [T/m] that maximize the transmission estimate; ties are
    broken toward a small, round spot at the inflector entrance.

    Differential evolution from several seeds; ``starts`` (e.g. the optima of neighbouring
    scenarios) seed the population and are evaluated too, so the result is never worse than a
    known tune.
    """

    def cost(x: np.ndarray) -> float:
        o = Optics(*x)
        env = envelope(beam, line, o, perveance_of_z, dz_m=2.0e-3)
        t = transmission(env, beam, **trans_kw)
        spot = 0.5 * (t["Rx_inflector_mm"] + t["Ry_inflector_mm"]) / 5.0
        return -t["T_total"] + 0.02 * spot + 0.01 * abs(t["Rx_inflector_mm"] - t["Ry_inflector_mm"]) / 5.0

    lo, hi = [b[0] for b in bounds], [b[1] for b in bounds]
    candidates = []
    for seed in seeds:
        x0 = None
        if starts:
            x0 = np.clip([starts[0].solenoid_B_T, starts[0].q1_gradient_Tm, starts[0].q2_gradient_Tm], lo, hi)
        res = differential_evolution(cost, bounds, seed=seed, maxiter=maxiter, popsize=popsize, tol=1e-7,
                                     polish=True, x0=x0)
        candidates.append((res.fun, Optics(*res.x)))
    for o in starts:
        candidates.append((cost(np.array([o.solenoid_B_T, o.q1_gradient_Tm, o.q2_gradient_Tm])), o))
    o = min(candidates, key=lambda c: c[0])[1]
    return o, transmission(envelope(beam, line, o, perveance_of_z), beam, **trans_kw)


def perveance_profile(
    K0: float,
    line: InjectionLine,
    eta_cell: float = 0.0,
    eta_downstream: float = 0.0,
    bunching_z_m: np.ndarray | None = None,
    bunching_factor: np.ndarray | None = None,
    compensation: str = "average",
) -> Callable[[np.ndarray], np.ndarray]:
    """
    Peak-slice perveance K(z); eta = eta_cell inside the cell, eta_downstream after it.

    compensation:
        "average"   : electrons cancel only the RF-averaged charge (tau_ion >> T_RF),
                      K = K0 * max(B_f - eta, 0), i.e. K_peak/K0,peak = 1 - eta_avg / B_f.
        "per_slice" : every bunch slice is compensated by the same fraction,
                      K = K0 * B_f * (1 - eta). Upper bound on the benefit; not reachable when
                      the electrons cannot follow the RF bunch structure.
    The two are identical for a DC beam (B_f = 1).
    """
    if compensation not in ("average", "per_slice"):
        raise ValueError(f"unknown compensation mode {compensation!r}")
    L = line.plasma_cell_length

    def K(z: np.ndarray) -> np.ndarray:
        z = np.asarray(z, float)
        eta = np.where(z <= L, eta_cell, eta_downstream)
        bf = 1.0 if bunching_factor is None else np.interp(z, bunching_z_m, bunching_factor)
        if compensation == "average":
            return K0 * np.clip(bf - eta, 0.0, None)
        return K0 * bf * np.clip(1.0 - eta, 0.0, None)

    return K


def line_with_optics(line: InjectionLine, optics: Optics) -> InjectionLine:
    return replace(line, solenoid_field_T=optics.solenoid_B_T, q1_gradient_Tm=optics.q1_gradient_Tm,
                   q2_gradient_Tm=optics.q2_gradient_Tm)
