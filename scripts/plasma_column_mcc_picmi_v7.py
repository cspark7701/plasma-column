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
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import _path_setup  # noqa: F401
except ImportError:
    from scripts import _path_setup  # noqa: F401

from plasma_column.constants import (
    beam_potential_depth_V,
    estimate_cfl_timestep,
    estimate_electrostatic_timestep,
)
from plasma_column.gas import (
    load_cross_section_table,
    interpolate_cross_section,
    gas_density_m3,
    lab_to_cm_energy,
)
try:
    from pywarpx import picmi
except (ImportError, ModuleNotFoundError):
    picmi = None

try:
    from pywarpx.Diagnostics import reduced_diagnostics
    from pywarpx.Bucket import Bucket
except Exception:
    reduced_diagnostics = None
    Bucket = None


if picmi is not None:
    C = picmi.constants.c
    QE = picmi.constants.q_e
    KB = picmi.constants.kb
    ME = picmi.constants.m_e
else:
    C = 299792458.0
    QE = 1.602176634e-19
    KB = 1.380649e-23
    ME = 9.1093837015e-31
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
    checkpoint_period: int = 2000
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
    # Seed ions per seed electron. 1.0 = quasi-neutral seed: an electron-only seed has no
    # confining charge before the beam arrives and loses ~70 % of its electrons (task 93).
    # With ions, eta_net starts near 0 and rises as the beam expels ions (~0.1 us, task 94).
    initial_ion_fraction: float = 1.0

    # Gas
    gas: str = "H2"  # H2 or Kr
    pressure_torr: float = 1.0e-5
    gas_temperature_K: float = 300.0

    # Solenoid
    solenoid_Bz: float = 0.15
    field_margin: float = 0.0
    # Explicit hard-edge solenoid extent [m] (task CW3 section model); None = cell +- field_margin.
    solenoid_zmin: Optional[float] = None
    solenoid_zmax: Optional[float] = None
    # Solenoid edge length [m] (task CW3). 0 = hard edge B_z only (tasks <= 111): no radial fringe
    # field, so the beam gets no Busch entrance kick and the solenoid barely focuses it. > 0:
    # B_z = B/2 [tanh((z - z0)/d) - tanh((z - z1)/d)] with the paraxial B_x,y = -(x,y)/2 dB_z/dz.
    solenoid_fringe: float = 0.0
    # Hard-edge quadrupoles (task CW3): "z0:z1:G;z0:z1:G" with gradient G [T/m], B_x = G y, B_y = G x
    # (G > 0 focuses protons in x, as in plasma_column.transport). Empty = none.
    quadrupoles: str = ""
    # Electrostatic end plugs (task 107): analytic potential phi(z) = -V * sum_k exp(-(z-z_k)^2/(2 w^2))
    # centred end_plug_offset outside each cell end (paraxial E_r = (r/2) phi''). V > 0 is a potential
    # hill for electrons. The offset (3 w by default) keeps the plugs off the seeded plasma, which would
    # otherwise start up to e*V high on the hill. Applied to particles only (no electrode surfaces or
    # image charges). 0 disables.
    end_plug_voltage: float = 0.0
    end_plug_width: float = 0.005
    end_plug_offset: float = 0.015
    # RF-bunched injection (task B2, docs/physics_notes/simulation_strategy_tasks.md): the injected
    # current is I_avg * f(t), with the periodic von Mises profile f = exp(kappa cos(omega t)) / I0(kappa)
    # (mean 1), and kappa set so that the beam fraction inside +-bunch_acceptance_deg/2 equals
    # beam_bunching_factor * bunch_acceptance_deg / 360.
    # Density bunching at constant velocity (no velocity modulation). 1.0 = DC beam.
    beam_bunching_factor: float = 1.0
    rf_frequency_hz: float = 50.0e6
    bunch_acceptance_deg: float = 36.0

    # Numerics — production defaults
    # Grid: 64×64×512 → dx=dy=0.31 mm, dz=0.51 mm (beam radius resolved by ~6 cells)
    # cfl=0.5 → dt≈3.4e-13 s (conservative for temporal accuracy)
    # max_steps=20000 → 9.5 ns = 2.7 beam transits (seeded equilibrium)
    #   For callback/MCC cases use max_steps=120000 (16.2 beam transits) via YAML override.
    # nppc=16 → reduces macro-particle shot noise by 4× vs development minimum of 4
    # diag_period=100 → ~200 plotfile snapshots over 20000 steps
    # reduced_diag_period=50 → fine-grained particle-count time series
    max_steps: int = 20000
    # Field solver: "em" (electromagnetic FDTD, dt set by the light-wave CFL) or
    # "es" (labframe electrostatic, dt set by electron dynamics; see estimate_pic_dt)
    solver: str = "em"
    es_method: str = "FFT"  # FFT (integrated Green function, open boundaries) or Multigrid
    dt: float = 0.0  # explicit time step [s] for solver="es"; 0 = estimate from electron limits
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
    p.add_argument("--solenoid_zmin", type=float, default=None, help="Solenoid start [m] (default: cell start - margin).")
    p.add_argument("--solenoid_zmax", type=float, default=None, help="Solenoid end [m] (default: cell end + margin).")
    p.add_argument("--solenoid_fringe", type=float, default=PlasmaColumnConfig.solenoid_fringe,
                   help="Solenoid tanh edge length [m]; 0 = hard edge without radial fringe field.")
    p.add_argument("--quadrupoles", default=PlasmaColumnConfig.quadrupoles,
                   help='Hard-edge quadrupoles "z0:z1:G;..." with G in T/m (B_x = G y, B_y = G x).')
    p.add_argument("--end_plug_voltage", type=float, default=PlasmaColumnConfig.end_plug_voltage,
                   help="Analytic end-plug potential depth [V] at both cell ends (>0 repels electrons; 0 = off).")
    p.add_argument("--end_plug_width", type=float, default=PlasmaColumnConfig.end_plug_width,
                   help="Gaussian width of each end-plug potential [m].")
    p.add_argument("--end_plug_offset", type=float, default=PlasmaColumnConfig.end_plug_offset,
                   help="Distance of each end-plug centre outside the cell end [m].")
    p.add_argument("--beam_bunching_factor", type=float, default=PlasmaColumnConfig.beam_bunching_factor,
                   help="Bunching factor inside the acceptance window of the injected beam (1 = DC).")
    p.add_argument("--rf_frequency_hz", type=float, default=PlasmaColumnConfig.rf_frequency_hz)
    p.add_argument("--bunch_acceptance_deg", type=float, default=PlasmaColumnConfig.bunch_acceptance_deg)

    p.add_argument("--max_steps", type=int, default=PlasmaColumnConfig.max_steps)
    p.add_argument("--solver", choices=["em", "es"], default=PlasmaColumnConfig.solver,
                   help="em: electromagnetic FDTD (CFL dt ~0.34 ps); es: electrostatic (dt from electron limits).")
    p.add_argument("--es_method", choices=["FFT", "Multigrid"], default=PlasmaColumnConfig.es_method)
    p.add_argument("--dt", type=float, default=PlasmaColumnConfig.dt,
                   help="Explicit time step [s] for --solver es (0 = estimate).")
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
    """Resolve directory containing proton-impact cross section files for cfg.gas.

    Checks in order:
    1. Explicitly configured cfg.h2_cross_section_dir (if gas is H2)
    2. <warpx_data_dir>/MCC_cross_sections/<gas>
    3. Project-bundled cross sections in warpx_proton_impact_cross_sections_linear/MCC_cross_sections/<gas>
    """
    if cfg.h2_cross_section_dir and cfg.gas == "H2":
        d = Path(cfg.h2_cross_section_dir).expanduser()
        if (d / "proton_impact_ionization.dat").exists():
            return d

    # Primary: check user/configured warpx_data_dir
    primary = Path(cfg.warpx_data_dir).expanduser() / "MCC_cross_sections" / cfg.gas
    if (primary / "proton_impact_ionization.dat").exists():
        return primary

    # Fallback: repository bundled cross sections via CrossSectionDatabase or relative path
    try:
        from plasma_column.gas import CrossSectionDatabase
        db = CrossSectionDatabase()
        for candidate in (cfg.gas, cfg.gas.capitalize(), cfg.gas.upper()):
            bundled = db.base_dir / candidate
            if (bundled / "proton_impact_ionization.dat").exists():
                return bundled
    except Exception:
        pass

    project_root = Path(__file__).resolve().parent.parent
    for candidate in (cfg.gas, cfg.gas.capitalize(), cfg.gas.upper()):
        bundled = (
            project_root
            / "warpx_proton_impact_cross_sections_linear"
            / "MCC_cross_sections"
            / candidate
        )
        if (bundled / "proton_impact_ionization.dat").exists():
            return bundled

    return primary


