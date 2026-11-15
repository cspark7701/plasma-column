"""
src/plasma_column/suppressor.py

Electron suppressor before the spiral inflector (task CW4 of
docs/physics_notes/simulation_strategy_tasks.md): axisymmetric (r, z) electrostatic model of the
end of the compensated line.

Geometry (z in m, suppressor centre at z = 0):
  - grounded beam pipe of radius R (10 mm) for z < z_inflector;
  - suppressor ring electrode at -V_s: r >= aperture, |z| <= length / 2 (a disc with a hole, inside
    the pipe);
  - the inflector region from z_inflector on, modeled as the pipe wall at potential +V_inf
    (leakage field of the inflector electrodes that pulls electrons downstream; V_inf = 0 for a
    grounded entrance);
  - both ends (z_min, z_max): Neumann (the beam continues through them).
Space charge: the 10 mA beam (uniform, radius a) with net compensation eta_down for z < z_comp_end
(the compensated line upstream of the suppressor) and 0 downstream of it, i.e. the suppressor is
where the electron population ends.

Electrons upstream sit in the compensated beam at the on-axis potential phi_up; they are held if
the on-axis potential between them and the inflector has a minimum below phi_up by more than
their energy: barrier = phi_up - min_z phi(0, z) over the suppressor and downstream.

Solved by finite differences (5-point, cylindrical, scipy sparse direct solve).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

from plasma_column.constants import EPSILON_0


@dataclass(frozen=True)
class SuppressorConfig:
    suppressor_voltage_V: float = 1000.0  # magnitude; the electrode is at -V_s
    aperture_m: float = 0.005
    length_m: float = 0.005
    pipe_radius_m: float = 0.010
    inflector_voltage_V: float = 0.0
    z_inflector_m: float = 0.030
    z_min_m: float = -0.060
    z_max_m: float = 0.050
    beam_current_A: float = 0.010
    beam_speed_m_s: float = 2.397e6
    beam_radius_m: float = 0.002
    eta_down: float = 0.7
    z_comp_end_m: float = -0.005  # compensation stops at the upstream face of the suppressor
    dr_m: float = 2.5e-4
    dz_m: float = 2.5e-4


def solve(cfg: SuppressorConfig) -> dict[str, np.ndarray]:
    """Potential phi(r, z) [V] on the grid; returns r, z, phi and the on-axis profile."""
    nr = int(round(cfg.pipe_radius_m / cfg.dr_m)) + 1
    nz = int(round((cfg.z_max_m - cfg.z_min_m) / cfg.dz_m)) + 1
    r = np.linspace(0.0, cfg.pipe_radius_m, nr)
    z = np.linspace(cfg.z_min_m, cfg.z_max_m, nz)
    dr, dz = r[1] - r[0], z[1] - z[0]
    R, Z = np.meshgrid(r, z, indexing="ij")

    # Fixed-potential nodes.
    fixed = np.zeros((nr, nz), bool)
    val = np.zeros((nr, nz))
    wall = np.isclose(R, cfg.pipe_radius_m)
    fixed |= wall
    val[wall & (Z >= cfg.z_inflector_m)] = cfg.inflector_voltage_V
    sup = (R >= cfg.aperture_m - 1e-12) & (np.abs(Z) <= 0.5 * cfg.length_m + 1e-12)
    fixed |= sup
    val[sup] = -cfg.suppressor_voltage_V

    # Beam charge density with compensation upstream of the suppressor.
    lam = cfg.beam_current_A / cfg.beam_speed_m_s
    rho_b = lam / (math.pi * cfg.beam_radius_m**2)
    # Fraction of each radial cell (annulus [r - dr/2, r + dr/2], axis cell [0, dr/2]) inside the beam,
    # so that the deposited line charge equals lambda on any grid.
    lo, hi = np.clip(r - 0.5 * dr, 0.0, None), r + 0.5 * dr
    frac = np.clip((np.minimum(hi, cfg.beam_radius_m) ** 2 - np.minimum(lo, cfg.beam_radius_m) ** 2)
                   / (hi**2 - lo**2), 0.0, 1.0)
    rho = (rho_b * frac)[:, None] * np.where(Z < cfg.z_comp_end_m, 1.0 - cfg.eta_down, 1.0)

    N = nr * nz
    idx = np.arange(N).reshape(nr, nz)
    A = lil_matrix((N, N))
    b = np.zeros(N)
    for i in range(nr):
        for j in range(nz):
            k = idx[i, j]
            if fixed[i, j]:
                A[k, k] = 1.0
                b[k] = val[i, j]
                continue
            # z-direction (Neumann at both ends by mirroring).
            jm = j - 1 if j > 0 else j + 1
            jp = j + 1 if j < nz - 1 else j - 1
            A[k, idx[i, jm]] += 1.0 / dz**2
            A[k, idx[i, jp]] += 1.0 / dz**2
            diag = -2.0 / dz**2
            if i == 0:  # axis: Laplacian_r = 4 (phi_1 - phi_0) / dr^2
                A[k, idx[1, j]] += 4.0 / dr**2
                diag += -4.0 / dr**2
            else:
                rp, rm = r[i] + 0.5 * dr, r[i] - 0.5 * dr
                A[k, idx[i + 1, j]] += rp / (r[i] * dr**2)
                A[k, idx[i - 1, j]] += rm / (r[i] * dr**2)
                diag += -(rp + rm) / (r[i] * dr**2)
            A[k, k] += diag
            b[k] = -rho[i, j] / EPSILON_0
    phi = spsolve(A.tocsr(), b).reshape(nr, nz)
    return {"r_m": r, "z_m": z, "phi_V": phi, "phi_axis_V": phi[0]}


def barrier_V(sol: dict[str, np.ndarray], cfg: SuppressorConfig) -> dict[str, float]:
    """On-axis potential in the compensated beam upstream, its minimum downstream, and the barrier."""
    z, pa = sol["z_m"], sol["phi_axis_V"]
    up = pa[z <= cfg.z_min_m + 0.01].mean()
    down = z >= cfg.z_comp_end_m
    return {"phi_upstream_V": float(up), "phi_min_V": float(pa[down].min()),
            "z_phi_min_m": float(z[down][np.argmin(pa[down])]), "barrier_V": float(up - pa[down].min())}


def lens_focal_length_m(sol: dict[str, np.ndarray], reference: dict[str, np.ndarray], beam_energy_eV: float) -> float:
    """
    Focal length of the suppressor electrode for the beam (positive = focusing), from the paraxial
    ray equation in the on-axis potential difference to a reference solution without suppressor
    voltage (removes the beam's own space charge):
        r'' + U' r' / (2 U) + U'' r / (4 U) = 0,  U = V0 - phi (proton kinetic energy / e),
    i.e. r'' = phi' r' / (2 U) + phi'' r / (4 U); parallel ray in, f = -r / r' after the lens.
    """
    z = sol["z_m"]
    phi = sol["phi_axis_V"] - reference["phi_axis_V"]
    d1, d2 = np.gradient(phi, z), np.gradient(np.gradient(phi, z), z)
    r, rp = 1.0e-3, 0.0
    for k in range(len(z) - 1):
        h = z[k + 1] - z[k]
        V = beam_energy_eV - 0.5 * (phi[k] + phi[k + 1])
        a = (0.5 * (d1[k] + d1[k + 1])) * rp / (2 * V) + (0.5 * (d2[k] + d2[k + 1])) * r / (4 * V)
        rp += a * h
        r += rp * h
    return float(-r / rp) if rp != 0 else math.inf
