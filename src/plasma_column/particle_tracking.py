"""
src/plasma_column/particle_tracking.py

Transverse particle tracking of a DC beam from the plasma cell to the spiral inflector (task CW5 of
docs/physics_notes/simulation_strategy_tasks.md), to replace the KV transmission estimate of
plasma_column.transport by counting particles (halo, non-KV distributions, PIC beams).

Model, deliberately the same lattice as the envelope model so the two can be compared:
  - hard-edge elements of plasma_column.injection_line.InjectionLine; solenoid as round linear
    focusing k = (B / 2 B rho)^2 in the Larmor frame (rotation dropped, as in the envelope model),
    quadrupoles k_x = -k_y = G / B rho;
  - space charge from the actual transverse distribution: 2D open-boundary field on a grid
    (cloud-in-cell deposit, FFT convolution with the line-charge kernel (x, y) / r^2), scaled by the
    local perveance K(z) = K0 (1 - eta(z)) and by the surviving current fraction:
        x'' = -k_x x + K sum_j w_j (x - x_j) / |r - r_j|^2   (w_j = 1 / N per initial particle)
    which reduces to x'' = K x / a^2 inside a uniform round beam of radius a (the KV equation);
  - leapfrog in z (kick-drift-kick), dz = 1 mm aligned with the element edges;
  - loss at r >= pipe radius (10 mm) anywhere; accepted at the inflector if r < 5 mm and
    |x'|, |y'| < 50 mrad (the envelope model's aperture and divergence limits).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from plasma_column.injection_line import InjectionLine
from plasma_column.transport import Optics


def element_edges(line: InjectionLine) -> np.ndarray:
    return np.cumsum([0.0, line.plasma_cell_length, line.drift1_length, line.solenoid_length, line.drift2_length,
                      line.q1_length, line.drift3_length, line.q2_length, line.drift4_length])


def focusing(line: InjectionLine, optics: Optics, rigidity_Tm: float, z_m: float) -> tuple[float, float]:
    e = element_edges(line)
    if e[2] <= z_m < e[3]:
        k = (optics.solenoid_B_T / (2.0 * rigidity_Tm)) ** 2
        return k, k
    if e[4] <= z_m < e[5]:
        g = optics.q1_gradient_Tm / rigidity_Tm
        return g, -g
    if e[6] <= z_m < e[7]:
        g = optics.q2_gradient_Tm / rigidity_Tm
        return g, -g
    return 0.0, 0.0


@dataclass
class SpaceChargeGrid:
    """Open-boundary 2D field of a line-charge distribution on an n x n grid of half-width L."""

    half_width_m: float = 0.012
    n: int = 64

    def __post_init__(self) -> None:
        self.h = 2.0 * self.half_width_m / self.n
        m = 2 * self.n
        idx = np.arange(m)
        d = np.where(idx < self.n, idx, idx - m) * self.h
        X, Y = np.meshgrid(d, d, indexing="ij")
        r2 = X**2 + Y**2
        r2[0, 0] = 1.0
        kx, ky = X / r2, Y / r2
        kx[0, 0] = ky[0, 0] = 0.0
        self._fkx, self._fky = np.fft.rfft2(kx), np.fft.rfft2(ky)

    def field(self, x: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """sum_j w_j (r - r_j) / |r - r_j|^2 at the particle positions (cloud-in-cell)."""
        n, h, L = self.n, self.h, self.half_width_m
        gx, gy = (x + L) / h - 0.5, (y + L) / h - 0.5
        i0, j0 = np.floor(gx).astype(int), np.floor(gy).astype(int)
        fx, fy = gx - i0, gy - j0
        rho = np.zeros((2 * n, 2 * n))
        ok = (i0 >= 0) & (i0 < n - 1) & (j0 >= 0) & (j0 < n - 1)
        for di, dj, ww in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(rho, (i0[ok] + di, j0[ok] + dj), (w * ww)[ok])
        fr = np.fft.rfft2(rho)
        ex = np.fft.irfft2(fr * self._fkx, s=rho.shape)[:n, :n]
        ey = np.fft.irfft2(fr * self._fky, s=rho.shape)[:n, :n]
        out_x, out_y = np.zeros_like(x), np.zeros_like(y)
        for di, dj, ww in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            out_x[ok] += ww[ok] * ex[i0[ok] + di, j0[ok] + dj]
            out_y[ok] += ww[ok] * ey[i0[ok] + di, j0[ok] + dj]
        return out_x, out_y


def track(x: np.ndarray, xp: np.ndarray, y: np.ndarray, yp: np.ndarray, line: InjectionLine, optics: Optics,
          rigidity_Tm: float, K0: float, eta_cell: float, eta_down: float, z_start_m: float = 0.0,
          dz_m: float = 1.0e-3, pipe_radius_m: float = 0.010, aperture_m: float = 0.005,
          max_divergence_rad: float = 0.050, space_charge: bool = True,
          grid: SpaceChargeGrid | None = None, record_every: int = 10) -> dict[str, np.ndarray | float]:
    """Track particles from z_start to the inflector entrance; returns transmission and rms history."""
    x, xp, y, yp = (np.array(a, float) for a in (x, xp, y, yp))
    n0 = x.size
    w = np.full(n0, 1.0 / n0)
    alive = np.hypot(x, y) < pipe_radius_m
    grid = grid or SpaceChargeGrid(half_width_m=1.2 * pipe_radius_m)
    L = line.total_length
    nsteps = int(round((L - z_start_m) / dz_m))
    hist = {"z_m": [], "x_rms_mm": [], "y_rms_mm": [], "surviving": []}

    def accel(z: float) -> tuple[np.ndarray, np.ndarray]:
        kx, ky = focusing(line, optics, rigidity_Tm, z)
        ax, ay = -kx * x, -ky * y
        K = K0 * (1.0 - (eta_cell if z < line.plasma_cell_length else eta_down))
        if space_charge and K != 0.0 and alive.any():
            fx, fy = grid.field(x[alive], y[alive], w[alive])
            ax[alive] += K * fx
            ay[alive] += K * fy
        return ax, ay

    z = z_start_m
    for s in range(nsteps):
        zm = z + 0.5 * dz_m
        ax, ay = accel(zm)  # fields piecewise constant over the step (edges on the grid)
        xp += 0.5 * dz_m * ax; yp += 0.5 * dz_m * ay
        x += dz_m * xp; y += dz_m * yp
        ax, ay = accel(zm)
        xp += 0.5 * dz_m * ax; yp += 0.5 * dz_m * ay
        z += dz_m
        alive &= np.hypot(x, y) < pipe_radius_m
        if s % record_every == 0 or s == nsteps - 1:
            a = alive
            hist["z_m"].append(z); hist["surviving"].append(a.mean())
            hist["x_rms_mm"].append(float(np.std(x[a]) * 1e3) if a.any() else np.nan)
            hist["y_rms_mm"].append(float(np.std(y[a]) * 1e3) if a.any() else np.nan)
    pipe_ok = alive
    in_ap = pipe_ok & (np.hypot(x, y) < aperture_m)
    accepted = in_ap & (np.abs(xp) < max_divergence_rad) & (np.abs(yp) < max_divergence_rad)
    return {"T_pipe": float(pipe_ok.mean()), "T_aperture": float(in_ap.mean()), "T_total": float(accepted.mean()),
            **{k: np.array(v) for k, v in hist.items()},
            "x": x, "xp": xp, "y": y, "yp": yp, "accepted": accepted}


def kv_beam(n: int, radius_m: float, emittance_geom_edge_m_rad: float, seed: int = 1) -> tuple[np.ndarray, ...]:
    """Round KV beam (uniform on the 4D ellipsoid surface), upright, edge radius a, edge emittance eps."""
    rng = np.random.default_rng(seed)
    u = rng.normal(size=(n, 4))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    a, ap = radius_m, emittance_geom_edge_m_rad / radius_m
    return u[:, 0] * a, u[:, 1] * ap, u[:, 2] * a, u[:, 3] * ap


def gaussian_beam(n: int, radius_m: float, emittance_geom_edge_m_rad: float, seed: int = 1) -> tuple[np.ndarray, ...]:
    """Round upright Gaussian beam with the rms of the KV beam (edge = 2 rms in each plane)."""
    rng = np.random.default_rng(seed)
    s, sp = radius_m / 2.0, emittance_geom_edge_m_rad / radius_m / 2.0
    return rng.normal(0, s, n), rng.normal(0, sp, n), rng.normal(0, s, n), rng.normal(0, sp, n)


def rms_emittance_m_rad(u: np.ndarray, up: np.ndarray) -> float:
    du, dup = u - u.mean(), up - up.mean()
    return float(math.sqrt(max(0.0, np.mean(du**2) * np.mean(dup**2) - np.mean(du * dup) ** 2)))
