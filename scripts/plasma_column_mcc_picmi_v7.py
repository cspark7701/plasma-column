#!/usr/bin/env python3
"""
plasma_column_mcc_picmi.py

WarpX/PICMI plasma-column model for cyclotron axial injection.

This version is designed to be launched from JupyterLab by subprocess calls.
That is more robust than running several WarpX simulations in the same notebook
kernel, because pywarpx/WarpX keeps global simulation state.

Main physics modes
------------------
1. Seeded neutralization model:
   The proton beam ionizes H2 in the plasma-column cell. The proton_impact_ionization.dat
   cross-section file is used to estimate the neutralization build-up time and the
   initial compensating electron density.

2. Optional supported MCC processes:
   - electron_impact:
       plasma electrons + fixed neutral H2 background -> additional electrons + H2+.
       Uses electron_impact_ionization.dat.
   - charge_exchange:
       beam protons + fixed neutral H2 background -> charge-exchange scattering/loss proxy.
       Uses Hion_on_H2_charge_exchange.dat.

Important limitation
--------------------
WarpX's built-in MCC impact ionization transform is documented for electron-impact
ionization: source species = electrons, target species 1 = electrons, target species 2 = ions.
Therefore this script does NOT enable true proton-impact ionization as a built-in MCC
process. Proton-impact ionization is used here to set the initial compensation level
through the data-driven rate estimate. For fully self-consistent p+ + H2 -> p+ + H2+ + e-,
a custom source/collision extension is needed.

Typical commands
----------------
Dry run:
    python plasma_column_mcc_picmi.py --dry_run

Seeded H2 compensation, no extra MCC:
    python plasma_column_mcc_picmi.py --output_dir runs/h2_seeded --neutralization -1 --run

With supported electron-impact MCC from seeded plasma electrons:
    python plasma_column_mcc_picmi.py --output_dir runs/h2_eimpact --mcc electron_impact --run

Write input file:
    python plasma_column_mcc_picmi.py --write_inputs --inputs_name inputs_plasma_column
"""

from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import _path_setup  # noqa: F401
except ImportError:
    from scripts import _path_setup  # noqa: F401

from pywarpx import picmi

try:
    from pywarpx.Diagnostics import reduced_diagnostics
    from pywarpx.Bucket import Bucket
except Exception:
    reduced_diagnostics = None
    Bucket = None


C = picmi.constants.c
QE = picmi.constants.q_e
KB = picmi.constants.kb
ME = picmi.constants.m_e
MP = 1.67262192369e-27
AMU = 1.66053906660e-27


@dataclass
class PlasmaColumnConfig:
    # Paths
    warpx_data_dir: str = "/home/cspark/Work/simulation_codes-working/warpx-data"
    h2_cross_section_dir: Optional[str] = None
    output_dir: str = "runs/plasma_column"

    # Run mode
    run: bool = False
    dry_run: bool = False
    write_inputs: bool = False
    inputs_name: str = "inputs_plasma_column_mcc"

    # Diagnostics
    diagformat: str = "plotfile"
    full_diag_every_step: bool = False
    checkpoint_period: int = 0
    restart_from: Optional[str] = None

    # Lightweight per-step text diagnostics
    record_particle_number: bool = True
    record_timestep: bool = True
    reduced_diag_dir: str = "reducedfiles/"
    postprocess_reduced: bool = True
    write_neutralization_model: bool = True

    # Grid
    nx: int = 64
    ny: int = 64
    nz: int = 512
    xmax: float = 1.0e-2
    ymax: float = 1.0e-2
    zmin: float = -2.0e-2
    zmax: float = 2.4e-1
    max_grid_size: int = 64

    # Beam
    beam_energy_keV: float = 30.0
    beam_current_mA: float = 10.0
    beam_radius: float = 2.0e-3
    beam_rms_divergence: float = 0.0

    # Plasma column
    column_zmin: float = 0.0
    column_length: float = 0.20
    plasma_radius: float = 3.0e-3
    neutralization: float = -1.0
    steady_state_neutralization: float = 0.90
    plasma_age: float = 2.0e-4
    electron_temperature_eV: float = 1.0
    initial_ion_fraction: float = 0.0

    # Gas
    gas: str = "H2"  # H2 or Kr
    pressure_torr: float = 1.0e-5
    gas_temperature_K: float = 300.0

    # Solenoid
    solenoid_Bz: float = 0.15
    field_margin: float = 0.0

    # Numerics — production defaults
    # Grid: 64×64×512 → dx=dy=0.31 mm, dz=0.51 mm (beam radius resolved by ~6 cells)
    # cfl=0.5 → dt≈3.4e-13 s (conservative for temporal accuracy)
    # max_steps=20000 → 9.5 ns = 2.7 beam transits (seeded equilibrium)
    #   For callback/MCC cases use max_steps=120000 (16.2 beam transits) via YAML override.
    # nppc=16 → reduces macro-particle shot noise by 4× vs development minimum of 4
    # diag_period=100 → ~200 plotfile snapshots over 20000 steps
    # reduced_diag_period=50 → fine-grained particle-count time series
    max_steps: int = 20000
    cfl: float = 0.5
    em_order: int = 3
    nppc_beam: int = 16
    nppc_plasma: int = 16
    particle_shape: str = "quadratic"
    diag_period: int = 100
    reduced_diag_period: int = 50

    cores: int = 8
    gpu: str = "auto"

    # MCC mode
    # choices: none, electron_impact, charge_exchange, both
    mcc: str = "none"
    mcc_ndt: int = 1


