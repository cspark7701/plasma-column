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

from .constants import estimate_cfl_timestep


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
    "cxx_mcc":  "cxx_mcc_custom",
    "mcc":      "cxx_mcc_custom",
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


def build_numerics_cmd_flags(numerics: NumericsConfig, method: str) -> list[str]:
    """Return driver CLI flags for the grid, solver and particle numerics of a case.

    Shared by scripts/run_case.py and scripts/run_scan.py. Not passed here:
    max_steps / diag_period / checkpoint_period (handled by the callers, which apply CLI
    overrides) and mcc (the method flag from build_warpx_cmd_flags decides MCC).
    nppc_plasma is passed only to the seeded/MCC driver and only when > 0; the callback
    driver's seed species use its own nppc_seed, and nppc_plasma = 0 (vacuum) already means
    zero plasma density in the driver.
    """
    n = numerics
    flags = [
        "--nx", str(n.nx), "--ny", str(n.ny), "--nz", str(n.nz),
        "--xmax", repr(n.xmax_m), "--ymax", repr(n.ymax_m),
        "--zmin", repr(n.zmin_m), "--zmax", repr(n.zmax_m),
        "--cfl", repr(n.cfl),
        "--nppc_beam", str(n.nppc_beam),
        "--solver", n.solver, "--es_method", n.es_method, "--dt", repr(n.dt),
    ]
    if n.reduced_diag_period:
        flags += ["--reduced_diag_period", str(n.reduced_diag_period)]
    if _normalise_method(method) != "python_callback" and n.nppc_plasma > 0:
        flags += ["--nppc_plasma", str(n.nppc_plasma)]
    return flags


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


def build_plasma_cmd_flags(plasma: PlasmaConfig, method: str) -> list[str]:
    """Return driver CLI flags for the callback ionization source (python_callback only).

    Other plasma fields are not passed: the drivers take gas/pressure from separate flags and use their own
    column geometry defaults.
    """
    if _normalise_method(method) != "python_callback":
        return []
    return ["--source_rate_factor", repr(plasma.source_rate_factor),
            "--source_weight_target", repr(plasma.source_weight_target)]


def get_default_numerics_for_method(method: str) -> tuple[int, int]:
    """Return recommended (max_steps, checkpoint_period) for a given simulation method.

    Recommendations:
    - quick / vacuum / small test: max_steps=2000, checkpoint_period=500
    - seeded_compensation: max_steps=20000, checkpoint_period=2000
    - python_callback / cxx_mcc_custom: max_steps=120000, checkpoint_period=10000

    Args:
        method: Canonical or alias method string.

    Returns:
        tuple (max_steps, checkpoint_period)
    """
    method = _normalise_method(method)
    if method in ("python_callback", "cxx_mcc_custom"):
        return 120000, 10000
    elif method == "seeded_compensation":
        return 20000, 2000
    elif method == "vacuum":
        return 20000, 2000
    return 2000, 500


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
    # python_callback only. source_rate_factor != 1 multiplies the ionization rate (artificial, rescaled).
    source_rate_factor: float = 1.0
    source_weight_target: float = 100.0


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
    # Field solver passed to the WarpX driver: "em" (FDTD, CFL dt) or "es" (labframe
    # electrostatic, dt from electron dynamics unless dt > 0); es_method FFT or Multigrid.
    solver: str = "em"
    es_method: str = "FFT"
    dt: float = 0.0
    mcc: str = "none"
    checkpoint_period: int = 0
    restart_from: Optional[str] = None
    diag_period: Optional[int] = None
    reduced_diag_period: Optional[int] = None

    def estimate_dt(self) -> float:
        """Computes the 3D FDTD Courant-Friedrichs-Lewy (CFL) stable electromagnetic timestep [s]."""
        dx = 2.0 * self.xmax_m / self.nx
        dy = 2.0 * self.ymax_m / self.ny
        dz = (self.zmax_m - self.zmin_m) / self.nz
        return estimate_cfl_timestep(dx, dy, dz, self.cfl)


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

        if self.numerics.solver not in ("em", "es"):
            raise ValueError(f"numerics.solver must be 'em' or 'es', got '{self.numerics.solver}'")
        if self.numerics.es_method not in ("FFT", "Multigrid"):
            raise ValueError(f"numerics.es_method must be 'FFT' or 'Multigrid', got '{self.numerics.es_method}'")
        if self.numerics.dt < 0.0:
            raise ValueError(f"numerics.dt must be >= 0 (0 = estimate), got {self.numerics.dt}")
        if self.plasma.source_rate_factor <= 0.0:
            raise ValueError(f"plasma.source_rate_factor must be > 0, got {self.plasma.source_rate_factor}")

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
        canonical_method = _normalise_method(d.get("method", "vacuum"))
        d["method"] = canonical_method

        # Propagate top-level gas and pressure_torr into plasma sub-config if provided
        plasma_dict = dict(d.get("plasma") or {})
        if "gas" in d and "gas" not in plasma_dict:
            plasma_dict["gas"] = d["gas"]
        if "pressure_torr" in d and "pressure_torr" not in plasma_dict:
            plasma_dict["pressure_torr"] = d["pressure_torr"]
        d["plasma"] = plasma_dict

        # Default numerics (max_steps, checkpoint_period, and mcc) tailored to method if omitted
        rec_steps, rec_chk = get_default_numerics_for_method(canonical_method)
        raw_numerics = dict(d.get("numerics") or {})
        if "max_steps" not in raw_numerics:
            raw_numerics["max_steps"] = rec_steps
        if "checkpoint_period" not in raw_numerics:
            raw_numerics["checkpoint_period"] = rec_chk
        if "mcc" not in raw_numerics:
            if canonical_method == "cxx_mcc_custom":
                raw_numerics["mcc"] = "electron_impact"
            else:
                raw_numerics["mcc"] = "none"
        d["numerics"] = raw_numerics

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


