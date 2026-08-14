"""
src/plasma_column/schema.py

Strongly-typed dataclass schemas and validation rules for plasma column simulation cases.
Guarantees physical bound checks and schema consistency across YAML files and metadata.json.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional
import yaml


# ── Canonical simulation-method registry ───────────────────────────────────────

ALLOWED_METHODS: frozenset[str] = frozenset({
    "vacuum",
    "seeded_compensation",
    "python_callback",
    "cxx_mcc_custom",
})

# Short-form aliases found in some case YAML files -> canonical name
METHOD_ALIASES: dict[str, str] = {
    "seeded":   "seeded_compensation",
    "callback": "python_callback",
}


def _normalise_method(raw: str) -> str:
    """Resolve alias and validate the simulation method string.

    Args:
        raw: Method string as read from a YAML file or user input.

    Returns:
        Canonical method string (one of ALLOWED_METHODS).

    Raises:
        ValueError: If the string is not recognised after alias resolution.
    """
    normalised = METHOD_ALIASES.get(raw, raw)
    if normalised not in ALLOWED_METHODS:
        raise ValueError(
            f"Unknown simulation method '{raw}'. "
            f"Allowed values: {sorted(ALLOWED_METHODS)}. "
            f"Recognised aliases: {METHOD_ALIASES}."
        )
    return normalised


def build_warpx_cmd_flags(method: str) -> list[str]:
    """Return the WarpX PICMI script CLI flags for the given simulation method.

    This is the single canonical source of truth for the method -> flag
    mapping.  Both scripts/run_case.py and scripts/run_scan.py must call this
    helper instead of duplicating the if/elif chain (see RT-02).

    Args:
        method: Canonical or alias method string.

    Returns:
        List of additional CLI argument strings ready for subprocess.run(),
        e.g. ["--neutralization", "-1"].  Empty list if no extra flags needed.
    """
    method = _normalise_method(method)
    if method == "seeded_compensation":
        return ["--neutralization", "-1"]
    elif method == "python_callback":
        return ["--neutralization", "-1", "--callback_source"]
    elif method == "cxx_mcc_custom":
        return ["--mcc", "electron_impact"]
    elif method == "vacuum":
        return ["--neutralization", "0.0"]
    return []  # pragma: no cover


# ── Sub-config dataclasses ─────────────────────────────────────────────────────

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


# ── Top-level case configuration ───────────────────────────────────────────────

@dataclass
class SimulationCaseConfig:
    case_name: str
    description: str = ""
    method: str = "vacuum"
    beam: BeamConfig = field(default_factory=BeamConfig)
    plasma: PlasmaConfig = field(default_factory=PlasmaConfig)
    solenoid: SolenoidConfig = field(default_factory=SolenoidConfig)
    numerics: NumericsConfig = field(default_factory=NumericsConfig)

    def validate(self) -> None:
        """Validates physical bounds, grid dimensions, and method consistency."""
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
            raise ValueError(
                f"Grid dimensions must be positive integers, "
                f"got ({self.numerics.nx}, {self.numerics.ny}, {self.numerics.nz})"
            )
        if self.numerics.zmax_m <= self.numerics.zmin_m:
            raise ValueError(
                f"zmax_m ({self.numerics.zmax_m}) must be strictly greater "
                f"than zmin_m ({self.numerics.zmin_m})"
            )

        # method must already be canonical at this point (from_dict resolves aliases)
        if self.method not in ALLOWED_METHODS:
            raise ValueError(
                f"method '{self.method}' is not in ALLOWED_METHODS "
                f"{sorted(ALLOWED_METHODS)}. "
                "Use SimulationCaseConfig.from_dict() to auto-resolve aliases."
            )

        # Cross-field consistency: vacuum method should not activate MCC
        if self.method == "vacuum" and self.numerics.mcc not in ("none", "None", "", None):
            warnings.warn(
                f"method='vacuum' but numerics.mcc='{self.numerics.mcc}'. "
                "MCC collisions have no effect in vacuum runs.",
                UserWarning,
                stacklevel=2,
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulationCaseConfig:
        """Parses dict into SimulationCaseConfig with nested dataclass models.

        Alias normalisation for the top-level 'method' field is applied here
        so that short-form YAML strings ('seeded', 'callback') are
        transparently converted to canonical equivalents before validation.
        """
        case_name = data.get("case_name", "unnamed_case")
        description = data.get("description", "")

        # Resolve method alias; default to "vacuum" when omitted
        raw_method = data.get("method", "vacuum")
        method = _normalise_method(raw_method)

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
            method=method,
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