def parse_args() -> PlasmaColumnConfig:
    p = argparse.ArgumentParser(description="WarpX/PICMI plasma-column simulation with H2 MCC data support")

    p.add_argument("--cores", type=int, default=PlasmaColumnConfig.cores, help="Number of CPU worker cores / OpenMP threads (default: 8).")
    p.add_argument("--gpu", default=PlasmaColumnConfig.gpu, help="GPU device ID or 'auto' (checks GPU and makes default if available, default: auto).")
    p.add_argument("--warpx_data_dir", default=os.environ.get("WARPX_DATA_DIR", PlasmaColumnConfig.warpx_data_dir))
    p.add_argument("--h2_cross_section_dir", default=None)
    p.add_argument("--output_dir", default=PlasmaColumnConfig.output_dir)
    p.add_argument("--run", action="store_true", help="Actually run sim.step().")
    p.add_argument("--dry_run", action="store_true", help="Only print derived parameters and validate paths.")
    p.add_argument("--write_inputs", action="store_true", help="Write WarpX input file.")
    p.add_argument("--inputs_name", default=PlasmaColumnConfig.inputs_name)

    p.add_argument("--diagformat", default=PlasmaColumnConfig.diagformat)
    p.add_argument("--diag_period", type=int, default=PlasmaColumnConfig.diag_period)
    p.add_argument(
        "--full_diag_every_step",
        action="store_true",
        help=(
            "Write full field/particle diagnostics every time step. "
            "This can produce very large output; use only for small tests."
        ),
    )
    p.add_argument(
        "--checkpoint_period",
        type=int,
        default=PlasmaColumnConfig.checkpoint_period,
        help="Checkpoint dumping period in steps. If > 0, dumps full AMReX checkpoint directory (chk<step>/).",
    )
    p.add_argument(
        "--restart_from",
        type=str,
        default=PlasmaColumnConfig.restart_from,
        help="Path or directory name of checkpoint to restart simulation from.",
    )
    p.add_argument(
        "--no_record_particle_number",
        dest="record_particle_number",
        action="store_false",
        help="Disable the lightweight ParticleNumber reduced diagnostic.",
    )
    p.set_defaults(record_particle_number=PlasmaColumnConfig.record_particle_number)
    p.add_argument(
        "--no_record_timestep",
        dest="record_timestep",
        action="store_false",
        help="Disable the lightweight Timestep reduced diagnostic.",
    )
    p.set_defaults(record_timestep=PlasmaColumnConfig.record_timestep)
    p.add_argument(
        "--reduced_diag_period",
        type=int,
        default=PlasmaColumnConfig.reduced_diag_period,
        help="Reduced diagnostic period in PIC steps. Use 1 for every step.",
    )
    p.add_argument(
        "--reduced_diag_dir",
        default=PlasmaColumnConfig.reduced_diag_dir,
        help="Directory, relative to output_dir, for reduced diagnostic text files.",
    )
    p.add_argument(
        "--no_postprocess_reduced",
        dest="postprocess_reduced",
        action="store_false",
        help="Disable automatic postprocessing of ParticleNumber into neutralization_from_particle_number.csv.",
    )
    p.set_defaults(postprocess_reduced=PlasmaColumnConfig.postprocess_reduced)
    p.add_argument(
        "--no_write_neutralization_model",
        dest="write_neutralization_model",
        action="store_false",
        help="Disable writing analytic neutralization_model.csv.",
    )
    p.set_defaults(write_neutralization_model=PlasmaColumnConfig.write_neutralization_model)

    p.add_argument("--nx", type=int, default=PlasmaColumnConfig.nx)
    p.add_argument("--ny", type=int, default=PlasmaColumnConfig.ny)
    p.add_argument("--nz", type=int, default=PlasmaColumnConfig.nz)
    p.add_argument("--xmax", type=float, default=PlasmaColumnConfig.xmax)
    p.add_argument("--ymax", type=float, default=PlasmaColumnConfig.ymax)
    p.add_argument("--zmin", type=float, default=PlasmaColumnConfig.zmin)
    p.add_argument("--zmax", type=float, default=PlasmaColumnConfig.zmax)
    p.add_argument("--max_grid_size", type=int, default=PlasmaColumnConfig.max_grid_size)

    p.add_argument("--beam_energy_keV", type=float, default=PlasmaColumnConfig.beam_energy_keV)
    p.add_argument("--beam_current_mA", type=float, default=PlasmaColumnConfig.beam_current_mA)
    p.add_argument("--beam_radius", type=float, default=PlasmaColumnConfig.beam_radius)
    p.add_argument("--beam_rms_divergence", type=float, default=PlasmaColumnConfig.beam_rms_divergence)

    p.add_argument("--column_zmin", type=float, default=PlasmaColumnConfig.column_zmin)
    p.add_argument("--column_length", type=float, default=PlasmaColumnConfig.column_length)
    p.add_argument("--plasma_radius", type=float, default=PlasmaColumnConfig.plasma_radius)
    p.add_argument("--neutralization", type=float, default=PlasmaColumnConfig.neutralization)
    p.add_argument("--steady_state_neutralization", type=float, default=PlasmaColumnConfig.steady_state_neutralization)
    p.add_argument("--plasma_age", type=float, default=PlasmaColumnConfig.plasma_age)
    p.add_argument("--electron_temperature_eV", type=float, default=PlasmaColumnConfig.electron_temperature_eV)
    p.add_argument("--initial_ion_fraction", type=float, default=PlasmaColumnConfig.initial_ion_fraction)

    p.add_argument("--gas", choices=["H2", "Kr"], default=PlasmaColumnConfig.gas)
    p.add_argument("--pressure_torr", type=float, default=PlasmaColumnConfig.pressure_torr)
    p.add_argument("--gas_temperature_K", type=float, default=PlasmaColumnConfig.gas_temperature_K)

    p.add_argument("--solenoid_Bz", type=float, default=PlasmaColumnConfig.solenoid_Bz)
    p.add_argument("--field_margin", type=float, default=PlasmaColumnConfig.field_margin)

    p.add_argument("--max_steps", type=int, default=PlasmaColumnConfig.max_steps)
    p.add_argument("--cfl", type=float, default=PlasmaColumnConfig.cfl)
    p.add_argument("--em_order", type=int, default=PlasmaColumnConfig.em_order)
    p.add_argument("--nppc_beam", type=int, default=PlasmaColumnConfig.nppc_beam)
    p.add_argument("--nppc_plasma", type=int, default=PlasmaColumnConfig.nppc_plasma)
    p.add_argument("--particle_shape", default=PlasmaColumnConfig.particle_shape)

    p.add_argument("--mcc", choices=["none", "electron_impact", "charge_exchange", "both"], default=PlasmaColumnConfig.mcc)
    p.add_argument("--mcc_ndt", type=int, default=PlasmaColumnConfig.mcc_ndt)

    args = p.parse_args()
    return PlasmaColumnConfig(**vars(args))


