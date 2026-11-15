"""
src/plasma_column/bunching.py

Ballistic longitudinal bunching of a DC beam by an RF buncher, used to find the local bunching
factor along the axial injection line (buncher -> plasma neutralizer -> solenoid -> Q1 -> Q2 ->
spiral inflector).

Model (klystron-type ballistic drift, no space charge):
    a DC beam enters the buncher gap uniformly in RF phase phi = omega * t0;
    the gap adds a kinetic-energy modulation dE(phi) (sinusoidal, or ideal sawtooth);
    each particle then drifts at its own velocity: t(z) = t0 + z / v;
    its phase relative to the synchronous particle at z is psi = omega * (t(z) - z / v0).

The local bunching factor is defined with the cyclotron phase acceptance Delta_phi:
    B_f(z) = (largest beam fraction inside any Delta_phi window) / (Delta_phi / 360 deg),
so a DC beam has B_f = 1 and a beam fully inside the window has B_f = 360 deg / Delta_phi.
This is the average current inside the accepted phase window divided by I_avg, which is the
quantity used in K_eff,peak / K0,peak ~ 1 - eta_avg / B_f.

Limitations: no space charge (which opposes bunching at multi-mA), no transverse-longitudinal
coupling in the solenoid and quadrupoles, ideal thin buncher gap at z = 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from plasma_column.constants import C, MP, QE


@dataclass(frozen=True)
class BuncherModel:
    """RF buncher acting on a DC proton beam."""

    energy_keV: float = 30.0
    rf_frequency_hz: float = 50.0e6
    voltage_V: float = 750.0  # peak gap voltage (energy modulation amplitude e*V)
    waveform: str = "sine"  # "sine" or "sawtooth" (ideal linear ramp over one RF period)
    energy_spread_rms_eV: float = 5.0  # source energy spread (Gaussian)

    def __post_init__(self) -> None:
        if self.waveform not in ("sine", "sawtooth"):
            raise ValueError("waveform must be 'sine' or 'sawtooth'")


def proton_speed_m_s(kinetic_energy_eV: np.ndarray | float) -> np.ndarray | float:
    gamma = 1.0 + np.asarray(kinetic_energy_eV) * QE / (MP * C**2)
    return C * np.sqrt(1.0 - 1.0 / gamma**2)


def sample_bunched_beam(buncher: BuncherModel, n_particles: int = 200_000, seed: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Entrance phases phi in [-pi, pi) (uniform, DC beam) and kinetic energies after the gap [eV]."""
    rng = np.random.default_rng(seed)
    phi = rng.uniform(-math.pi, math.pi, n_particles)
    if buncher.waveform == "sine":
        modulation = np.sin(phi)
    else:
        modulation = phi / math.pi
    energy_eV = (buncher.energy_keV * 1e3 + buncher.voltage_V * modulation
                 + rng.normal(0.0, buncher.energy_spread_rms_eV, n_particles))
    return phi, energy_eV


def phases_at(z_m: float, phi: np.ndarray, energy_eV: np.ndarray, buncher: BuncherModel) -> np.ndarray:
    """RF phase psi in [-pi, pi) of each particle at position z, relative to the synchronous particle."""
    omega = 2.0 * math.pi * buncher.rf_frequency_hz
    v0 = proton_speed_m_s(buncher.energy_keV * 1e3)
    psi = phi + omega * z_m * (1.0 / proton_speed_m_s(energy_eV) - 1.0 / v0)
    return (psi + math.pi) % (2.0 * math.pi) - math.pi


def window_bunching_factor(psi: np.ndarray, acceptance_deg: float = 36.0, bin_deg: float = 0.5) -> tuple[float, float]:
    """
    B_f inside the best acceptance window, and the window centre [deg].

    Returns (B_f, centre_deg) with B_f = max window fraction / (acceptance_deg / 360).
    """
    nbins = int(round(360.0 / bin_deg))
    hist, edges = np.histogram(np.degrees(psi), bins=nbins, range=(-180.0, 180.0))
    w = int(round(acceptance_deg / bin_deg))
    wrapped = np.concatenate([hist, hist[: w - 1]])
    sums = np.convolve(wrapped, np.ones(w, dtype=int), mode="valid")[:nbins]
    i = int(np.argmax(sums))
    centre = edges[i] + 0.5 * acceptance_deg
    centre = (centre + 180.0) % 360.0 - 180.0
    return float(sums[i] / psi.size / (acceptance_deg / 360.0)), float(centre)


def peak_current_ratio(psi: np.ndarray, bin_deg: float = 2.0) -> float:
    """I_peak / I_avg from a phase histogram with ``bin_deg`` resolution (resolution dependent near a caustic)."""
    nbins = int(round(360.0 / bin_deg))
    hist, _ = np.histogram(np.degrees(psi), bins=nbins, range=(-180.0, 180.0))
    return float(hist.max() / hist.mean())


