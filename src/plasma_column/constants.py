"""
src/plasma_column/constants.py

Fundamental physical constants and conversion factors used throughout the plasma column project.
All values are in SI units unless explicitly noted.
"""

import math

# Fundamental physical constants (CODATA 2018 / standard physics values)
C: float = 299792458.0                # Speed of light [m/s]
SPEED_OF_LIGHT: float = C             # Alias for speed of light
QE: float = 1.602176634e-19           # Elementary charge [C]
ELEMENTARY_CHARGE: float = QE         # Alias for QE
ME: float = 9.1093837015e-31          # Electron mass [kg]
MP: float = 1.67262192369e-27         # Proton mass [kg]
AMU: float = 1.66053906660e-27        # Atomic mass unit [kg]
KB: float = 1.380649e-23              # Boltzmann constant [J/K]
EPSILON_0: float = 8.8541878128e-12   # Vacuum permittivity [F/m]
MU_0: float = 4.0 * math.pi * 1.0e-7  # Vacuum permeability [H/m]

# Mass of neutral species [kg]
MH2: float = 2.01588 * AMU             # H2 molecular mass [kg]
MKR: float = 83.798 * AMU              # Kr atomic mass [kg]

# Unit conversions
TORR_TO_PA: float = 133.3223684       # 1 Torr in Pa
EV_TO_JOULE: float = QE               # 1 eV in Joules
EV_TO_KELVIN: float = QE / KB         # 1 eV in Kelvin

# Radiation length mass density for neutral gases [kg/m^2] (PDG: 1 g/cm^2 = 10 kg/m^2)
RADIATION_LENGTH_H2: float = 630.5     # H2 radiation length [kg/m^2] (63.05 g/cm^2)
RADIATION_LENGTH_KR: float = 353.4     # Kr radiation length [kg/m^2] (35.34 g/cm^2)


def estimate_cfl_timestep(dx: float, dy: float, dz: float, cfl: float = 0.5) -> float:
    """
    Computes the 3D FDTD Courant-Friedrichs-Lewy (CFL) stable electromagnetic timestep [s].

    Formula:
        dt = cfl / (c * sqrt(dx^-2 + dy^-2 + dz^-2))

    Args:
        dx: Grid spacing in x [m]
        dy: Grid spacing in y [m]
        dz: Grid spacing in z [m]
        cfl: Courant factor (typically 0.5 to 0.7 for Yee FDTD, default 0.5)

    Returns:
        float: Estimated maximum stable timestep [s]
    """
    return float(cfl / (C * math.sqrt(dx**-2 + dy**-2 + dz**-2)))