def proton_beta_gamma_v(kinetic_energy_keV: float):
    kinetic_energy_J = kinetic_energy_keV * 1.0e3 * QE
    gamma = 1.0 + kinetic_energy_J / (MP * C**2)
    beta = math.sqrt(1.0 - 1.0 / gamma**2)
    v = beta * C
    u = gamma * v
    return beta, gamma, v, u


def gas_mass(cfg: PlasmaColumnConfig) -> float:
    if cfg.gas == "H2":
        return 2.01588 * AMU
    if cfg.gas == "Kr":
        return 83.798 * AMU
    raise ValueError(f"Unsupported gas: {cfg.gas}")


def gas_ion_name(cfg: PlasmaColumnConfig) -> str:
    return "gas_ions" if cfg.gas == "H2" else "kr_ions"


def gas_ionization_energy_eV(cfg: PlasmaColumnConfig, cross_section_file: Optional[Path] = None) -> float:
    """
    First ionization threshold energy [eV] used for electron-impact MCC.

    WarpX ScatteringProcess requires that the cross section at energy_penalty
    must be identically zero: WARPX_ALWAYS_ASSERT(getCrossSection(energy_penalty) == 0).
    If a cross-section data file is provided, determine the threshold energy
    directly from the file's zero-crossing / first energy entry so that this
    numerical condition is always strictly satisfied.
    """
    if cross_section_file is not None and cross_section_file.exists():
        try:
            with cross_section_file.open("r") as f:
                first_e = None
                zero_crossing_e = None
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    parts = s.replace(",", " ").split()
                    if len(parts) >= 2:
                        e_val = float(parts[0])
                        sig_val = float(parts[1])
                        if first_e is None:
                            first_e = e_val
                        if sig_val == 0.0:
                            zero_crossing_e = e_val
                        else:
                            break
                if zero_crossing_e is not None:
                    return zero_crossing_e
                if first_e is not None:
                    return first_e
        except Exception:
            pass

    # Physical default ionization thresholds (used if file not provided)
    return 15.43 if cfg.gas == "H2" else 14.00


def get_cross_section_dir(cfg: PlasmaColumnConfig) -> Path:
    if cfg.h2_cross_section_dir and cfg.gas == "H2":
        d = Path(cfg.h2_cross_section_dir).expanduser()
    else:
        d = Path(cfg.warpx_data_dir).expanduser() / "MCC_cross_sections" / cfg.gas
    return d


def load_two_column_cross_section(path: Path):
    """
    Load a WarpX-style cross-section table.

    Expected format:
        column 1: collision/projectile energy [eV]
        column 2: cross section [m^2]

    Lines beginning with # are ignored. Extra columns are ignored.
    """
    if not path.exists():
        raise FileNotFoundError(f"Cross-section file not found: {path}")

    rows = []
    with path.open("r") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.replace(",", " ").split()
            if len(parts) < 2:
                continue
            try:
                rows.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue

    if not rows:
        raise ValueError(f"No numeric two-column data found in {path}")

    arr = np.array(rows, dtype=float)
    order = np.argsort(arr[:, 0])
    return arr[order, 0], arr[order, 1]


def interp_sigma(path: Path, energy_eV: float) -> float:
    e, sigma = load_two_column_cross_section(path)
    if energy_eV <= e[0]:
        return float(sigma[0])
    if energy_eV >= e[-1]:
        return float(sigma[-1])
    return float(np.interp(energy_eV, e, sigma))


def gas_density_m3(pressure_torr: float, temperature_K: float) -> float:
    pressure_Pa = pressure_torr * 133.322368
    return pressure_Pa / (KB * temperature_K)