def interp_sigma(path: Path, energy_eV: float) -> float:
    """Interpolate cross section [m^2] at collision energy_eV using plasma_column.gas."""
    energies, sigmas, _ = load_cross_section_table(path)
    return interpolate_cross_section(energies, sigmas, energy_eV)


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

def end_plug_field_expressions(cfg: PlasmaColumnConfig, z0: float, z1: float) -> dict[str, str]:
    """
    Applied-field expressions of the analytic end plugs (empty dict when disabled).

    phi(z) = -V * sum_k g_k, g_k = exp(-(z - z_k)^2 / (2 w^2)), z_k = z0 - offset, z1 + offset.
    E_z = -phi' = -V * sum_k (z - z_k) / w^2 * g_k
    E_x = (x/2) phi'' , E_y = (y/2) phi'' with phi'' = -V * sum_k ((z - z_k)^2 / w^4 - 1 / w^2) * g_k
    (paraxial solution of Laplace's equation around the axis).
    """
    V, w = cfg.end_plug_voltage, cfg.end_plug_width
    if V == 0.0:
        return {}
    if w <= 0.0:
        raise ValueError("end_plug_width must be positive")
    centres = (z0 - cfg.end_plug_offset, z1 + cfg.end_plug_offset)
    g = [f"exp(-(z-({zk:.17e}))*(z-({zk:.17e}))/({2.0 * w * w:.17e}))" for zk in centres]
    dz = [f"(z-({zk:.17e}))" for zk in centres]
    ez = " + ".join(f"{d}*{gk}" for d, gk in zip(dz, g))
    phi2 = " + ".join(f"({d}*{d}/{w**4:.17e} - {1.0 / w**2:.17e})*{gk}" for d, gk in zip(dz, g))
    return {
        "Ez_expression": f"-({V:.17e})/({w * w:.17e})*({ez})",
        "Ex_expression": f"0.5*x*(-({V:.17e}))*({phi2})",
        "Ey_expression": f"0.5*y*(-({V:.17e}))*({phi2})",
    }