def optimal_voltage_V(
    focus_z_m: float,
    buncher: BuncherModel,
    acceptance_deg: float = 36.0,
    v_min: float = 50.0,
    v_max: float = 5000.0,
    n_particles: int = 100_000,
) -> float:
    """Gap voltage that maximizes the window bunching factor at ``focus_z_m`` (grid scan, then refinement)."""

    def score(volt: float) -> float:
        b = BuncherModel(buncher.energy_keV, buncher.rf_frequency_hz, volt, buncher.waveform, buncher.energy_spread_rms_eV)
        phi, e = sample_bunched_beam(b, n_particles)
        return window_bunching_factor(phases_at(focus_z_m, phi, e, b), acceptance_deg)[0]

    grid = np.geomspace(v_min, v_max, 60)
    best = grid[int(np.argmax([score(v) for v in grid]))]
    fine = np.linspace(0.8 * best, 1.2 * best, 41)
    return float(fine[int(np.argmax([score(v) for v in fine]))])


def bunching_along_line(
    z_m: np.ndarray,
    buncher: BuncherModel,
    acceptance_deg: float = 36.0,
    n_particles: int = 200_000,
) -> dict[str, np.ndarray]:
    """Window bunching factor, window centre and 2-deg peak current ratio at each z."""
    phi, e = sample_bunched_beam(buncher, n_particles)
    bf, centre, peak = [], [], []
    for z in z_m:
        psi = phases_at(float(z), phi, e, buncher)
        b, c = window_bunching_factor(psi, acceptance_deg)
        bf.append(b)
        centre.append(c)
        peak.append(peak_current_ratio(psi))
    return {"z_m": np.asarray(z_m, float), "bunching_factor": np.asarray(bf),
            "window_centre_deg": np.asarray(centre), "peak_current_ratio_2deg": np.asarray(peak)}


def bunching_with_buncher_at(
    z_m: np.ndarray,
    buncher_z_m: float,
    buncher: BuncherModel,
    acceptance_deg: float = 36.0,
    n_particles: int = 100_000,
) -> np.ndarray:
    """
    Window bunching factor along the line for a buncher gap at ``buncher_z_m`` (B_f = 1 upstream of
    it, ballistic bunching downstream). A buncher anywhere but upstream of the neutralizer is an
    alternative-placement study (baseline: buncher -> neutralizer -> solenoid -> Q1 -> Q2 -> inflector).
    """
    z = np.asarray(z_m, float)
    bf = np.ones_like(z)
    down = z >= buncher_z_m
    if np.any(down):
        bf[down] = np.maximum(
            bunching_along_line(z[down] - buncher_z_m, buncher, acceptance_deg, n_particles)["bunching_factor"], 1.0)
    return bf


def slice_bunching_along_line(
    z_m: np.ndarray,
    buncher_z_m: float,
    buncher: BuncherModel,
    focus_z_m: float,
    acceptance_deg: float = 36.0,
    n_slices: int = 9,
    n_particles: int = 200_000,
) -> dict[str, np.ndarray]:
    """
    Local current factor along the line of each longitudinal slice of the accepted bunch (task B5).

    The accepted bunch is the best ``acceptance_deg`` phase window at ``focus_z_m`` (the inflector),
    split into ``n_slices`` equal phase slices. A slice is followed back along the line by the
    circular mean phase of its particles; its local current factor at z is the beam fraction within
    +- half a slice width of that phase, divided by (slice width / 360 deg), so it is 1 for a DC beam
    and upstream of the buncher. Returns the slice centres at the focus [deg], the beam fraction in
    each slice, the local factors (n_slices, len(z)) and the window bunching factor at the focus.
    """
    z = np.asarray(z_m, float)
    phi, e = sample_bunched_beam(buncher, n_particles)
    psi_f = phases_at(focus_z_m - buncher_z_m, phi, e, buncher)
    bf_window, centre = window_bunching_factor(psi_f, acceptance_deg)
    width = math.radians(acceptance_deg / n_slices)
    rel_f = (psi_f - math.radians(centre) + math.pi) % (2.0 * math.pi) - math.pi
    edges = math.radians(-0.5 * acceptance_deg) + width * np.arange(n_slices + 1)
    labels = np.digitize(rel_f, edges) - 1
    factors = np.ones((n_slices, z.size))
    for j, zj in enumerate(z):
        if zj < buncher_z_m:
            continue
        psi = phases_at(zj - buncher_z_m, phi, e, buncher)
        for s in range(n_slices):
            sel = labels == s
            if not np.any(sel):
                factors[s, j] = 0.0
                continue
            mean = math.atan2(np.mean(np.sin(psi[sel])), np.mean(np.cos(psi[sel])))
            d = (psi - mean + math.pi) % (2.0 * math.pi) - math.pi
            factors[s, j] = np.mean(np.abs(d) < 0.5 * width) / (width / (2.0 * math.pi))
    frac = np.array([np.mean(labels == s) for s in range(n_slices)])
    return {"z_m": z, "slice_centre_deg": centre + np.degrees(0.5 * (edges[:-1] + edges[1:])),
            "slice_fraction": frac, "slice_factor": factors, "bf_window": bf_window}