def estimate_neutralization_from_proton_impact(cfg: PlasmaColumnConfig, v_beam: float):
    """
    Estimate f(t) = f_ss * (1 - exp(-t/tau)) using proton-impact ionization data.

    Required file:
        <warpx_data_dir>/MCC_cross_sections/<gas>/proton_impact_ionization.dat

    The file must be in WarpX MCC format:
        column 1: center-of-mass collision energy [eV]
        column 2: total ionization cross section [m^2]

    For a neutral gas target initially at rest, the projectile lab energy is
    converted to center-of-mass energy by
        E_cm = E_lab * m_target / (m_projectile + m_target).
    """
    xsec_dir = get_cross_section_dir(cfg)
    xsec_file = xsec_dir / "proton_impact_ionization.dat"

    m_t = gas_mass(cfg)
    e_lab_eV = cfg.beam_energy_keV * 1.0e3
    e_cm_eV = e_lab_eV * m_t / (MP + m_t)

    sigma = interp_sigma(xsec_file, e_cm_eV)
    ng = gas_density_m3(cfg.pressure_torr, cfg.gas_temperature_K)
    tau = 1.0 / (ng * sigma * v_beam)
    f = cfg.steady_state_neutralization * (1.0 - math.exp(-cfg.plasma_age / tau))
    f = max(0.0, min(f, 0.999))
    return f, tau, ng, sigma, xsec_file, e_cm_eV

def get_electron_impact_dir(cfg: PlasmaColumnConfig) -> Path:
    """
    Returns the directory containing electron_impact_ionization.dat for the configured gas.

    For H2: warpx-data stores the electron-impact cross section under MCC_cross_sections/H/
            (atomic hydrogen approximation), not MCC_cross_sections/H2/.
            Fall back to H/ automatically if H2/electron_impact_ionization.dat is absent.
    For Kr: no electron-impact ionization data is available in warpx-data.
    """
    base = Path(cfg.warpx_data_dir).expanduser() / "MCC_cross_sections"
    # Primary: gas-specific directory
    primary = base / cfg.gas
    if (primary / "electron_impact_ionization.dat").exists():
        return primary
    # Fallback for H2: the file is under H/ (atomic hydrogen approximation)
    if cfg.gas == "H2":
        fallback = base / "H"
        if (fallback / "electron_impact_ionization.dat").exists():
            return fallback
    return primary  # will raise FileNotFoundError downstream if still missing


def validate_cross_section_files(cfg: PlasmaColumnConfig):
    xsec_dir = get_cross_section_dir(cfg)

    # Always needed for the seeded neutralization model when --neutralization -1 is used.
    status = {
        "proton_impact_ionization.dat": (xsec_dir / "proton_impact_ionization.dat").exists()
    }

    # Optional files are only needed when the corresponding MCC mode is requested.
    if cfg.mcc in ("electron_impact", "both"):
        eion_dir = get_electron_impact_dir(cfg)
        status["electron_impact_ionization.dat"] = (eion_dir / "electron_impact_ionization.dat").exists()

    if cfg.gas == "H2" and cfg.mcc in ("charge_exchange", "both"):
        status["Hion_on_H2_charge_exchange.dat"] = (xsec_dir / "Hion_on_H2_charge_exchange.dat").exists()

    return xsec_dir, status

def make_background_density_expression(cfg: PlasmaColumnConfig, ng: float):
    z0 = cfg.column_zmin
    z1 = cfg.column_zmin + cfg.column_length
    return f"((z >= {z0:.17e})*(z <= {z1:.17e})*{ng:.17e})"



def estimate_pic_dt(cfg: PlasmaColumnConfig) -> float:
    """
    Estimate the electromagnetic PIC time step from the 3D CFL condition.

    WarpX may use implementation-specific details for the exact time step, so the
    Timestep reduced diagnostic is still enabled by default. This estimate is only
    used for the analytic neutralization_model.csv.
    """
    dx = 2.0 * cfg.xmax / cfg.nx
    dy = 2.0 * cfg.ymax / cfg.ny
    dz = (cfg.zmax - cfg.zmin) / cfg.nz
    return cfg.cfl / (C * math.sqrt(dx**-2 + dy**-2 + dz**-2))


def setup_reduced_diagnostics(cfg: PlasmaColumnConfig):
    """
    Register lightweight WarpX reduced diagnostics.

    ParticleNumber writes the number of macroparticles and the sum of weights for
    every species. This is the recommended way to record proton/electron/ion
    evolution every step without dumping every particle every step.
    """
    if reduced_diagnostics is None or Bucket is None:
        print("WARNING: Could not import pywarpx reduced diagnostic buckets.")
        print("         ParticleNumber/Timestep reduced diagnostics were not registered.")
        return

    # Clear stale reduced diagnostics if the script is reused in a persistent Python process.
    try:
        reduced_diagnostics._diagnostics_dict.clear()
    except Exception:
        pass

    if cfg.record_particle_number:
        pnum = Bucket("particle_number")
        pnum.type = "ParticleNumber"
        pnum.intervals = str(cfg.reduced_diag_period)
        pnum.path = cfg.reduced_diag_dir
        pnum.extension = "txt"
        pnum.separator = ","
        pnum.precision = 16
        reduced_diagnostics._diagnostics_dict["particle_number"] = pnum

    if cfg.record_timestep:
        tdiag = Bucket("timestep")
        tdiag.type = "Timestep"
        tdiag.intervals = str(cfg.reduced_diag_period)
        tdiag.path = cfg.reduced_diag_dir
        tdiag.extension = "txt"
        tdiag.separator = ","
        tdiag.precision = 16
        reduced_diagnostics._diagnostics_dict["timestep"] = tdiag


