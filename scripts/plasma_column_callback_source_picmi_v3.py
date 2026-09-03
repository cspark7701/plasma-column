#!/usr/bin/env python3
"""
plasma_column_callback_source_picmi.py

Prototype self-consistent proton-impact ionization source for a cyclotron
axial-injection plasma-column simulation in WarpX/PICMI.

This script adds electron/ion pairs through a Python callback:

    p + gas -> p + gas+ + e-

The callback is intended for physics verification and small simulations.  It is
not the final high-performance implementation.  For large MPI/GPU production
runs, use the C++ ion_impact_ionization BackgroundMCC patch.

Main use cases
--------------
H2:
    python plasma_column_callback_source_picmi.py --run --gas H2 --output_dir runs/h2_callback

Kr:
    python plasma_column_callback_source_picmi.py --run --gas Kr --output_dir runs/kr_callback

Vacuum/no source:
    python plasma_column_callback_source_picmi.py --run --enable_ionization_source 0 --output_dir runs/vacuum_callback_script

Cross-section input
-------------------
Required file:
    <warpx_data_dir>/MCC_cross_sections/<gas>/proton_impact_ionization.dat

Format:
    column 1: center-of-mass collision energy [eV]
    column 2: cross section [m^2]

The source uses a deterministic fractional-weight source:
    w_pair = w_proton * P_ion
with
    P_ion = 1 - exp[-n_g sigma(E_cm) v_rel dt].

This avoids event-count noise but can increase particle number rapidly. Use
--source_every_n_steps and --source_weight_min to control cost.
"""

from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

try:
    import _path_setup  # noqa: F401
except ImportError:
    from scripts import _path_setup  # noqa: F401

from pywarpx import picmi

try:
    from pywarpx.callbacks import installcallback
    from pywarpx import particle_containers
    from pywarpx import fields
except Exception:
    installcallback = None
    particle_containers = None
    fields = None


C = picmi.constants.c
QE = picmi.constants.q_e
KB = picmi.constants.kb
ME = picmi.constants.m_e
MP = 1.67262192369e-27
AMU = 1.66053906660e-27


@dataclass
class Config:
    warpx_data_dir: str = "/home/cspark/Work/simulation_codes-working/warpx-data"
    output_dir: str = "runs/plasma_column_callback"
    run: bool = False
    dry_run: bool = False
    write_inputs: bool = False
    inputs_name: str = "inputs_plasma_column_callback"

    # Grid/diagnostics
    # Production defaults: 64×64×512, cfl=0.5, 120000 steps (16.2 beam transits)
    # to accumulate sufficient ionization events for accurate dynamic neutralization.
    # nppc_beam=16 reduces macro-particle shot noise. diag_period=600 → 200 snapshots.
    nx: int = 64
    ny: int = 64
    nz: int = 512
    xmax: float = 1.0e-2
    ymax: float = 1.0e-2
    zmin: float = -2.0e-2
    zmax: float = 2.4e-1
    max_grid_size: int = 64
    max_steps: int = 120000
    cfl: float = 0.5
    em_order: int = 3
    diagformat: str = "plotfile"
    diag_period: int = 600
    checkpoint_period: int = 0
    restart_from: Optional[str] = None
    reduced_diag_period: int = 100
    reduced_diag_dir: str = "reducedfiles/"

    # Beam
    beam_energy_keV: float = 30.0
    beam_current_mA: float = 10.0
    beam_radius: float = 2.0e-3
    beam_rms_divergence: float = 0.0

    # Gas column
    gas: str = "H2"       # H2 or Kr
    pressure_torr: float = 1.0e-5
    gas_temperature_K: float = 300.0
    column_zmin: float = 0.0
    column_length: float = 0.20
    plasma_radius: float = 3.0e-3

    # Solenoid
    solenoid_Bz: float = 0.15

    # Source controls
    enable_ionization_source: int = 1
    source_every_n_steps: int = 1
    source_weight_min: float = 1.0
    secondary_electron_energy_eV: float = 1.0
    subtract_ionization_energy: int = 0

    # Particles
    nppc_beam: int = 16
    nppc_seed: int = 4
    particle_shape: str = "quadratic"

    # Hardware controls
    cores: int = 8
    gpu: str = "auto"