def solenoid_field_expressions(B: float, z0: float, z1: float, fringe: float) -> dict[str, str]:
    """
    Solenoid field between z0 and z1. fringe = 0: hard-edge B_z only (no radial field). fringe = d > 0:
    B_z = B/2 [tanh((z - z0)/d) - tanh((z - z1)/d)], B_x = -(x/2) dB_z/dz, B_y = -(y/2) dB_z/dz
    (paraxial, divergence-free to first order in r), which gives the Busch kick at the edges.
    """
    if fringe <= 0.0:
        return {"Bx_expression": "0.0", "By_expression": "0.0",
                "Bz_expression": f"(z >= {z0:.17e})*(z <= {z1:.17e})*({B:.17e})"}
    t0, t1 = f"tanh((z-({z0:.17e}))/{fringe:.17e})", f"tanh((z-({z1:.17e}))/{fringe:.17e})"
    dbz = f"(({B:.17e})/(2.0*{fringe:.17e}))*((1.0-{t0}*{t0}) - (1.0-{t1}*{t1}))"
    return {"Bx_expression": f"(-0.5*x*{dbz})", "By_expression": f"(-0.5*y*{dbz})",
            "Bz_expression": f"(0.5*({B:.17e})*({t0} - {t1}))"}


def quadrupole_field_expressions(spec: str) -> dict[str, str]:
    """
    Hard-edge quadrupole fields from "z0:z1:G;z0:z1:G" (G [T/m]): B_x = G y, B_y = G x inside
    z0 <= z <= z1, so that G > 0 focuses protons (moving in +z) in x. Empty spec gives zero fields.
    """
    bx, by = [], []
    for item in filter(None, (t.strip() for t in spec.split(";"))):
        z0, z1, g = (float(v) for v in item.split(":"))
        if z1 <= z0:
            raise ValueError(f"quadrupole {item!r}: z1 must exceed z0")
        win = f"(z >= {z0:.17e})*(z <= {z1:.17e})*({g:.17e})"
        bx.append(f"{win}*y")
        by.append(f"{win}*x")
    return {"Bx_expression": " + ".join(bx) or "0.0", "By_expression": " + ".join(by) or "0.0"}