def write_neutralization_model_csv(output_dir: Path, cfg: PlasmaColumnConfig, derived: dict):
    """
    Write analytic neutralization evolution:
        f(t) = f_ss * [1 - exp(-(plasma_age + t)/tau)]
    or constant f for fixed --neutralization >= 0.

    This is a model history, not a particle-count diagnostic.
    """
    if not cfg.write_neutralization_model:
        return

    path = output_dir / "neutralization_model.csv"
    dt = estimate_pic_dt(cfg)

    tau = float(derived.get("neutralization_tau_s", float("nan")))
    f_seed = float(derived.get("neutralization_fraction", 0.0))
    fss = float(cfg.steady_state_neutralization)

    with path.open("w") as f:
        f.write(
            "step,t_est_s,t_since_beam_turn_on_s,tau_s,"
            "neutralization_fraction_model,seeded_fraction_at_step0\n"
        )
        for step in range(cfg.max_steps + 1):
            t = step * dt
            if cfg.neutralization < 0.0 and tau == tau and tau > 0.0:
                f_model = fss * (1.0 - math.exp(-(cfg.plasma_age + t) / tau))
            else:
                f_model = f_seed
            f.write(
                f"{step},{t:.16e},{(cfg.plasma_age + t):.16e},"
                f"{tau:.16e},{f_model:.16e},{f_seed:.16e}\n"
            )

    print(f"Wrote analytic neutralization model: {path}")


def find_reduced_diag_file(output_dir: Path, name: str) -> Optional[Path]:
    candidates = [
        output_dir / "reducedfiles" / f"{name}.txt",
        output_dir / "reducedfiles" / name,
        output_dir / "diags" / "reducedfiles" / f"{name}.txt",
        output_dir / "diags" / "reducedfiles" / name,
        output_dir / f"{name}.txt",
        output_dir / name,
    ]
    for p in candidates:
        if p.exists():
            return p

    patterns = [f"{name}.txt", name, f"*{name}*.txt", f"*{name}*"]
    for pattern in patterns:
        matches = sorted(output_dir.rglob(pattern))
        matches = [p for p in matches if p.is_file()]
        if matches:
            return matches[0]
    return None


def postprocess_particle_number(output_dir: Path, cfg: PlasmaColumnConfig, derived: dict):
    """
    Convert WarpX ParticleNumber reduced diagnostic to a neutralization history CSV.

    Assumed species order follows the order in which species are added:
        beam_protons, plasma_electrons, gas_ions

    Columns in ParticleNumber are documented as:
        step, time,
        total macroparticles, macroparticles per species,
        total physical particles, physical particles per species.
    """
    if not cfg.postprocess_reduced:
        return

    pnum_path = find_reduced_diag_file(output_dir, "particle_number")
    if pnum_path is None:
        print("ParticleNumber reduced diagnostic file was not found.")
        print(f"Searched below: {output_dir}")
        existing = sorted([p for p in output_dir.rglob("*") if p.is_file()])
        if existing:
            print("Existing files under output_dir:")
            for p in existing[:50]:
                print(f"  {p.relative_to(output_dir)}")
            if len(existing) > 50:
                print(f"  ... {len(existing) - 50} more files")
        else:
            print("No files found under output_dir.")
        return

    try:
        data = np.genfromtxt(pnum_path, comments="#", delimiter=",")
        if data.size == 0:
            print(f"ParticleNumber file is empty: {pnum_path}")
            return
        if data.ndim == 1:
            data = data.reshape(1, -1)
        # On restarts, data lines may have overlapping or unordered steps; sort and deduplicate by step
        _, unique_indices = np.unique(data[:, 0], return_index=True)
        data = data[unique_indices]
    except Exception as exc:
        print(f"Could not read ParticleNumber file {pnum_path}: {exc}")
        return

    n_species = 3
    expected_min_cols = 2 + 2 * (1 + n_species)
    if data.shape[1] < expected_min_cols:
        print(
            f"ParticleNumber file has {data.shape[1]} columns; expected at least "
            f"{expected_min_cols}. File: {pnum_path}"
        )
        return

    # Species order used when registering diagnostics:
    # [beam_protons, plasma_electrons, gas_ions]
    step = data[:, 0].astype(int)
    time = data[:, 1]

    macro_total = data[:, 2]
    macro_beam_p = data[:, 3]
    macro_e = data[:, 4]
    macro_gas_i = data[:, 5]

    phys_offset = 2 + 1 + n_species
    phys_total = data[:, phys_offset]
    phys_beam_p = data[:, phys_offset + 1]
    phys_e = data[:, phys_offset + 2]
    phys_gas_i = data[:, phys_offset + 3]

    # Ratios are undefined when there are no beam protons in the diagnostic row.
    # Do not divide by np.finfo(float).tiny here; that can overflow when the
    # numerator is finite and phys_beam_p is zero at early steps.
    valid_proton_count = phys_beam_p > 0.0

    electron_over_proton = np.full_like(phys_e, np.nan, dtype=float)
    ion_over_proton = np.full_like(phys_gas_i, np.nan, dtype=float)
    global_net_neutralization = np.full_like(phys_e, np.nan, dtype=float)

    np.divide(
        phys_e,
        phys_beam_p,
        out=electron_over_proton,
        where=valid_proton_count,
    )
    np.divide(
        phys_gas_i,
        phys_beam_p,
        out=ion_over_proton,
        where=valid_proton_count,
    )

    # For a positive proton beam, electron compensation fraction is approximately
    # Ne/Np. Positive gas ions reduce the net negative compensation, so a simple
    # global net estimate is (Ne - Ni) / Np.
    np.divide(
        phys_e - phys_gas_i,
        phys_beam_p,
        out=global_net_neutralization,
        where=valid_proton_count,
    )

    out = output_dir / "neutralization_from_particle_number.csv"
    with out.open("w") as f:
        f.write(
            "step,time_s,"
            "macro_total,macro_beam_protons,macro_plasma_electrons,macro_gas_ions,"
            "physical_total,physical_beam_protons,physical_plasma_electrons,physical_gas_ions,"
            "electron_over_proton,ion_over_proton,global_net_neutralization\n"
        )
        for i in range(data.shape[0]):
            f.write(
                f"{step[i]},{time[i]:.16e},"
                f"{macro_total[i]:.16e},{macro_beam_p[i]:.16e},"
                f"{macro_e[i]:.16e},{macro_gas_i[i]:.16e},"
                f"{phys_total[i]:.16e},{phys_beam_p[i]:.16e},"
                f"{phys_e[i]:.16e},{phys_gas_i[i]:.16e},"
                f"{electron_over_proton[i]:.16e},{ion_over_proton[i]:.16e},"
                f"{global_net_neutralization[i]:.16e}\n"
            )

    print(f"Read ParticleNumber reduced diagnostic: {pnum_path}")
    print(f"Wrote neutralization history from particle counts: {out}")
    print(
        "Note: global_net_neutralization is a global particle-count ratio. "
        "For local column neutralization, use spatially filtered particle histograms "
        "or charge-density reductions inside the plasma-cell volume."
    )