def parse_args() -> Config:
    p = argparse.ArgumentParser()
    for f in Config.__dataclass_fields__.values():
        name = "--" + f.name
        default = f.default
        if isinstance(default, bool):
            p.add_argument(name, action="store_true", default=default)
        elif isinstance(default, int):
            p.add_argument(name, type=int, default=default)
        elif isinstance(default, float):
            p.add_argument(name, type=float, default=default)
        else:
            p.add_argument(name, default=default)
    args = p.parse_args()
    if args.gas not in ("H2", "Kr"):
        raise ValueError("--gas must be H2 or Kr")
    return Config(**vars(args))


def gas_mass(gas: str) -> float:
    return 2.01588 * AMU if gas == "H2" else 83.798 * AMU


def gas_ionization_energy(gas: str) -> float:
    return 15.43 if gas == "H2" else 14.00


def gas_ion_name(gas: str) -> str:
    return "h2_ions" if gas == "H2" else "kr_ions"


def gas_density(pressure_torr: float, T: float) -> float:
    return pressure_torr * 133.322368 / (KB * T)


def proton_beta_gamma_v(E_keV: float):
    E_J = E_keV * 1e3 * QE
    gamma = 1.0 + E_J / (MP * C*C)
    beta = math.sqrt(1.0 - 1.0 / (gamma*gamma))
    v = beta * C
    u = gamma * v
    return beta, gamma, v, u


def estimate_pic_dt(cfg: Config) -> float:
    dx = 2.0 * cfg.xmax / cfg.nx
    dy = 2.0 * cfg.ymax / cfg.ny
    dz = (cfg.zmax - cfg.zmin) / cfg.nz
    return cfg.cfl / (C * math.sqrt(dx**-2 + dy**-2 + dz**-2))


def load_cross_section(cfg: Config):
    path = (
        Path(cfg.warpx_data_dir).expanduser()
        / "MCC_cross_sections"
        / cfg.gas
        / "proton_impact_ionization.dat"
    )
    if not path.exists():
        raise FileNotFoundError(path)
    data = np.loadtxt(path, comments="#")
    if data.ndim != 2 or data.shape[1] < 2:
        raise ValueError(f"Bad cross-section table: {path}")
    return path, data[:, 0], data[:, 1]


