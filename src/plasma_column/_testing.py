"""
src/plasma_column/_testing.py

Testing and illustration fixtures for synthetic spatial density distributions.
Separated from operational diagnostics to keep the public API clean and fast.
"""

from __future__ import annotations

import numpy as np


def generate_synthetic_3d_grid(
    nx: int = 31,
    ny: int = 31,
    nz: int = 50,
    x_max: float = 0.015,
    y_max: float = 0.015,
    z_min: float = 0.0,
    z_max: float = 0.30,
    n_proton_peak: float = 1.0e15,
    eta_target: float = 0.8,
    displaced_x: float = 0.0,
    overcompensated: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generates synthetic 3D spatial grids and species density arrays for testing local masks
    and creating illustrative figures when full 3D plotfile data is not present.
    """
    x = np.linspace(-x_max, x_max, nx)
    y = np.linspace(-y_max, y_max, ny)
    z = np.linspace(z_min, z_max, nz)

    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    R_beam = np.sqrt(X**2 + Y**2)
    R_elec = np.sqrt((X - displaced_x)**2 + Y**2)

    sigma_r = 0.002
    np_3d = n_proton_peak * np.exp(-(R_beam**2) / (2.0 * sigma_r**2))

    multiplier = 1.25 if overcompensated else eta_target
    ne_3d = multiplier * n_proton_peak * np.exp(-(R_elec**2) / (2.0 * sigma_r**2))
    ni_3d = 0.05 * ne_3d

    return ne_3d, ni_3d, np_3d, x, y, z
