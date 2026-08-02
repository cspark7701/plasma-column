"""
src/plasma_column/schema.py

Strongly-typed dataclass schemas and validation rules for plasma column simulation cases.
Guarantees physical bound checks and schema consistency across YAML files and metadata.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional
import yaml


@dataclass
class BeamConfig:
    species: str = "proton"
    energy_keV: float = 30.0
    current_mA: float = 10.0
    radius_m: float = 0.002
    rms_divergence: float = 0.0


@dataclass
class PlasmaConfig:
    gas: str = "H2"
    pressure_torr: float = 1.0e-5
    column_zmin_m: float = 0.0
    column_length_m: float = 0.20
    plasma_radius_m: float = 0.003
    neutralization: float = -1.0
    steady_state_neutralization: float = 0.90
    plasma_age_s: float = 2.0e-4
    electron_temperature_eV: float = 1.0


@dataclass
class SolenoidConfig:
    Bz_T: float = 0.15


@dataclass
class NumericsConfig:
    nx: int = 32
    ny: int = 32
    nz: int = 256
    xmax_m: float = 0.01
    ymax_m: float = 0.01
    zmin_m: float = -0.02
    zmax_m: float = 0.24
    max_steps: int = 2000
    cfl: float = 0.7
    nppc_beam: int = 4
    nppc_plasma: int = 4
    mcc: str = "electron_impact"


@dataclass
class SimulationCaseConfig:
    case_name: str
    description: str = ""
    beam: BeamConfig = field(default_factory=BeamConfig)
    plasma: PlasmaConfig = field(default_factory=PlasmaConfig)
    solenoid: SolenoidConfig = field(default_factory=SolenoidConfig)
    numerics: NumericsConfig = field(default_factory=NumericsConfig)

    def validate(self) -> None:
        """Validates all physical bounds and grid dimensions."""
        if not self.case_name:
            raise ValueError("case_name cannot be empty")
        if self.beam.energy_keV <= 0:
            raise ValueError(f"Beam energy_keV must be positive, got {self.beam.energy_keV}")
        if self.beam.current_mA < 0:
            raise ValueError(f"Beam current_mA cannot be negative, got {self.beam.current_mA}")
        if self.plasma.pressure_torr < 0:
            raise ValueError(f"Pressure_torr cannot be negative, got {self.plasma.pressure_torr}")
        if self.plasma.gas not in ("H2", "Kr", "none", "None", "", None):
            raise ValueError(f"Gas must be H2, Kr, or none, got '{self.plasma.gas}'")
        if self.numerics.nx <= 0 or self.numerics.ny <= 0 or self.numerics.nz <= 0:
            raise ValueError(f"Grid dimensions must be positive integers, got ({self.numerics.nx}, {self.numerics.ny}, {self.numerics.nz})")
        if self.numerics.zmax_m <= self.numerics.zmin_m:
            raise ValueError(f"zmax_m ({self.numerics.zmax_m}) must be strictly greater than zmin_m ({self.numerics.zmin_m})")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationCaseConfig:
        """Parses dict into SimulationCaseConfig with dataclass nested models."""
        case_name = data.get("case_name", "unnamed_case")
        description = data.get("description", "")

        beam_data = data.get("beam", {})
        beam = BeamConfig(
            species=beam_data.get("species", "proton"),
            energy_keV=float(beam_data.get("energy_keV", 30.0)),
            current_mA=float(beam_data.get("current_mA", 10.0)),
            radius_m=float(beam_data.get("radius_m", 0.002)),
            rms_divergence=float(beam_data.get("rms_divergence", 0.0)),
        )

        plasma_data = data.get("plasma", {})
        plasma = PlasmaConfig(
            gas=plasma_data.get("gas", "H2"),
            pressure_torr=float(plasma_data.get("pressure_torr", 1.0e-5)),
            column_zmin_m=float(plasma_data.get("column_zmin_m", 0.0)),
            column_length_m=float(plasma_data.get("column_length_m", 0.20)),
            plasma_radius_m=float(plasma_data.get("plasma_radius_m", 0.003)),
            neutralization=float(plasma_data.get("neutralization", -1.0)),
            steady_state_neutralization=float(plasma_data.get("steady_state_neutralization", 0.90)),
            plasma_age_s=float(plasma_data.get("plasma_age_s", 2.0e-4)),
            electron_temperature_eV=float(plasma_data.get("electron_temperature_eV", 1.0)),
        )

        solenoid_data = data.get("solenoid", {})
        solenoid = SolenoidConfig(
            Bz_T=float(solenoid_data.get("Bz_T", 0.15)),
        )

        numerics_data = data.get("numerics", {})
        numerics = NumericsConfig(
            nx=int(numerics_data.get("nx", 32)),
            ny=int(numerics_data.get("ny", 32)),
            nz=int(numerics_data.get("nz", 256)),
            xmax_m=float(numerics_data.get("xmax_m", 0.01)),
            ymax_m=float(numerics_data.get("ymax_m", 0.01)),
            zmin_m=float(numerics_data.get("zmin_m", -0.02)),
            zmax_m=float(numerics_data.get("zmax_m", 0.24)),
            max_steps=int(numerics_data.get("max_steps", 2000)),
            cfl=float(numerics_data.get("cfl", 0.7)),
            nppc_beam=int(numerics_data.get("nppc_beam", 4)),
            nppc_plasma=int(numerics_data.get("nppc_plasma", 4)),
            mcc=numerics_data.get("mcc", "electron_impact"),
        )

        config = cls(
            case_name=case_name,
            description=description,
            beam=beam,
            plasma=plasma,
            solenoid=solenoid,
            numerics=numerics,
        )
        config.validate()
        return config

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> SimulationCaseConfig:
        """Loads and validates SimulationCaseConfig directly from YAML path."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Case YAML file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        """Converts dataclass back to dictionary representation."""
        return asdict(self)