def build_sim(cfg: PlasmaColumnConfig):
    beta, gamma, v_beam, u_beam = proton_beta_gamma_v(cfg.beam_energy_keV)
    current_A = cfg.beam_current_mA * 1.0e-3

    # Continuous beam injection: use a square top-hat source with the same area
    # as a circular beam of radius cfg.beam_radius.
    source_half_width = math.sqrt(math.pi) * cfg.beam_radius / 2.0
    source_area = (2.0 * source_half_width) ** 2
    beam_area_round = math.pi * cfg.beam_radius**2
    nb = current_A / (QE * v_beam * beam_area_round)
    flux = current_A / (QE * source_area)  # particles / m^2 / s

    if cfg.neutralization < 0.0:
        f_neut, tau, ng, sigma, xsec_file, e_cm_for_sigma = estimate_neutralization_from_proton_impact(cfg, v_beam)
    else:
        ng = gas_density_m3(cfg.pressure_torr, cfg.gas_temperature_K)
        xsec_dir = get_cross_section_dir(cfg)
        xsec_file = xsec_dir / "proton_impact_ionization.dat"
        m_t = gas_mass(cfg)
        e_cm_for_sigma = cfg.beam_energy_keV * 1.0e3 * m_t / (MP + m_t)
        sigma = interp_sigma(xsec_file, e_cm_for_sigma) if xsec_file.exists() else float("nan")
        tau = 1.0 / (ng * sigma * v_beam) if (ng > 0 and sigma == sigma and sigma > 0) else float("nan")
        f_neut = max(0.0, min(cfg.neutralization, 0.999))

    ne0 = f_neut * nb
    ni0 = cfg.initial_ion_fraction * ne0

    derived = {
        "beta": beta,
        "gamma": gamma,
        "beam_speed_m_per_s": v_beam,
        "beam_gamma_v_m_per_s": u_beam,
        "round_beam_density_m3": nb,
        "neutral_gas_density_m3": ng,
        "proton_impact_sigma_at_beam_energy_m2": sigma,
        "neutralization_tau_s": tau,
        "neutralization_fraction": f_neut,
        "seed_electron_density_m3": ne0,
        "seed_gas_ion_density_m3": ni0,
        "proton_impact_file": str(xsec_file),
        "center_of_mass_energy_for_sigma_eV": e_cm_for_sigma,
        "gas": cfg.gas,
        "source_half_width_m": source_half_width,
        "source_area_m2": source_area,
        "estimated_pic_dt_s": estimate_pic_dt(cfg),
        "reduced_diagnostic_period": cfg.reduced_diag_period,
        "species_order_for_particle_number": "beam_protons, plasma_electrons, gas_ions",
    }

    grid = picmi.Cartesian3DGrid(
        number_of_cells=[cfg.nx, cfg.ny, cfg.nz],
        lower_bound=[-cfg.xmax, -cfg.ymax, cfg.zmin],
        upper_bound=[+cfg.xmax, +cfg.ymax, cfg.zmax],
        lower_boundary_conditions=["open", "open", "open"],
        upper_boundary_conditions=["open", "open", "open"],
        lower_boundary_conditions_particles=["absorbing", "absorbing", "absorbing"],
        upper_boundary_conditions_particles=["absorbing", "absorbing", "absorbing"],
        warpx_max_grid_size=cfg.max_grid_size,
    )

    solver = picmi.ElectromagneticSolver(
        grid=grid,
        cfl=cfg.cfl,
        stencil_order=[cfg.em_order, cfg.em_order, cfg.em_order],
    )

    # Continuous proton source at zmin.
    vth_p = abs(cfg.beam_rms_divergence) * v_beam

    proton_flux_dist = picmi.UniformFluxDistribution(
        flux=flux,
        flux_normal_axis="z",
        surface_flux_position=cfg.zmin,
        flux_direction=1,
        lower_bound=[-source_half_width, -source_half_width, cfg.zmin],
        upper_bound=[+source_half_width, +source_half_width, cfg.zmin],
        directed_velocity=[0.0, 0.0, u_beam],
        rms_velocity=[vth_p, vth_p, 0.0],
        flux_tmin=0.0,
        flux_tmax=None,
    )

    beam_protons = picmi.Species(
        particle_type="proton",
        name="beam_protons",
        initial_distribution=proton_flux_dist,
    )

    # Seeded compensation electrons in the column.
    z0 = cfg.column_zmin
    z1 = cfg.column_zmin + cfg.column_length
    vth_e = math.sqrt(QE * cfg.electron_temperature_eV / ME)

    electron_density_expr = (
        f"((x*x + y*y) < ({cfg.plasma_radius:.17e})^2)"
        f"*(z >= {z0:.17e})*(z <= {z1:.17e})*{ne0:.17e}"
    )

    electron_dist = picmi.AnalyticDistribution(
        density_expression=electron_density_expr,
        lower_bound=[-cfg.plasma_radius, -cfg.plasma_radius, z0],
        upper_bound=[+cfg.plasma_radius, +cfg.plasma_radius, z1],
        directed_velocity=[0.0, 0.0, 0.0],
        rms_velocity=[vth_e, vth_e, vth_e],
    )

    plasma_electrons = picmi.Species(
        particle_type="electron",
        name="plasma_electrons",
        initial_distribution=electron_dist,
    )

    # H2+ ion species. This can be initially zero-ish, but for PICMI robustness
    # we define a very small physical distribution if initial_ion_fraction = 0.
    if ni0 > 0.0:
        ion_density = ni0
    else:
        ion_density = 1.0
    ion_density_expr = (
        f"((x*x + y*y) < ({cfg.plasma_radius:.17e})^2)"
        f"*(z >= {z0:.17e})*(z <= {z1:.17e})*{ion_density:.17e}"
    )
    ion_dist = picmi.AnalyticDistribution(
        density_expression=ion_density_expr,
        lower_bound=[-cfg.plasma_radius, -cfg.plasma_radius, z0],
        upper_bound=[+cfg.plasma_radius, +cfg.plasma_radius, z1],
        directed_velocity=[0.0, 0.0, 0.0],
        rms_velocity=[0.0, 0.0, 0.0],
    )

    gas_ions = picmi.Species(
        name=gas_ion_name(cfg),
        charge=QE,
        mass=gas_mass(cfg),
        initial_distribution=ion_dist,
    )

    # Hard-edge solenoid particle field.
    bz_z0 = z0 - cfg.field_margin
    bz_z1 = z1 + cfg.field_margin
    solenoid_field = picmi.AnalyticAppliedField(
        Bx_expression="0.0",
        By_expression="0.0",
        Bz_expression=f"(z >= {bz_z0:.17e})*(z <= {bz_z1:.17e})*{cfg.solenoid_Bz:.17e}",
    )

    # Optional MCC.
    collisions = []
    xsec_dir, status = validate_cross_section_files(cfg)
    neutral_expr = make_background_density_expression(cfg, ng)

    if cfg.mcc in ("electron_impact", "both"):
        if cfg.gas == "Kr":
            # No electron-impact ionization data available for Kr in warpx-data.
            # Skipping electron_impact MCC for Kr; only proton-impact seeded model applies.
            print(
                "  [WARNING] MCC electron_impact requested for Kr but no cross-section data exists."
                " Skipping electron-impact collision registration for Kr.",
                flush=True,
            )
        else:
            eion_dir = get_electron_impact_dir(cfg)
            eion_file = eion_dir / "electron_impact_ionization.dat"
            if not eion_file.exists():
                raise FileNotFoundError(f"electron-impact ionization file not found: {eion_file}")
            if eion_dir != xsec_dir:
                print(
                    f"  [INFO] electron_impact: using H/ cross-section data as H2 fallback: {eion_file}",
                    flush=True,
                )

            electron_scattering_processes = {
                "ionization": {
                    "cross_section": str(eion_file),
                    "energy": gas_ionization_energy_eV(cfg, cross_section_file=eion_file),
                    "species": gas_ions,
                }
            }

            collisions.append(
                picmi.MCCCollisions(
                    name="coll_electron_H2_ionization",
                    species=plasma_electrons,
                    background_density=neutral_expr,
                    max_background_density=ng,
                    background_temperature=cfg.gas_temperature_K,
                    background_mass=gas_mass(cfg),
                    ndt_supercycle=cfg.mcc_ndt,
                    scattering_processes=electron_scattering_processes,
                )
            )

    if cfg.mcc in ("charge_exchange", "both"):
        if cfg.gas != "H2":
            raise ValueError("charge_exchange mode is currently implemented only for H2 using Hion_on_H2_charge_exchange.dat")
        cx_file = xsec_dir / "Hion_on_H2_charge_exchange.dat"
        if not cx_file.exists():
            raise FileNotFoundError(f"charge-exchange file not found: {cx_file}")

        proton_scattering_processes = {
            "charge_exchange": {
                "cross_section": str(cx_file),
            }
        }

        collisions.append(
            picmi.MCCCollisions(
                name="coll_proton_H2_charge_exchange",
                species=beam_protons,
                background_density=neutral_expr,
                max_background_density=ng,
                background_temperature=cfg.gas_temperature_K,
                background_mass=gas_mass(cfg),
                ndt_supercycle=cfg.mcc_ndt,
                scattering_processes=proton_scattering_processes,
            )
        )

    full_diag_period = 1 if cfg.full_diag_every_step else cfg.diag_period

    field_diag = picmi.FieldDiagnostic(
        name="diag1",
        grid=grid,
        period=full_diag_period,
        data_list=["E", "B", "J", "rho", "part_per_cell"],
        warpx_format=cfg.diagformat,
    )

    particle_diag = picmi.ParticleDiagnostic(
        name="diag1",
        period=full_diag_period,
        species=[beam_protons, plasma_electrons, gas_ions],
        data_list=["position", "weighting", "momentum"],
        warpx_format=cfg.diagformat,
    )

    sim_kwargs = dict(
        solver=solver,
        max_steps=cfg.max_steps,
        verbose=1,
        particle_shape=cfg.particle_shape,
        warpx_current_deposition_algo="esirkepov",
        warpx_use_filter=1,
    )
    if collisions:
        sim_kwargs["warpx_collisions"] = collisions
        sim_kwargs["warpx_collisions_split_momentum_push"] = 0  # split_position_push renamed in picmistandard>=0.34


    sim = picmi.Simulation(**sim_kwargs)

    sim.add_species(
        beam_protons,
        layout=picmi.PseudoRandomLayout(n_macroparticles_per_cell=cfg.nppc_beam, grid=grid),
    )
    sim.add_species(
        plasma_electrons,
        layout=picmi.PseudoRandomLayout(n_macroparticles_per_cell=cfg.nppc_plasma, grid=grid),
    )
    sim.add_species(
        gas_ions,
        layout=picmi.PseudoRandomLayout(n_macroparticles_per_cell=max(1, cfg.nppc_plasma // 2), grid=grid),
    )

    sim.add_applied_field(solenoid_field)
    sim.add_diagnostic(field_diag)
    sim.add_diagnostic(particle_diag)

    if cfg.checkpoint_period > 0:
        chk_diag = picmi.Checkpoint(
            name="chk",
            period=cfg.checkpoint_period,
            write_dir=".",
            warpx_file_prefix="chk",
        )
        sim.add_diagnostic(chk_diag)

    # Lightweight per-step reduced diagnostics.
    # Use the official PICMI wrapper rather than manually editing pywarpx buckets.
    # This writes, by default:
    #   <output_dir>/<reduced_diag_dir>/particle_number.txt
    #   <output_dir>/<reduced_diag_dir>/timestep.txt
    if cfg.record_particle_number:
        sim.add_diagnostic(
            picmi.ReducedDiagnostic(
                diag_type="ParticleNumber",
                name="particle_number",
                period=cfg.reduced_diag_period,
                path=cfg.reduced_diag_dir,
                extension="txt",
                separator=",",
            )
        )

    if cfg.record_timestep:
        sim.add_diagnostic(
            picmi.ReducedDiagnostic(
                diag_type="Timestep",
                name="timestep",
                period=cfg.reduced_diag_period,
                path=cfg.reduced_diag_dir,
                extension="txt",
                separator=",",
            )
        )

    derived["cross_section_dir"] = str(xsec_dir)
    derived["cross_section_file_status"] = status
    derived["mcc_process_count"] = len(collisions)

    return sim, derived


def print_report(cfg: PlasmaColumnConfig, derived: dict):
    print("\n=== Plasma-column WarpX/PICMI setup ===")
    print("Configuration:")
    for k, v in asdict(cfg).items():
        print(f"  {k:32s}: {v}")
    print("\nDerived parameters:")
    for k, v in derived.items():
        print(f"  {k:32s}: {v}")

    sigma = derived.get("proton_impact_sigma_at_beam_energy_m2", float("nan"))
    if sigma == sigma:
        if sigma < 1.0e-25 or sigma > 1.0e-16:
            print("\nWARNING: The interpolated cross section is outside the expected m^2 range.")
            print("Check the warpx-data README to confirm the unit convention of the file.")


def main():
    cfg = parse_args()

    # Configure CPU threads and GPU accelerator
    from plasma_column.hardware import configure_runtime
    configure_runtime(cores=cfg.cores, gpu=cfg.gpu)

    output_dir = Path(cfg.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    sim, derived = build_sim(cfg)
    print_report(cfg, derived)

    if cfg.dry_run and not cfg.write_inputs and not cfg.run:
        print("\nDry run complete. No WarpX time stepping performed.")
        return

    os.chdir(output_dir)

    write_neutralization_model_csv(output_dir, cfg, derived)

    if cfg.write_inputs:
        sim.write_input_file(file_name=cfg.inputs_name)
        print(f"\nWrote WarpX input file: {output_dir / cfg.inputs_name}")

    if cfg.run:
        if cfg.restart_from:
            restart_path = Path(cfg.restart_from)
            # Resolve relative to output_dir or current dir
            if not restart_path.is_absolute() and not restart_path.exists():
                if (output_dir / restart_path).exists():
                    restart_path = output_dir / restart_path
            print(f"\n[RESTART] Restarting simulation from checkpoint: {restart_path}")
            from pywarpx import amr
            amr.restart = str(restart_path)

        print(f"\nRunning WarpX in: {output_dir}")
        sim.step()
        print("\nWarpX run complete.")
        postprocess_particle_number(output_dir, cfg, derived)

    if not cfg.run and not cfg.write_inputs:
        print("\nNo action selected. Use --run, --write_inputs, or --dry_run.")


if __name__ == "__main__":
    main()