def bunch_profile_kappa(bunching_factor: float, acceptance_deg: float) -> float:
    """
    von Mises concentration kappa whose fraction inside +-acceptance/2 is bunching_factor * acceptance / 360.
    Returns 0 for a DC beam (bunching_factor <= 1).
    """
    if bunching_factor <= 1.0:
        return 0.0
    target = bunching_factor * acceptance_deg / 360.0
    if not 0.0 < target < 1.0:
        raise ValueError("beam_bunching_factor * bunch_acceptance_deg / 360 must be below 1")
    from scipy.integrate import quad
    from scipy.optimize import brentq
    from scipy.special import i0e

    half = math.radians(acceptance_deg) / 2.0

    def frac(k: float) -> float:
        # exp(k cos x) / (2 pi I0(k)) = exp(k (cos x - 1)) / (2 pi i0e(k)), stable for large k
        val, _ = quad(lambda x: math.exp(k * (math.cos(x) - 1.0)), -half, half)
        return val / (2.0 * math.pi * i0e(k))

    return brentq(lambda k: frac(k) - target, 1e-6, 2000.0)


def bunched_flux_expression(cfg: PlasmaColumnConfig, flux: float) -> str:
    """flux_function(x,y,z,t) of the bunched beam: flux * exp(kappa (cos(omega t) - 1)) / i0e(kappa)."""
    from scipy.special import i0e

    k = bunch_profile_kappa(cfg.beam_bunching_factor, cfg.bunch_acceptance_deg)
    omega = 2.0 * math.pi * cfg.rf_frequency_hz
    return f"{flux / i0e(k):.17e}*exp({k:.17e}*(cos({omega:.17e}*t)-1.0))"


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
        cx_cand = xsec_dir / "Hion_on_H2_charge_exchange.dat"
        if not cx_cand.exists():
            cx_cand = Path(cfg.warpx_data_dir).expanduser() / "MCC_cross_sections" / "H" / "Hion_on_H2_charge_exchange.dat"
        status["Hion_on_H2_charge_exchange.dat"] = cx_cand.exists()

    return xsec_dir, status

def make_background_density_expression(cfg: PlasmaColumnConfig, ng: float):
    z0 = cfg.column_zmin
    z1 = cfg.column_zmin + cfg.column_length
    return f"((z >= {z0:.17e})*(z <= {z1:.17e})*{ng:.17e})"