def make_sim(cfg: Config):
    beta, gamma, vb, ub = proton_beta_gamma_v(cfg.beam_energy_keV)

    grid = picmi.Cartesian3DGrid(
        number_of_cells=[cfg.nx, cfg.ny, cfg.nz],
        lower_bound=[-cfg.xmax, -cfg.ymax, cfg.zmin],
        upper_bound=[ cfg.xmax,  cfg.ymax, cfg.zmax],
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

    # Continuous square top-hat proton source with the same area as circular beam radius.
    source_half_width = math.sqrt(math.pi) * cfg.beam_radius / 2.0
    source_area = (2.0 * source_half_width)**2
    current_A = cfg.beam_current_mA * 1e-3
    flux = current_A / (QE * source_area)

    vth_p = abs(cfg.beam_rms_divergence) * vb
    proton_dist = picmi.UniformFluxDistribution(
        flux=flux,
        flux_normal_axis="z",
        surface_flux_position=cfg.zmin,
        flux_direction=1,
        lower_bound=[-source_half_width, -source_half_width, cfg.zmin],
        upper_bound=[ source_half_width,  source_half_width, cfg.zmin],
        directed_velocity=[0.0, 0.0, ub],
        rms_velocity=[vth_p, vth_p, 0.0],
        flux_tmin=0.0,
        flux_tmax=None,
    )

    beam_protons = picmi.Species(
        particle_type="proton",
        name="beam_protons",
        initial_distribution=proton_dist,
    )

    # Define empty/tiny product species so the callback can add particles.
    z0 = cfg.column_zmin
    z1 = cfg.column_zmin + cfg.column_length
    tiny_density = (
        f"((x*x+y*y)<({cfg.plasma_radius})^2)"
        f"*(z>={z0})*(z<={z1})*1.0"
    )

    seed_dist = picmi.AnalyticDistribution(
        density_expression=tiny_density,
        lower_bound=[-cfg.plasma_radius, -cfg.plasma_radius, z0],
        upper_bound=[ cfg.plasma_radius,  cfg.plasma_radius, z1],
        directed_velocity=[0.0, 0.0, 0.0],
        rms_velocity=[0.0, 0.0, 0.0],
    )

    plasma_electrons = picmi.Species(
        particle_type="electron",
        name="plasma_electrons",
        initial_distribution=seed_dist,
    )

    gas_ions = picmi.Species(
        name=gas_ion_name(cfg.gas),
        charge=QE,
        mass=gas_mass(cfg.gas),
        initial_distribution=seed_dist,
    )

    solenoid = picmi.AnalyticAppliedField(
        Bx_expression="0.0",
        By_expression="0.0",
        Bz_expression=(
            f"(z>={cfg.column_zmin})"
            f"*(z<={cfg.column_zmin + cfg.column_length})"
            f"*{cfg.solenoid_Bz}"
        ),
    )

    field_diag = picmi.FieldDiagnostic(
        name="diag1",
        grid=grid,
        period=cfg.diag_period,
        data_list=["E", "B", "J", "rho", "part_per_cell"],
        warpx_format=cfg.diagformat,
    )

    part_diag = picmi.ParticleDiagnostic(
        name="diag1",
        period=cfg.diag_period,
        species=[beam_protons, plasma_electrons, gas_ions],
        data_list=["position", "weighting", "momentum"],
        warpx_format=cfg.diagformat,
    )

    sim = picmi.Simulation(
        solver=solver,
        max_steps=cfg.max_steps,
        verbose=1,
        particle_shape=cfg.particle_shape,
        warpx_current_deposition_algo="esirkepov",
        warpx_use_filter=1,
    )

    sim.add_species(
        beam_protons,
        layout=picmi.PseudoRandomLayout(
            n_macroparticles_per_cell=cfg.nppc_beam,
            grid=grid,
        ),
    )
    sim.add_species(
        plasma_electrons,
        layout=picmi.PseudoRandomLayout(
            n_macroparticles_per_cell=cfg.nppc_seed,
            grid=grid,
        ),
    )
    sim.add_species(
        gas_ions,
        layout=picmi.PseudoRandomLayout(
            n_macroparticles_per_cell=cfg.nppc_seed,
            grid=grid,
        ),
    )

    sim.add_applied_field(solenoid)
    sim.add_diagnostic(field_diag)
    sim.add_diagnostic(part_diag)

    if cfg.checkpoint_period > 0:
        chk_diag = picmi.Checkpoint(
            name="chk",
            period=cfg.checkpoint_period,
            write_dir=".",
            warpx_file_prefix="chk",
        )
        sim.add_diagnostic(chk_diag)

    # Reduced diagnostics.
    try:
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
    except Exception as exc:
        print(f"WARNING: ReducedDiagnostic setup failed: {exc}")

    derived = {
        "beta": beta,
        "gamma": gamma,
        "beam_speed_m_per_s": vb,
        "beam_gamma_v_m_per_s": ub,
        "pic_dt_estimate_s": estimate_pic_dt(cfg),
        "neutral_gas_density_m3": gas_density(cfg.pressure_torr, cfg.gas_temperature_K),
    }

    return sim, derived


class ProtonImpactSource:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.step = 0
        self.xsec_path, self.Ecm, self.sigma = load_cross_section(cfg)

        self.protons = particle_containers.ParticleContainerWrapper("beam_protons")
        self.electrons = particle_containers.ParticleContainerWrapper("plasma_electrons")
        self.ions = particle_containers.ParticleContainerWrapper(gas_ion_name(cfg.gas))

        self.ng0 = gas_density(cfg.pressure_torr, cfg.gas_temperature_K)
        self.dt = estimate_pic_dt(cfg)
        self.mt = gas_mass(cfg)

        self.rng = np.random.default_rng(12345)

        print("Installed proton-impact ionization callback")
        print("  gas                  =", cfg.gas)
        print("  xsec file            =", self.xsec_path)
        print("  ng0 [m^-3]           =", self.ng0)
        print("  estimated dt [s]     =", self.dt)
        print("  source every N steps =", cfg.source_every_n_steps)

    def _sigma(self, Ecm_eV):
        return np.interp(Ecm_eV, self.Ecm, self.sigma, left=0.0, right=self.sigma[-1])

    def _neutral_mask(self, x, y, z):
        r2 = x*x + y*y
        z0 = self.cfg.column_zmin
        z1 = z0 + self.cfg.column_length
        return (z >= z0) & (z <= z1) & (r2 <= self.cfg.plasma_radius**2)

    def __call__(self):
        self.step += 1
        if self.step % max(1, self.cfg.source_every_n_steps) != 0:
            return

        # In some pywarpx builds these return lists of arrays, one array per tile.
        x_tiles = self.protons.get_particle_x(level=0, copy_to_host=True)
        y_tiles = self.protons.get_particle_y(level=0, copy_to_host=True)
        z_tiles = self.protons.get_particle_z(level=0, copy_to_host=True)
        ux_tiles = self.protons.get_particle_ux(level=0, copy_to_host=True)
        uy_tiles = self.protons.get_particle_uy(level=0, copy_to_host=True)
        uz_tiles = self.protons.get_particle_uz(level=0, copy_to_host=True)
        w_tiles = self.protons.get_particle_weight(level=0, copy_to_host=True)

        x_new_all = []
        y_new_all = []
        z_new_all = []
        w_new_all = []
        ux_parent_all = []
        uy_parent_all = []
        uz_parent_all = []

        mu = MP * self.mt / (MP + self.mt)

        for x, y, z, ux, uy, uz, w in zip(
            x_tiles, y_tiles, z_tiles, ux_tiles, uy_tiles, uz_tiles, w_tiles
        ):
            if len(x) == 0:
                continue

            x = np.asarray(x)
            y = np.asarray(y)
            z = np.asarray(z)
            ux = np.asarray(ux)
            uy = np.asarray(uy)
            uz = np.asarray(uz)
            w = np.asarray(w)

            u2 = ux*ux + uy*uy + uz*uz
            gamma = np.sqrt(1.0 + u2 / C**2)
            vx = ux / gamma
            vy = uy / gamma
            vz = uz / gamma
            vrel = np.sqrt(vx*vx + vy*vy + vz*vz)

            Ecm_eV = 0.5 * mu * vrel*vrel / QE
            sig = self._sigma(Ecm_eV)
            mask_gas = self._neutral_mask(x, y, z)

            P = np.zeros_like(vrel)
            idx = mask_gas & (vrel > 0.0)
            P[idx] = 1.0 - np.exp(-self.ng0 * sig[idx] * vrel[idx] * self.dt * self.cfg.source_every_n_steps)

            w_new = w * P
            mask = w_new > self.cfg.source_weight_min
            if not np.any(mask):
                continue

            x_new_all.append(x[mask])
            y_new_all.append(y[mask])
            z_new_all.append(z[mask])
            w_new_all.append(w_new[mask])
            ux_parent_all.append(ux[mask])
            uy_parent_all.append(uy[mask])
            uz_parent_all.append(uz[mask])

        if not x_new_all:
            return

        x_new = np.concatenate(x_new_all)
        y_new = np.concatenate(y_new_all)
        z_new = np.concatenate(z_new_all)
        w_new = np.concatenate(w_new_all)

        n_new = len(x_new)

        # Secondary electron, fixed isotropic kinetic energy.
        Ee_J = self.cfg.secondary_electron_energy_eV * QE
        ue = math.sqrt(Ee_J * (Ee_J + 2.0 * ME * C*C) / (C*C)) / ME if Ee_J > 0 else 0.0
        costh = self.rng.uniform(-1.0, 1.0, n_new)
        sinth = np.sqrt(np.maximum(0.0, 1.0 - costh*costh))
        phi = self.rng.uniform(0.0, 2.0*np.pi, n_new)

        ux_e = ue * sinth * np.cos(phi)
        uy_e = ue * sinth * np.sin(phi)
        uz_e = ue * costh

        # Gas ion initially cold/thermal approximation.
        vi_th = math.sqrt(KB * self.cfg.gas_temperature_K / gas_mass(self.cfg.gas))
        ux_i = self.rng.normal(0.0, vi_th, n_new)
        uy_i = self.rng.normal(0.0, vi_th, n_new)
        uz_i = self.rng.normal(0.0, vi_th, n_new)

        self.electrons.add_particles(
            x=x_new, y=y_new, z=z_new,
            ux=ux_e, uy=uy_e, uz=uz_e,
            w=w_new,
            unique_particles=False,
        )
        self.ions.add_particles(
            x=x_new, y=y_new, z=z_new,
            ux=ux_i, uy=uy_i, uz=uz_i,
            w=w_new,
            unique_particles=False,
        )


def write_neutralization_model(cfg: Config, derived: dict, output_dir: Path):
    beta, gamma, vb, ub = proton_beta_gamma_v(cfg.beam_energy_keV)
    xsec_path, Ecm, sigma = load_cross_section(cfg)
    Ecm0 = 0.5 * (MP * gas_mass(cfg.gas) / (MP + gas_mass(cfg.gas))) * vb*vb / QE
    sig0 = np.interp(Ecm0, Ecm, sigma, left=0.0, right=sigma[-1])
    ng = gas_density(cfg.pressure_torr, cfg.gas_temperature_K)
    tau = 1.0 / (ng * sig0 * vb)
    dt = estimate_pic_dt(cfg)

    path = output_dir / "neutralization_source_model.csv"
    with path.open("w") as f:
        f.write("step,t_est_s,Ecm_eV,sigma_m2,tau_s,source_integral_fraction_1_minus_exp\n")
        for step in range(cfg.max_steps + 1):
            t = step * dt
            fmodel = 1.0 - math.exp(-t / tau)
            f.write(f"{step},{t:.16e},{Ecm0:.16e},{sig0:.16e},{tau:.16e},{fmodel:.16e}\n")


def find_reduced_diag_file(output_dir: Path, name: str):
    candidates = [
        output_dir / "reducedfiles" / f"{name}.txt",
        output_dir / "reducedfiles" / name,
        output_dir / f"reducedfiles{name}.txt",
        output_dir / f"reducedfiles{name}",
        output_dir / f"{name}.txt",
        output_dir / name,
    ]
    for p in candidates:
        if p.exists():
            return p
    matches = sorted(output_dir.rglob(f"*{name}*"))
    matches = [p for p in matches if p.is_file()]
    return matches[0] if matches else None


def postprocess_particle_number(output_dir: Path):
    pnum = find_reduced_diag_file(output_dir, "particle_number")
    if pnum is None:
        print("ParticleNumber file was not found; skipping callback history CSV.")
        return

    data = np.genfromtxt(pnum, comments="#", delimiter=",")
    if data.size == 0:
        print(f"ParticleNumber file is empty: {pnum}")
        return
    if data.ndim == 1:
        data = data.reshape(1, -1)
    # On restarts, data lines may have overlapping or unordered steps; sort and deduplicate by step
    _, unique_indices = np.unique(data[:, 0], return_index=True)
    data = data[unique_indices]

    n_species = 3
    expected_min_cols = 2 + 2 * (1 + n_species)
    if data.shape[1] < expected_min_cols:
        print(f"Unexpected ParticleNumber column count: {data.shape[1]} in {pnum}")
        return

    step = data[:, 0].astype(int)
    time_s = data[:, 1]

    macro_total = data[:, 2]
    macro_beam_p = data[:, 3]
    macro_e = data[:, 4]
    macro_gas_i = data[:, 5]

    phys_offset = 2 + 1 + n_species
    phys_total = data[:, phys_offset]
    phys_beam_p = data[:, phys_offset + 1]
    phys_e = data[:, phys_offset + 2]
    phys_gas_i = data[:, phys_offset + 3]

    valid = phys_beam_p > 0.0
    electron_over_proton = np.full_like(phys_e, np.nan, dtype=float)
    ion_over_proton = np.full_like(phys_gas_i, np.nan, dtype=float)
    global_net_neutralization = np.full_like(phys_e, np.nan, dtype=float)

    np.divide(phys_e, phys_beam_p, out=electron_over_proton, where=valid)
    np.divide(phys_gas_i, phys_beam_p, out=ion_over_proton, where=valid)
    np.divide(phys_e - phys_gas_i, phys_beam_p, out=global_net_neutralization, where=valid)

    out = output_dir / "callback_neutralization_from_particle_number.csv"
    with out.open("w") as f:
        f.write(
            "step,time_s,"
            "macro_total,macro_beam_protons,macro_plasma_electrons,macro_gas_ions,"
            "physical_total,physical_beam_protons,physical_plasma_electrons,physical_gas_ions,"
            "electron_over_proton,ion_over_proton,global_net_neutralization\n"
        )
        for i in range(data.shape[0]):
            f.write(
                f"{step[i]},{time_s[i]:.16e},"
                f"{macro_total[i]:.16e},{macro_beam_p[i]:.16e},{macro_e[i]:.16e},{macro_gas_i[i]:.16e},"
                f"{phys_total[i]:.16e},{phys_beam_p[i]:.16e},{phys_e[i]:.16e},{phys_gas_i[i]:.16e},"
                f"{electron_over_proton[i]:.16e},{ion_over_proton[i]:.16e},{global_net_neutralization[i]:.16e}\n"
            )
    print(f"Read ParticleNumber reduced diagnostic: {pnum}")
    print(f"Wrote callback neutralization history: {out}")


def main():
    cfg = parse_args()

    # Configure CPU threads and GPU accelerator
    from plasma_column.hardware import configure_runtime
    configure_runtime(cores=cfg.cores, gpu=cfg.gpu)

    output_dir = Path(cfg.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Configuration")
    for k, v in asdict(cfg).items():
        print(f"  {k:30s}: {v}")

    sim, derived = make_sim(cfg)

    print("Derived")
    for k, v in derived.items():
        print(f"  {k:30s}: {v}")

    if cfg.dry_run and not cfg.run and not cfg.write_inputs:
        return

    os.chdir(output_dir)

    if cfg.enable_ionization_source:
        if installcallback is None or particle_containers is None:
            raise RuntimeError("pywarpx callback/particle_containers could not be imported")

        # pywarpx.callbacks.installcallback expects a Python function object with
        # a __name__ attribute.  A callable class instance is not accepted by
        # some WarpX/pywarpx versions, so keep the source object alive in a
        # closure and install a normal function wrapper.
        source = ProtonImpactSource(cfg)

        def proton_impact_ionization_callback():
            source()

        installcallback("particleinjection", proton_impact_ionization_callback)

    write_neutralization_model(cfg, derived, output_dir)

    if cfg.write_inputs:
        sim.write_input_file(file_name=cfg.inputs_name)
        print(f"Wrote {output_dir / cfg.inputs_name}")

    if cfg.run:
        if cfg.restart_from:
            restart_path = Path(cfg.restart_from)
            if not restart_path.is_absolute() and not restart_path.exists():
                if (output_dir / restart_path).exists():
                    restart_path = output_dir / restart_path
            print(f"\n[RESTART] Restarting simulation from checkpoint: {restart_path}")
            from pywarpx import amr
            amr.restart = str(restart_path)

        sim.step()
        print("Run complete")
        postprocess_particle_number(output_dir)


if __name__ == "__main__":
    main()
