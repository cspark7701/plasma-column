"""
src/plasma_column/schema.py

Strongly-typed dataclass schemas and validation rules for plasma column simulation cases.
Guarantees physical bound checks and schema consistency across YAML files and metadata.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, fields as dataclass_fields, is_dataclass
from pathlib import Path
from typing import Any, Optional, get_type_hints
import warnings
import yaml


def _dataclass_from_dict(cls: type, data: dict[str, Any] | None) -> Any:
    """Populate a dataclass from a dict, casting to each field's type."""
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return data

    type_hints = get_type_hints(cls)
    kwargs = {}

    for f in dataclass_fields(cls):
        if f.name not in data:
            continue
        val = data[f.name]
        ftype = type_hints.get(f.name, f.type)

        if is_dataclass(ftype) and isinstance(ftype, type):
            kwargs[f.name] = _dataclass_from_dict(ftype, val)
        elif val is not None:
            if ftype is int:
                kwargs[f.name] = int(val)
            elif ftype is float:
                kwargs[f.name] = float(val)
            elif ftype is str:
                kwargs[f.name] = str(val)
            else:
                kwargs[f.name] = val
        else:
            kwargs[f.name] = None

    return cls(**kwargs)


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


def get_runner_script(method: str, root_dir: Path | None = None) -> Path:
    """Return the absolute path to the appropriate runner script for a method.

    - 'python_callback' -> scripts/plasma_column_callback_source_picmi_v3.py
    - 'seeded_compensation', 'cxx_mcc_custom', 'vacuum' -> scripts/plasma_column_mcc_picmi_v7.py

    Args:
        method: Canonical or alias method string.
        root_dir: Root directory of the repository (defaults to 3 levels up).

    Returns:
        Path to the target runner script.
    """
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent.parent.parent
    method = _normalise_method(method)
    if method == "python_callback":
        return root_dir / "scripts" / "plasma_column_callback_source_picmi_v3.py"
    else:
        return root_dir / "scripts" / "plasma_column_mcc_picmi_v7.py"


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
        return ["--enable_ionization_source", "1"]
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
    checkpoint_period: int = 0
    restart_from: Optional[str] = None


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
        d = dict(data or {})
        if "case_name" not in d:
            d["case_name"] = "unnamed_case"
        d["method"] = _normalise_method(d.get("method", "vacuum"))

        config = _dataclass_from_dict(cls, d)
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
