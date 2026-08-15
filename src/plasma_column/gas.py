"""
src/plasma_column/gas.py

Gas properties, neutral gas density calculation, and cross-section data table loading/interpolation
for H2 and Kr neutralizer gases.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

from plasma_column.constants import KB, TORR_TO_PA, MH2, MKR, MP


@dataclass
class NeutralGas:
    species: str = "H2"
    pressure_torr: float = 1.0e-5
    temperature_K: float = 300.0

    @property
    def pressure_pa(self) -> float:
        return self.pressure_torr * TORR_TO_PA

    @property
    def number_density(self) -> float:
        """Neutral gas number density n_gas [m^-3] assuming ideal gas law."""
        if self.pressure_torr <= 0:
            return 0.0
        return self.pressure_pa / (KB * self.temperature_K)

    @property
    def mass(self) -> float:
        species_upper = self.species.upper()
        if species_upper in ("H2", "HYDROGEN"):
            return MH2
        elif species_upper in ("KR", "KRYPTON"):
            return MKR
        else:
            raise ValueError(f"Unknown gas species: {self.species}")


def gas_density_m3(pressure_torr: float, temperature_K: float = 300.0) -> float:
    """
    Computes ideal gas number density n_gas [m^-3] from pressure in Torr and temperature in K.
    Formula: n_gas = p_pa / (k_B * T)
    """
    if pressure_torr <= 0:
        return 0.0
    pressure_pa = pressure_torr * TORR_TO_PA
    return pressure_pa / (KB * temperature_K)


def ionization_tau_s(n_gas_m3: float, sigma_m2: float, beam_speed_m_s: float) -> float:
    """
    Computes characteristic ionization buildup time tau [s]:
    Formula: tau = 1 / (n_gas * sigma * v_beam)
    """
    if n_gas_m3 <= 0 or sigma_m2 <= 0 or beam_speed_m_s <= 0:
        return float("inf")
    return 1.0 / (n_gas_m3 * sigma_m2 * beam_speed_m_s)


def lab_to_cm_energy(e_lab_eV: float, m_projectile: float = MP, m_target: float = MH2) -> float:
    """Converts laboratory kinetic energy [eV] to center-of-mass energy [eV]."""
    return e_lab_eV * (m_target / (m_projectile + m_target))


def cm_to_lab_energy(e_cm_eV: float, m_projectile: float = MP, m_target: float = MH2) -> float:
    """Converts center-of-mass energy [eV] to laboratory kinetic energy [eV]."""
    return e_cm_eV * ((m_projectile + m_target) / m_target)


def load_cross_section_table(filepath: str | Path) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    """
    Loads two-column cross-section file (energy [eV], cross_section [m^2]).
    Ignores comment lines starting with '#' and header lines.
    Returns (energies, cross_sections, metadata_comments).
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Cross-section data file not found: {path}")

    metadata = {}
    energies = []
    sigmas = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith("#"):
                if ":" in line_str:
                    parts = line_str.strip("# ").split(":", 1)
                    metadata[parts[0].strip()] = parts[1].strip()
                continue

            tokens = line_str.split()
            if len(tokens) >= 2:
                try:
                    e_val = float(tokens[0])
                    s_val = float(tokens[1])
                    energies.append(e_val)
                    sigmas.append(s_val)
                except ValueError:
                    continue

    if not energies:
        raise ValueError(f"No valid numerical cross-section data found in {path}")

    energies_arr = np.array(energies, dtype=float)
    sigmas_arr = np.array(sigmas, dtype=float)

    # Ensure sorted by energy
    sort_idx = np.argsort(energies_arr)
    return energies_arr[sort_idx], sigmas_arr[sort_idx], metadata


def interpolate_cross_section(
    energies: np.ndarray, sigmas: np.ndarray, target_energy_eV: float
) -> float:
    """
    Interpolates cross section [m^2] at target_energy_eV.
    Uses linear interpolation within bounds, returning 0.0 outside bounds.
    """
    if len(energies) == 0:
        return 0.0
    if target_energy_eV < energies[0] or target_energy_eV > energies[-1]:
        return float(np.interp(target_energy_eV, energies, sigmas, left=0.0, right=0.0))
    return float(np.interp(target_energy_eV, energies, sigmas))


class CrossSectionDatabase:
    """
    Database manager for proton-impact and electron-impact cross sections for H2 and Kr.
    """

    def __init__(self, base_dir: Optional[str | Path] = None):
        if base_dir is None:
            project_dir = Path(__file__).resolve().parent.parent.parent
            base_dir = project_dir / "warpx_proton_impact_cross_sections_linear" / "MCC_cross_sections"
        self.base_dir = Path(base_dir)

    def get_proton_impact_cross_section(self, species: str, e_lab_eV: float = 30000.0) -> float:
        species_upper = species.upper()
        if species_upper in ("H2", "HYDROGEN"):
            file_path = self.base_dir / "H2" / "proton_impact_ionization.dat"
            m_target = MH2
        elif species_upper in ("KR", "KRYPTON"):
            file_path = self.base_dir / "Kr" / "proton_impact_ionization.dat"
            m_target = MKR
        else:
            raise ValueError(f"Unsupported species: {species}")

        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing cross-section data file for species '{species}': {file_path}"
            )

        energies_cm, sigmas, meta = load_cross_section_table(file_path)
        e_cm = lab_to_cm_energy(e_lab_eV, m_projectile=MP, m_target=m_target)
        return interpolate_cross_section(energies_cm, sigmas, e_cm)


def get_h2_cross_section(e_lab_keV: float = 30.0) -> float:
    """Returns proton-impact ionization cross section [m^2] for H2 at e_lab_keV."""
    db = CrossSectionDatabase()
    return db.get_proton_impact_cross_section("H2", e_lab_keV * 1000.0)


def get_kr_cross_section(e_lab_keV: float = 30.0) -> float:
    """Returns proton-impact ionization cross section [m^2] for Kr at e_lab_keV."""
    db = CrossSectionDatabase()
    return db.get_proton_impact_cross_section("Kr", e_lab_keV * 1000.0)