def electrostatic_dt_limits(cfg: PlasmaColumnConfig) -> dict:
    """
    Electron-dynamics time-step limits for the electrostatic solver.

    Electron density: the larger of the uncompensated round-beam density and the seed density
    (trapped electrons accumulate up to about the beam density). Fastest electron: one that
    falls through the full uncompensated beam potential plus 5 thermal speeds.
    """
    _, _, v_beam, _ = proton_beta_gamma_v(cfg.beam_energy_keV)
    current_A = cfg.beam_current_mA * 1.0e-3
    nb = current_A / (QE * v_beam * math.pi * cfg.beam_radius**2)
    ne_max = max(nb, cfg.steady_state_neutralization * nb)
    dphi = beam_potential_depth_V(current_A, v_beam, cfg.beam_radius, min(cfg.xmax, cfg.ymax))
    ve_max = math.sqrt(2.0 * QE * dphi / ME) + 5.0 * math.sqrt(QE * cfg.electron_temperature_eV / ME)
    dx_min = min(2.0 * cfg.xmax / cfg.nx, 2.0 * cfg.ymax / cfg.ny, (cfg.zmax - cfg.zmin) / cfg.nz)
    limits = estimate_electrostatic_timestep(dx_min, cfg.solenoid_Bz, ne_max, ve_max)
    limits.update({"beam_potential_depth_V": dphi, "electron_speed_max_m_per_s": ve_max,
                   "electron_density_for_dt_m3": ne_max})
    return limits


def checkpoint_step(path: str | Path) -> int:
    """Step number of a WarpX checkpoint directory named chkNNNNNN."""
    m = re.search(r"chk(\d+)$", Path(path).name)
    if m is None:
        raise ValueError(f"cannot read the step from checkpoint name {path}")
    return int(m.group(1))


