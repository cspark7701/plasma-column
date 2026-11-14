"""
src/plasma_column/electron_trap.py

Test-electron confinement in the static fields of the plasma cell over the ion-production time
scale (task C2 of docs/physics_notes/simulation_strategy_tasks.md): does the solenoid + end-plug
trap hold electrons for tau_ion ~ 80 us, beyond the 1 us reach of the PIC runs?

Model (guiding centre, magnetized electrons, uniform B_z):
  - axial motion of the guiding centre under E_z of the analytic end plugs (same potential as the
    PIC driver, phi = -V sum_k exp(-(z - z_k)^2 / 2 w^2), centres `offset` outside the cell ends);
    the mirror force is zero in a uniform field and magnetic moment mu = m v_perp^2 / 2B is kept;
  - the guiding centre moves across B only at velocity changes (collisions, heating): a change
    dv_perp of the gyration vector shifts it by |dv_perp| / omega_c in a random direction;
  - net static beam well phi_b(r) = (1 - eta) x potential of a uniform 10 mA, 2 mm beam in a
    10 mm pipe; a radial step keeps the total energy (kinetic energy changes by e dphi_b; a step
    that would need negative kinetic energy is rejected);
  - elastic e-H2 collisions (Monte Carlo, isotropic, approximate momentum-transfer cross section,
    see ELASTIC_TABLE) at the gas density;
  - Coulomb heating by the beam protons inside the beam (r < a): energy diffusion at the rate
    H = e^4 n_b lnL / (4 pi eps0^2 m_e v_b), about 0.04 eV/us for 10 mA.
  Lost: guiding centre at r >= pipe radius (radial), or z outside the plugs (3 widths beyond each
  plug centre) or, without plugs, outside the cell by more than `escape_margin_m` (axial).

Not modeled: collective fields and fluctuations (the likely loss channel in PIC), ion dynamics,
e-e collisions, inelastic collisions (the electrons stay below ~10 eV), field errors and the
end-plug radial field (r << w). The result is therefore a classical upper bound on tau_c for a
static, quiescent trap.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from plasma_column.constants import EPSILON_0, KB, ME, QE, TORR_TO_PA

# Approximate e-H2 momentum-transfer cross section [eV, m^2] (shape of the standard swarm-derived
# compilations, accurate to about +-30%; peak ~1.7e-19 m^2 near 3 eV).
ELASTIC_TABLE = np.array([
    [0.01, 6.5e-20], [0.1, 9.5e-20], [0.5, 1.30e-19], [1.0, 1.50e-19], [2.0, 1.65e-19], [3.0, 1.70e-19],
    [5.0, 1.55e-19], [10.0, 1.15e-19], [20.0, 7.0e-20], [50.0, 3.5e-20], [100.0, 2.0e-20], [1000.0, 3.0e-21],
])


def elastic_cross_section_m2(energy_eV: np.ndarray) -> np.ndarray:
    e = np.clip(np.asarray(energy_eV, float), ELASTIC_TABLE[0, 0], ELASTIC_TABLE[-1, 0])
    return np.exp(np.interp(np.log(e), np.log(ELASTIC_TABLE[:, 0]), np.log(ELASTIC_TABLE[:, 1])))


@dataclass(frozen=True)
class TrapConfig:
    solenoid_Bz_T: float = 0.15
    plug_voltage_V: float = 300.0
    plug_width_m: float = 0.010
    plug_offset_m: float = 0.030
    cell_z_m: tuple[float, float] = (0.0, 0.20)
    eta: float = 0.9  # net compensation of the beam well inside the cell
    beam_current_A: float = 0.010
    beam_speed_m_s: float = 2.397e6  # 30 keV protons
    beam_radius_m: float = 0.002
    pipe_radius_m: float = 0.010
    pressure_torr: float = 1.0e-5
    gas_temperature_K: float = 300.0
    coulomb_log: float = 10.0
    beam_heating: bool = True
    collisions: bool = True
    escape_margin_m: float = 0.03

    @property
    def gas_density_m3(self) -> float:
        return self.pressure_torr * TORR_TO_PA / (KB * self.gas_temperature_K)

    @property
    def line_charge_C_m(self) -> float:
        return self.beam_current_A / self.beam_speed_m_s

    @property
    def beam_density_m3(self) -> float:
        return self.line_charge_C_m / (QE * math.pi * self.beam_radius_m**2)

    @property
    def heating_W(self) -> float:
        """Energy gain rate of an electron inside the beam from proton collisions [J/s]."""
        return QE**4 * self.beam_density_m3 * self.coulomb_log / (4 * math.pi * EPSILON_0**2 * ME * self.beam_speed_m_s)

    @property
    def plug_centres_m(self) -> tuple[float, float]:
        return self.cell_z_m[0] - self.plug_offset_m, self.cell_z_m[1] + self.plug_offset_m

    @property
    def z_bounds_m(self) -> tuple[float, float]:
        if self.plug_voltage_V > 0:
            z0, z1 = self.plug_centres_m
            return z0 - 3 * self.plug_width_m, z1 + 3 * self.plug_width_m
        return self.cell_z_m[0] - self.escape_margin_m, self.cell_z_m[1] + self.escape_margin_m

    def beam_potential_V(self, r_m: np.ndarray) -> np.ndarray:
        """Net beam-well potential (1 - eta) phi_b(r), zero at the pipe wall [V]."""
        a, R = self.beam_radius_m, self.pipe_radius_m
        k = self.line_charge_C_m / (4 * math.pi * EPSILON_0)
        r = np.asarray(r_m, float)
        inside = k * (1.0 - r**2 / a**2 + 2.0 * math.log(R / a))
        outside = 2.0 * k * np.log(R / np.maximum(r, 1e-12))
        return (1.0 - self.eta) * np.where(r <= a, inside, outside)

    def plug_Ez_V_m(self, z_m: np.ndarray) -> np.ndarray:
        if self.plug_voltage_V == 0:
            return np.zeros_like(z_m)
        V, w = self.plug_voltage_V, self.plug_width_m
        return -V / w**2 * sum((z_m - zk) * np.exp(-(z_m - zk) ** 2 / (2 * w * w)) for zk in self.plug_centres_m)

    def plug_potential_V(self, z_m: np.ndarray) -> np.ndarray:
        V, w = self.plug_voltage_V, self.plug_width_m
        return -V * sum(np.exp(-(np.asarray(z_m) - zk) ** 2 / (2 * w * w)) for zk in self.plug_centres_m)


def track(cfg: TrapConfig, n_electrons: int = 2000, t_end_s: float = 100e-6, dt_s: float = 2e-10,
          temperature_eV: float = 1.0, n_out: int = 200, seed: int = 1) -> dict[str, np.ndarray]:
    """
    Guiding-centre test electrons born uniformly in the beam (r < a) inside the cell with an
    isotropic Maxwellian of `temperature_eV`. Returns the surviving fraction, mean kinetic energy
    and cumulative axial/radial losses at n_out times.
    """
    if cfg.solenoid_Bz_T <= 0:
        raise ValueError("the guiding-centre model needs B_z > 0")
    rng = np.random.default_rng(seed)
    wc = QE * cfg.solenoid_Bz_T / ME
    n = n_electrons
    rr = cfg.beam_radius_m * np.sqrt(rng.random(n))
    th = rng.uniform(0, 2 * math.pi, n)
    gx, gy = rr * np.cos(th), rr * np.sin(th)
    z = rng.uniform(*cfg.cell_z_m, n)
    vt = math.sqrt(temperature_eV * QE / ME)
    v = rng.normal(0.0, vt, (n, 3))
    vpar, vperp = v[:, 2].copy(), np.hypot(v[:, 0], v[:, 1])
    alive = np.ones(n, bool)
    lost_axial = np.zeros(n, bool)
    lost_radial = np.zeros(n, bool)
    zlo, zhi = cfg.z_bounds_m
    ng = cfg.gas_density_m3
    sig_heat = math.sqrt(2.0 / 3.0 * cfg.heating_W * dt_s / ME)

    steps = int(round(t_end_s / dt_s))
    out_every = max(1, steps // n_out)
    t_out, surv, e_mean, ax, rad = [], [], [], [], []

    def kick(idx: np.ndarray, new_par: np.ndarray, old_x: np.ndarray, old_y: np.ndarray,
             new_x: np.ndarray, new_y: np.ndarray) -> None:
        """
        Velocity change of electrons idx (perpendicular vectors old -> new in one frame): new v_par,
        v_perp, and guiding-centre step (dv_perp x z_hat) / omega_c. Total energy is kept across the
        step in the beam well; a step needing negative kinetic energy is rejected.
        """
        dvx, dvy = new_x - old_x, new_y - old_y
        sx, sy = gx[idx] + dvy / wc, gy[idx] - dvx / wc
        dphi = cfg.beam_potential_V(np.hypot(sx, sy)) - cfg.beam_potential_V(np.hypot(gx[idx], gy[idx]))
        ke_new = 0.5 * ME * (new_par**2 + new_x**2 + new_y**2)
        ke_corr = ke_new + QE * dphi  # electron potential energy is -e phi
        ok = ke_corr > 0
        scale = np.sqrt(np.where(ok, ke_corr / np.maximum(ke_new, 1e-40), 1.0))
        j = idx[ok]
        vpar[j] = new_par[ok] * scale[ok]
        vperp[j] = np.hypot(new_x[ok], new_y[ok]) * scale[ok]
        gx[j], gy[j] = sx[ok], sy[ok]

    def old_perp(idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        phase = rng.uniform(0, 2 * math.pi, idx.size)  # gyrophase is not tracked
        return vperp[idx] * np.cos(phase), vperp[idx] * np.sin(phase)

    for s in range(steps + 1):
        if s % out_every == 0:
            ke = 0.5 * ME * (vpar[alive] ** 2 + vperp[alive] ** 2) / QE
            t_out.append(s * dt_s); surv.append(alive.mean()); e_mean.append(ke.mean() if ke.size else np.nan)
            ax.append(lost_axial.mean()); rad.append(lost_radial.mean())
            if not alive.any():
                break
        a = np.flatnonzero(alive)
        # Axial leapfrog: a_z = -(e/m) E_z
        vpar[a] += -QE / ME * cfg.plug_Ez_V_m(z[a]) * dt_s
        z[a] += vpar[a] * dt_s
        if cfg.collisions:
            speed = np.sqrt(vpar[a] ** 2 + vperp[a] ** 2)
            energy = 0.5 * ME * speed**2 / QE
            hit = rng.random(a.size) < ng * elastic_cross_section_m2(energy) * speed * dt_s
            if hit.any():
                h = a[hit]
                sp = speed[hit] * math.sqrt(max(0.0, 1.0 - 2 * ME / (2.016 * 1.6605e-27)))
                mu = rng.uniform(-1, 1, h.size)
                ph = rng.uniform(0, 2 * math.pi, h.size)
                new_perp = sp * np.sqrt(1 - mu**2)
                ox, oy = old_perp(h)
                kick(h, sp * mu, ox, oy, new_perp * np.cos(ph), new_perp * np.sin(ph))
        if cfg.beam_heating:
            inb = a[(np.hypot(gx[a], gy[a]) < cfg.beam_radius_m)]
            if inb.size:
                d = rng.normal(0.0, sig_heat, (inb.size, 3))
                ox, oy = old_perp(inb)
                kick(inb, vpar[inb] + d[:, 2], ox, oy, ox + d[:, 0], oy + d[:, 1])
        out_z = (z < zlo) | (z > zhi)
        out_r = np.hypot(gx, gy) >= cfg.pipe_radius_m
        newly_ax = alive & out_z
        newly_r = alive & out_r & ~out_z
        lost_axial |= newly_ax
        lost_radial |= newly_r
        alive &= ~(newly_ax | newly_r)

    return {"t_s": np.array(t_out), "surviving": np.array(surv), "mean_energy_eV": np.array(e_mean),
            "lost_axial": np.array(ax), "lost_radial": np.array(rad)}


def confinement_time_s(t_s: np.ndarray, surviving: np.ndarray) -> float:
    """tau from an exponential fit over the run; inf if nothing is lost, 0-like if all are lost early."""
    ok = surviving > 0
    if ok.sum() < 3:
        return float(t_s[np.argmax(surviving <= np.exp(-1))]) if np.any(surviving <= np.exp(-1)) else float("nan")
    if surviving[ok][-1] >= 1.0:
        return float("inf")
    slope = np.polyfit(t_s[ok], np.log(surviving[ok]), 1)[0]
    return float("inf") if slope >= 0 else -1.0 / slope
