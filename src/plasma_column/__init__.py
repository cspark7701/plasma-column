"""
plasma_column package

Simulation, physics, diagnostics, and plotting workflow for plasma-assisted space-charge neutralization.
"""

__version__ = "1.0.0"

from .hardware import detect_gpu, configure_runtime
from .constants import estimate_cfl_timestep, SPEED_OF_LIGHT, C

__all__ = [
    "__version__",
    "detect_gpu",
    "configure_runtime",
    "estimate_cfl_timestep",
    "SPEED_OF_LIGHT",
    "C",
]