def estimate_pic_dt(cfg: PlasmaColumnConfig) -> float:
    """
    PIC time step [s].

    solver="em": 3D CFL estimate (WarpX computes the exact value; the Timestep reduced
    diagnostic records it). solver="es": cfg.dt if set, otherwise the electron-dynamics
    limit from electrostatic_dt_limits; this value is passed to WarpX as the time step.
    """
    if cfg.solver == "es":
        return cfg.dt if cfg.dt > 0.0 else electrostatic_dt_limits(cfg)["dt_s"]
    dx = 2.0 * cfg.xmax / cfg.nx
    dy = 2.0 * cfg.ymax / cfg.ny
    dz = (cfg.zmax - cfg.zmin) / cfg.nz
    return estimate_cfl_timestep(dx, dy, dz, cfg.cfl)


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
        "field_solver": cfg.solver if cfg.solver == "em" else f"es ({cfg.es_method})",
        # Flux injection adds nppc_beam macroparticles per source cell per step
        "beam_macroparticle_weight": (current_A * estimate_pic_dt(cfg) / QE)
        / (cfg.nppc_beam * source_area / ((2.0 * cfg.xmax / cfg.nx) * (2.0 * cfg.ymax / cfg.ny))),
        "beam_domain_transit_steps": (cfg.zmax - cfg.zmin) / (v_beam * estimate_pic_dt(cfg)),
        "beam_reaches_column_end_step": (cfg.column_zmin + cfg.column_length - cfg.zmin) / (v_beam * estimate_pic_dt(cfg)),
        "reduced_diagnostic_period": cfg.reduced_diag_period,
        "end_plug_voltage_V": cfg.end_plug_voltage,
        "end_plug_width_m": cfg.end_plug_width,
        "end_plug_offset_m": cfg.end_plug_offset,
        "beam_bunching_factor": cfg.beam_bunching_factor,
        "bunch_profile_kappa": bunch_profile_kappa(cfg.beam_bunching_factor, cfg.bunch_acceptance_deg),
        "rf_frequency_hz": cfg.rf_frequency_hz,
        "species_order_for_particle_number": "beam_protons, plasma_electrons, gas_ions",
    }

    if cfg.solver == "es":
        derived["electrostatic_dt_limits"] = electrostatic_dt_limits(cfg)

    # Multigrid has no open boundary; use grounded (Dirichlet) walls for it.
    field_bc = "dirichlet" if (cfg.solver == "es" and cfg.es_method == "Multigrid") else "open"
    grid = picmi.Cartesian3DGrid(
        number_of_cells=[cfg.nx, cfg.ny, cfg.nz],
        lower_bound=[-cfg.xmax, -cfg.ymax, cfg.zmin],
        upper_bound=[+cfg.xmax, +cfg.ymax, cfg.zmax],
        lower_boundary_conditions=[field_bc] * 3,
        upper_boundary_conditions=[field_bc] * 3,
        lower_boundary_conditions_particles=["absorbing", "absorbing", "absorbing"],
        upper_boundary_conditions_particles=["absorbing", "absorbing", "absorbing"],
        warpx_max_grid_size=cfg.max_grid_size,
    )

    if cfg.solver == "es":
        solver = picmi.ElectrostaticSolver(grid=grid, method=cfg.es_method, required_precision=1.0e-7)
    else:
        solver = picmi.ElectromagneticSolver(
            grid=grid,
            cfl=cfg.cfl,
            stencil_order=[cfg.em_order, cfg.em_order, cfg.em_order],
        )

    # Continuous proton source at zmin.
    vth_p = abs(cfg.beam_rms_divergence) * v_beam

    flux_kwargs = dict(
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
    if cfg.beam_bunching_factor > 1.0:
        proton_flux_dist = picmi.AnalyticFluxDistribution(flux=bunched_flux_expression(cfg, flux), **flux_kwargs)
    else:
        proton_flux_dist = picmi.UniformFluxDistribution(flux=flux, **flux_kwargs)

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

    # Gas-ion species seeded at initial_ion_fraction * ne0 (default: equal to the electrons).
    # If that is zero (e.g. vacuum), PICMI still needs a distribution, so a 1 m^-3 placeholder is used.
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
    bz_z0 = z0 - cfg.field_margin if cfg.solenoid_zmin is None else cfg.solenoid_zmin
    bz_z1 = z1 + cfg.field_margin if cfg.solenoid_zmax is None else cfg.solenoid_zmax
    plug_E = end_plug_field_expressions(cfg, z0, z1)
    quad_B = quadrupole_field_expressions(cfg.quadrupoles)
    sol_B = solenoid_field_expressions(cfg.solenoid_Bz, bz_z0, bz_z1, cfg.solenoid_fringe)
    solenoid_field = picmi.AnalyticAppliedField(
        Bx_expression=f"{quad_B['Bx_expression']} + {sol_B['Bx_expression']}",
        By_expression=f"{quad_B['By_expression']} + {sol_B['By_expression']}",
        Bz_expression=sol_B["Bz_expression"],
        **plug_E,
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
            cx_fallback = Path(cfg.warpx_data_dir).expanduser() / "MCC_cross_sections" / "H" / "Hion_on_H2_charge_exchange.dat"
            if cx_fallback.exists():
                cx_file = cx_fallback
            else:
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

    sim_kwargs = dict(
        solver=solver,
        max_steps=cfg.max_steps,
        verbose=1,
        particle_shape=cfg.particle_shape,
        warpx_use_filter=1,
    )
    if cfg.solver == "es":
        sim_kwargs["time_step_size"] = estimate_pic_dt(cfg)
    else:
        sim_kwargs["warpx_current_deposition_algo"] = "esirkepov"
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

    if full_diag_period > 0:
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

        # PICMI step() runs max_steps more steps from the checkpoint; stop at max_steps in total.
        nsteps = cfg.max_steps - checkpoint_step(cfg.restart_from) if cfg.restart_from else cfg.max_steps
        print(f"\nRunning WarpX in: {output_dir} ({nsteps} steps)")
        sim.step(nsteps)
        print("\nWarpX run complete.")
        postprocess_particle_number(output_dir, cfg, derived)

    if not cfg.run and not cfg.write_inputs:
        print("\nNo action selected. Use --run, --write_inputs, or --dry_run.")


if __name__ == "__main__":
    main()