def merge_dicts(default: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two dictionaries, giving priority to values in override."""
    merged = default.copy()
    for key, val in override.items():
        if isinstance(val, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = merge_dicts(merged[key], val)
        else:
            merged[key] = val
    return merged


# ── Matrix scan configuration ──────────────────────────────────────────────────

@dataclass
class ScanMatrixConfig:
    """Strongly-typed schema and validator for multi-case simulation scan matrices.

    Merges global matrix 'defaults' into each case specification, validates
    physical parameters and grid settings, and provides access to typed
    SimulationCaseConfig instances.
    """
    matrix_name: str
    description: str = ""
    defaults: dict[str, Any] = field(default_factory=dict)
    cases: list[SimulationCaseConfig] = field(default_factory=list)
    raw_cases: list[dict[str, Any]] = field(default_factory=list)
    # Optional analysis groups: stage name -> case names. A case may belong to several stages; each case
    # is still run once (task 97, cases/production.yaml).
    stages: dict[str, list[str]] = field(default_factory=dict)

    def validate(self) -> None:
        """Validates all cases within the matrix."""
        if not self.matrix_name:
            raise ValueError("matrix_name cannot be empty")
        if not self.cases:
            raise ValueError(f"Scan matrix '{self.matrix_name}' contains no cases")
        for case in self.cases:
            case.validate()
        names = [c.case_name for c in self.cases]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"Scan matrix '{self.matrix_name}' has duplicate case names: {duplicates}")
        for stage, members in self.stages.items():
            if not members:
                raise ValueError(f"Stage '{stage}' lists no cases")
            unknown = [m for m in members if m not in names]
            if unknown:
                raise ValueError(f"Stage '{stage}' lists unknown cases: {unknown}")

    def stage_cases(self, stage: str) -> list[SimulationCaseConfig]:
        """Return the cases of one stage, in the order the stage lists them."""
        if stage not in self.stages:
            raise KeyError(f"Unknown stage '{stage}'; available: {sorted(self.stages)}")
        by_name = {c.case_name: c for c in self.cases}
        return [by_name[n] for n in self.stages[stage]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScanMatrixConfig:
        """Parses a dictionary into a validated ScanMatrixConfig instance."""
        d = dict(data or {})
        matrix_name = d.get("matrix_name", "unnamed_matrix")
        description = d.get("description", "")
        defaults = dict(d.get("defaults") or {})
        raw_case_list = list(d.get("cases") or [])
        stages = {str(k): [str(n) for n in (v or [])] for k, v in dict(d.get("stages") or {}).items()}

        parsed_cases: list[SimulationCaseConfig] = []
        raw_cases_merged: list[dict[str, Any]] = []

        for case_item in raw_case_list:
            merged = merge_dicts(defaults, case_item)
            case_method = _normalise_method(merged.get("method", "vacuum"))
            if case_method == "vacuum" and "mcc" not in case_item.get("numerics", {}):
                if "numerics" in merged:
                    merged["numerics"]["mcc"] = "none"
            case_config = SimulationCaseConfig.from_dict(merged)
            parsed_cases.append(case_config)
            raw_cases_merged.append(merged)

        instance = cls(
            matrix_name=matrix_name,
            description=description,
            defaults=defaults,
            cases=parsed_cases,
            raw_cases=raw_cases_merged,
            stages=stages,
        )
        instance.validate()
        return instance

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> ScanMatrixConfig:
        """Loads and validates a ScanMatrixConfig from a YAML file."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Matrix YAML file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        """Converts matrix config back to dictionary representation."""
        return {
            "matrix_name": self.matrix_name,
            "description": self.description,
            "defaults": self.defaults,
            "cases": [case.to_dict() for case in self.cases],
        }
