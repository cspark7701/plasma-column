#!/usr/bin/env python3
"""
scripts/make_manuscript_study_results.py

Freezes the results of the confinement, transport and bunched-beam studies (tasks 107-121,
docs/physics_notes/simulation_strategy_tasks.md) into a small tracked dataset and generates the
corresponding number macros and figures of the journal manuscript
paper/manuscript/plasma_column_prab.tex. Every study number in the manuscript text comes from the
frozen dataset, so the text can be rebuilt without the simulation output.

Studies (task, source under results/):
    C1/C3  confinement_scan/analysis         tau_c and exit beam quality vs B_z, T_e, 5 mm plugs
    C4     plug_scan/analysis                plug voltage and width
    CW1    cw_best_config/analysis           best configuration on the production grid
    C2     trap_orbit_tracking               guiding-centre test electrons to 100 us
    CW2    transmission_vs_downstream        envelope transmission vs downstream compensation
    CW5    track_to_inflector                2D space-charge particle tracking
    CW3    line_section/analysis             electron retention in the solenoid and quadrupoles
    CW4    suppressor_scan                   suppressor voltage before the inflector
    B2     bunched_cell/analysis             bunched beam in the cell (PIC)
    B4     line_section_bunched/analysis     strongly bunched beam downstream (PIC)
    B3     late_bunching_layout              late bunching (ALTERNATIVE-PLACEMENT STUDY)
    B5/B6  sliced_bunch_transport            sliced-bunch transport, sine and sawtooth

Outputs (default --output_dir paper/manuscript):
    study_data/*.csv, study_data/provenance.json
    figures/fig9_confinement_times.{pdf,png}
    figures/fig10_transmission_downstream.{pdf,png}
    figures/fig11_bunched_gain.{pdf,png}
    numbers_studies.tex               LaTeX \\newcommand macros (\\numst...)

All PIC studies start from a seeded plasma (analytic source estimate, not self-consistent
proton-impact ionization). Buncher positions other than the cell entrance are an
ALTERNATIVE-PLACEMENT STUDY.

Usage:
    python scripts/make_manuscript_study_results.py --dry_run
    python scripts/make_manuscript_study_results.py                 # freeze from results/
    python scripts/make_manuscript_study_results.py --from_frozen   # rebuild from study_data/ only
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.design_estimates import compute_design_numbers
from plasma_column.plotting import save_figure, setup_publication_style
from plasma_column.warpx_io import get_git_info

# frozen name -> (source relative to results/, JSON key holding the table or None for a CSV)
SOURCES: dict[str, tuple[str, str | None]] = {
    "c1_confinement": ("confinement_scan/analysis/confinement_summary.csv", None),
    "c1_beam_quality": ("confinement_scan/analysis/beam_quality.csv", None),
    "c4_confinement": ("plug_scan/analysis/confinement_summary.csv", None),
    "c4_beam_quality": ("plug_scan/analysis/beam_quality.csv", None),
    "cw1_confinement": ("cw_best_config/analysis/confinement_summary.csv", None),
    "cw1_time_series": ("cw_best_config/analysis/confinement_time_series.csv", None),
    "cw1_beam_quality": ("cw_best_config/analysis/beam_quality.csv", None),
    "c2_trap": ("trap_orbit_tracking/trap_summary.csv", None),
    "cw2_transmission": ("transmission_vs_downstream/transmission_vs_downstream.csv", None),
    "cw5_tracking": ("track_to_inflector/track_summary.csv", None),
    "cw3_line_section": ("line_section/analysis/line_section_summary.csv", None),
    "cw4_suppressor": ("suppressor_scan/suppressor_scan.json", "needed"),
    "b2_bunched_cell": ("bunched_cell/analysis/bunched_cell_summary.csv", None),
    "b2_confinement": ("bunched_cell/analysis/confinement_summary.csv", None),
    "b4_line_section": ("line_section_bunched/analysis/line_section_summary.csv", None),
    "b4_bunched": ("line_section_bunched/analysis/bunched_cell_summary.csv", None),
    "b3_late_bunching": ("late_bunching_layout/late_bunching_layout.csv", None),
    "b5_sine": ("sliced_bunch_transport/sliced_bunch_sine.csv", None),
    "b6_sawtooth": ("sliced_bunch_transport/sliced_bunch_sawtooth.csv", None),
}
# Run records whose command line and commit go into the provenance.
PROVENANCE_JSON = ("transmission_vs_downstream/transmission_vs_downstream.json", "track_to_inflector/track_summary.json",
                   "trap_orbit_tracking/trap_summary.json", "suppressor_scan/suppressor_scan.json",
                   "late_bunching_layout/late_bunching_layout.json", "sliced_bunch_transport/sliced_bunch_sine.json",
                   "sliced_bunch_transport/sliced_bunch_sawtooth.json")

ETA_TARGET = 0.7      # downstream compensation needed for T >= 0.9 (CW2/CW5)
CW1_FROM_FRACTION = 0.5  # CW1 average over t >= this fraction of the run (as in analyze_confinement)
EMIT_REF = 0.25       # reference normalized edge emittance [pi mm mrad]
POSITIONS = ("baseline_cell_entrance", "drift3_Q1_Q2", "drift4_Q2_inflector")
POSITION_LABELS = ("cell entrance\n(baseline)", "between Q1 and Q2\n(alternative)", "Q2 to inflector\n(alternative)")
SERIES = ("#2a78d6", "#eb6834", "#1baf7a")  # validated categorical slots 1-3 (light surface)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Freeze the confinement/transport/bunching studies for the manuscript.")
    p.add_argument("--results_dir", type=Path, default=PROJECT_ROOT / "results")
    p.add_argument("--output_dir", type=Path, default=PROJECT_ROOT / "paper" / "manuscript")
    p.add_argument("--from_frozen", action="store_true",
                   help="Do not read results_dir; rebuild figures and macros from output_dir/study_data/.")
    p.add_argument("--dry_run", action="store_true", help="Collect and check data, print the macros; write nothing.")
    return p.parse_args()


# --------------------------------------------------------------------------- #
# Freezing
# --------------------------------------------------------------------------- #
def collect(results_dir: Path) -> dict[str, pd.DataFrame]:
    data = {}
    for name, (rel, key) in SOURCES.items():
        path = results_dir / rel
        if not path.exists():
            raise FileNotFoundError(f"{name}: missing {path}")
        data[name] = pd.DataFrame(json.loads(path.read_text())[key]) if key else pd.read_csv(path)
    return data


def load_frozen(data_dir: Path) -> dict[str, pd.DataFrame]:
    return {name: pd.read_csv(data_dir / f"{name}.csv") for name in SOURCES}


def collect_provenance(results_dir: Path) -> dict:
    runs = {}
    for rel in PROVENANCE_JSON:
        j = json.loads((results_dir / rel).read_text())
        runs[rel] = {k: j.get(k) for k in ("timestamp", "command_line", "plasma_column_repo")}
    for rel in ("cw_best_config/B0p15_Te1_V300_w10mm/metadata.json",):
        p = results_dir / rel
        if p.exists():
            j = json.loads(p.read_text())
            runs[rel] = {k: j.get(k) for k in ("timestamp", "command_line", "plasma_column_repo")}
    return {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command_line": " ".join(sys.argv),
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "plasma_column_repo": get_git_info(PROJECT_ROOT),
        "results_dir": str(results_dir),
        "sources": {name: rel for name, (rel, _) in SOURCES.items()},
        "runs": runs,
        "labels": "PIC studies: seeded plasma (analytic source estimate). Buncher positions other than the cell "
                  "entrance: ALTERNATIVE-PLACEMENT STUDY. B_f = 5 cell runs: bunch-focus study.",
    }


# --------------------------------------------------------------------------- #
# Numbers
# --------------------------------------------------------------------------- #
def _row(df: pd.DataFrame, col: str, value: str) -> pd.Series:
    sel = df[df[col] == value]
    if len(sel) != 1:
        raise KeyError(f"{col} == {value}: {len(sel)} rows")
    return sel.iloc[0]


def _crossing(x: np.ndarray, y: np.ndarray, level: float) -> float:
    """First x where y reaches level (linear interpolation), NaN if never."""
    for i in range(1, len(x)):
        if y[i - 1] < level <= y[i]:
            return float(x[i - 1] + (level - y[i - 1]) * (x[i] - x[i - 1]) / (y[i] - y[i - 1]))
    return float("nan")


def _f(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}"


def _sci(x: float) -> str:
    """One significant figure in LaTeX scientific notation."""
    e = math.floor(math.log10(abs(x)))
    m = round(x / 10**e)
    if m == 10:
        m, e = 1, e + 1
    return f"{m}\\times10^{{{e}}}" if m != 1 else f"10^{{{e}}}"


def build_macros(d: dict[str, pd.DataFrame]) -> tuple[dict[str, str], dict[str, float]]:
    dn = compute_design_numbers()
    tau_ion_us = dn["tau_h2_s"] * 1e6
    p_ref_torr = 1e-5
    m: dict[str, str] = {}
    raw: dict[str, float] = {"tau_ion_us": tau_ion_us}

    # C1: confinement scan (32x32x256, 650 ns)
    c1 = d["c1_confinement"].set_index("case_name")
    m["stCOtauBzero"] = _f(c1.loc["B0_Te1_plug0", "tau_c_fit_us"])
    m["stCOtauBhigh"] = _f(c1.loc["B0p15_Te1_plug0", "tau_c_fit_us"])
    ratios = [c1.loc[f"{b}_{t}_plug0", "tau_c_fit_us"] / c1.loc[f"{b}_{t}_plug300", "tau_c_fit_us"]
              for b in ("B0", "B0p05", "B0p15") for t in ("Te1", "Te10")]
    m["stCOplugratiomin"], m["stCOplugratiomax"] = _f(min(ratios), 1), _f(max(ratios), 1)
    m["stCOtend"] = _f(c1.loc["B0p15_Te1_plug0", "t_end_ns"], 0)
    # C3: exit beam quality with and without 5 mm, 300 V plugs (0.15 T, 1 eV)
    bq = d["c1_beam_quality"]
    ex = bq[bq.slab == "exit"].set_index("case_name")
    m["stCthreedivnoplug"] = _f(ex.loc["B0p15_Te1_plug0", "rp_rms_mrad"], 1)
    m["stCthreedivplug"] = _f(ex.loc["B0p15_Te1_plug300", "rp_rms_mrad"], 1)
    m["stCthreeremit"] = _f(ex.loc["B0p15_Te1_plug300", "eps_n_rms_mm_mrad"] / ex.loc["B0p15_Te1_plug0", "eps_n_rms_mm_mrad"], 1)
    m["stCthreerexit"] = _f(ex.loc["B0p15_Te1_plug0", "r_rms_mm"], 1)

    # C4: plug width and voltage (0.15 T, 1 eV)
    c4 = d["c4_confinement"].set_index("case_name")
    for key, case in (("stCFtaunoplug", "plug0"), ("stCFtauwfive", "V300_w5"), ("stCFtauwten", "V300_w10"),
                      ("stCFtauwtwenty", "V300_w20"), ("stCFtauVlow", "V100_w10")):
        m[key] = _f(c4.loc[case, "tau_c_fit_us"], 1)
    m["stCFetassmax"] = _f(c4.loc[["V300_w10", "V300_w20"], "eta_ss_lower_bound"].max())
    bq4 = d["c4_beam_quality"]
    ce = bq4[bq4.slab == "cell_end"].set_index("case_name")
    incr = [100 * (ce.loc[c, "rp_rms_mrad"] / ce.loc["plug0", "rp_rms_mrad"] - 1) for c in ("V300_w10", "V300_w20")]
    m["stCFdivincrmin"], m["stCFdivincrmax"] = _f(min(incr), 0), _f(max(incr), 0)

    # CW1: production grid
    cw = d["cw1_confinement"].iloc[0]
    ts = d["cw1_time_series"]
    t_from_ns = CW1_FROM_FRACTION * ts.time.max() * 1e9
    late = ts[ts.time * 1e9 >= t_from_ns - 1e-6]
    m["stCWeta"] = _f(late.eta_net_local.mean())
    m["stCWetamin"], m["stCWetamax"] = _f(late.eta_net_local.min()), _f(late.eta_net_local.max())
    m["stCWfromns"] = _f(round(t_from_ns, -1), 0)
    m["stCWtendns"] = _f(cw.t_end_ns, 0)
    m["stCWtauc"] = _f(cw.tau_c_fit_us, 1)
    m["stCWetass"] = _f(cw.tau_c_fit_us / tau_ion_us)
    bqw = d["cw1_beam_quality"].set_index("slab")
    m["stCWrexit"] = _f(bqw.loc["exit", "r_rms_mm"], 1)
    m["stCWdivexit"] = _f(bqw.loc["exit", "rp_rms_mrad"], 0)
    raw["cw1_tau_c_us"] = float(cw.tau_c_fit_us)

    # C2: test electrons in the static trap
    tr = d["c2_trap"]
    tr = tr[~tr.case.str.contains("dtcheck")]
    plugged, open_ = tr[tr.plug_voltage_V >= 100], tr[tr.plug_voltage_V == 0]
    m["stCtwotend"] = _f(plugged.t_end_us.max(), 0)
    m["stCtwosurvmin"] = _f(plugged.surviving_end.min(), 3)
    m["stCtwoopentaumin"], m["stCtwoopentaumax"] = _f(open_.tau_c_us.min(), 1), _f(open_.tau_c_us.max(), 1)
    m["stCtwoenergylow"] = _f(plugged[plugged.birth_temperature_eV == 1].mean_energy_end_eV.mean(), 0)
    m["stCtwoenergyhigh"] = _f(plugged[plugged.birth_temperature_eV == 10].mean_energy_end_eV.mean(), 0)
    m["stCtwowellmin"] = _f(tr.well_depth_V.min(), 0)

    # Steady state bracket from the particle balance dN_e/dt = N_p/tau_ion - N_e/tau_c
    m["stSStauion"] = _f(tau_ion_us, 0)
    m["stSSbuildpic"] = _f(3 * raw["cw1_tau_c_us"], 0)               # 95 % of eta_ss after 3 tau_c
    m["stSSbuildninety"] = _f(0.9 * tau_ion_us, 0)                   # eta = 0.9 for tau_c >> tau_ion
    m["stSStauneeded"] = _f(ETA_TARGET * tau_ion_us, 0)              # tau_c for eta_ss = 0.7 at p_ref

    # CW2: envelope transmission vs eta_down
    t2 = d["cw2_transmission"]
    ref = t2[np.isclose(t2.emittance_n_edge_pi_mm_mrad, EMIT_REF)].sort_values("eta_downstream")
    m["stCWtwoTzero"] = _f(ref.T_total.iloc[0])
    m["stCWtwoetahalf"] = _f(_crossing(ref.eta_downstream.values, ref.T_total.values, 0.5))
    m["stCWtwoetaninety"] = _f(_crossing(ref.eta_downstream.values, ref.T_total.values, 0.9))
    m["stCWtwoTmidemit"] = _f(t2[np.isclose(t2.emittance_n_edge_pi_mm_mrad, 0.5)].T_total.max())
    m["stCWtwoThighemit"] = _f(t2[np.isclose(t2.emittance_n_edge_pi_mm_mrad, 1.0)].T_total.max())
    raw["eta_down_for_T90"] = _crossing(ref.eta_downstream.values, ref.T_total.values, 0.9)

    # CW5: particle tracking
    t5 = d["cw5_tracking"]
    g = t5[(t5.beam == "gaussian") & np.isclose(t5.emittance_n_edge_pi_mm_mrad, EMIT_REF)].set_index("eta_downstream")
    m["stCWfiveGseven"], m["stCWfiveGnine"] = _f(g.loc[0.7, "T_total"]), _f(g.loc[0.9, "T_total"])
    kv = t5[(t5.beam == "kv") & np.isclose(t5.emittance_n_edge_pi_mm_mrad, EMIT_REF)]
    m["stCWfiveKVdev"] = _f((kv.T_total - kv.T_envelope).abs().iloc[1:].max())  # eta_down >= 0.5
    pic = t5[t5.beam == "cw1"]
    m["stCWfivepicmin"], m["stCWfivepicmax"] = _f(pic.T_total.min()), _f(pic.T_total.max())
    short = t5[t5.beam == "c1_short"].set_index("eta_downstream")
    m["stCWfiveshortnine"] = _f(short.loc[0.9, "T_total"])

    # CW3: line section retention (DC, seeded residual-gas plasma at the reference pressure)
    ls = d["cw3_line_section"]
    tau = ls.set_index(["case_name", "region"]).tau_c_us
    sol = [tau[("fields", "solenoid")], tau[("solenoid", "solenoid")]]
    quad = [tau[("fields", "Q1")], tau[("fields", "Q2")]]
    m["stCWthreesolmin"], m["stCWthreesolmax"] = _f(min(sol), 1), _f(max(sol), 1)
    m["stCWthreenofields"] = _f(tau[("nofields", "solenoid")])
    m["stCWthreequadmin"], m["stCWthreequadmax"] = _f(min(quad), 1), _f(max(quad), 1)
    m["stCWthreeetasolmin"], m["stCWthreeetasol"] = _f(min(sol) / tau_ion_us), _f(max(sol) / tau_ion_us)
    m["stCWthreeetaquad"] = _f(max(quad) / tau_ion_us, 3)
    m["stCWthreepsol"] = _sci(p_ref_torr * ETA_TARGET * tau_ion_us / min(sol))
    m["stCWthreepquad"] = _sci(p_ref_torr * ETA_TARGET * tau_ion_us / min(quad))

    # CW4: suppressor voltage for a 20 V barrier (V_inf = 1 kV)
    s4 = d["cw4_suppressor"]
    s4 = s4[np.isclose(s4.inflector_voltage_V, 1000.0)].set_index(["aperture_mm", "eta_down"])
    for ap, tag in ((5.0, "small"), (7.5, "large")):
        for eta, etag in ((0.5, "a"), (0.7, "b"), (0.9, "c")):
            m[f"stCWfourV{tag}{etag}"] = _f(s4.loc[(ap, eta), "V_s_needed_V"], 0)
    m["stCWfourfocalmin"] = _f(d["cw4_suppressor"].lens_focal_length_at_needed_m.min() / 1e3, 1)

    # B2: bunched beam in the cell (PIC, small grid)
    b2 = d["b2_bunched_cell"].set_index("case_name")
    b2c = d["b2_confinement"].set_index("case_name")
    for case, tag in (("trap_Bf1", "dc"), ("trap_Bf1p3", "base"), ("trap_Bf5", "focus"), ("open_Bf1p3", "open")):
        m[f"stBtwoeta{tag}"] = _f(b2.loc[case, "eta_avg_mean"])
        m[f"stBtwotau{tag}"] = _f(b2c.loc[case, "tau_c_fit_us"], 2 if b2c.loc[case, "tau_c_fit_us"] < 0.5 else 1)
    m["stBtwoBcell"] = _f(b2.loc["trap_Bf1p3", "bunching_factor_cell_mean"])
    m["stBtwopeakbase"] = _f(b2.loc["trap_Bf1p3", "eta_peak_mean"])
    m["stBtwopeakstd"] = _f(b2.loc["trap_Bf1p3", "eta_peak_std"])

    # B4: strongly bunched beam in the line section (PIC)
    b4 = d["b4_bunched"].set_index("case_name")
    b4t = d["b4_line_section"].set_index(["case_name", "region"]).tau_c_us
    for case, tag in (("fields_Bf3", "a"), ("fields_Bf5p7", "b")):
        m[f"stBfourpeak{tag}"] = _f(b4.loc[case, "eta_peak_mean"])
        m[f"stBfourstatic{tag}"] = _f(b4.loc[case, "static_cloud_eta_peak"])
        m[f"stBfourBcell{tag}"] = _f(b4.loc[case, "bunching_factor_cell_mean"], 1)
        m[f"stBfourtau{tag}"] = _f(b4t[(case, "solenoid")])

    # B3: late bunching (ALTERNATIVE-PLACEMENT STUDY beyond the cell entrance)
    b3 = d["b3_late_bunching"]
    base = b3[b3.position == "baseline_cell_entrance"]
    m["stBthreebasemin"], m["stBthreebasemax"] = _f(base.accepted_gain_vs_dc.min()), _f(base.accepted_gain_vs_dc.max())
    q = b3[(b3.position == "drift3_Q1_Q2") & np.isclose(b3.emittance_n_edge_pi_mm_mrad, EMIT_REF)]
    m["stBthreeqgain"] = _f(q.accepted_gain_vs_dc.max(), 1)
    m["stBthreeqV"] = _f(q.buncher_voltage_V.iloc[0] / 1e3, 2)
    late4 = b3[b3.position == "drift4_Q2_inflector"]
    m["stBthreelatemin"], m["stBthreelatemax"] = _f(late4.accepted_gain_vs_dc.min(), 1), _f(late4.accepted_gain_vs_dc.max(), 1)
    m["stBthreelateV"] = _f(late4.buncher_voltage_V.iloc[0] / 1e3, 1)

    # B5/B6: sliced-bunch transport, 0.25 pi mm mrad, gain G = sum f_s T_s / (window fraction * T_DC)
    for key, wf in (("Bfive", "b5_sine"), ("Bsix", "b6_sawtooth")):
        s = d[wf]
        s = s[np.isclose(s.emittance_n_edge_pi_mm_mrad, EMIT_REF)]
        for pos, ptag in zip(POSITIONS, ("base", "q", "late")):
            sp = s[s.position == pos]
            avg = sp[sp.compensation == "average"].set_index("eta_downstream").accepted_gain_vs_dc
            per = sp[sp.compensation == "per_slice"].set_index("eta_downstream").accepted_gain_vs_dc
            for eta, etag in ((0.0, "a"), (0.5, "b"), (0.9, "c")):
                m[f"st{key}G{ptag}{etag}"] = _f(avg.loc[eta], 3 if avg.loc[eta] < 0.01 else 2)
            m[f"st{key}bound{ptag}"] = _f(per.loc[0.9], 2 if per.loc[0.9] < 1 else 1)
            m[f"st{key}V{ptag}"] = _f(sp.buncher_voltage_V.iloc[0] / 1e3, 2 if sp.buncher_voltage_V.iloc[0] < 1e4 else 0)
            m[f"st{key}slice{ptag}"] = _f(sp.max_slice_factor.iloc[0], 0)
        m[f"st{key}Bf"] = _f(s[s.position == POSITIONS[0]].bf_window_inflector.iloc[0], 1)
    return m, raw


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def fig_confinement(d: dict[str, pd.DataFrame], raw: dict[str, float]) -> plt.Figure:
    c1 = d["c1_confinement"].set_index("case_name").tau_c_fit_us
    c4 = d["c4_confinement"].set_index("case_name").tau_c_fit_us
    ls = d["cw3_line_section"].set_index(["case_name", "region"]).tau_c_us
    b2 = d["b2_confinement"].set_index("case_name").tau_c_fit_us
    b4 = d["b4_line_section"].set_index(["case_name", "region"]).tau_c_us
    rows = [  # (label, tau_c [us], group)
        ("cell, 0 T", c1["B0_Te1_plug0"], "cell, DC"),
        ("cell, 0.15 T", c1["B0p15_Te1_plug0"], "cell, DC"),
        ("cell, 0.15 T, 5 mm plugs", c1["B0p15_Te1_plug300"], "cell, DC"),
        ("cell, 0.15 T, 10 mm plugs", c4["V300_w10"], "cell, DC"),
        ("cell, 0.15 T, 20 mm plugs", c4["V300_w20"], "cell, DC"),
        ("cell, production grid (CW1)", raw["cw1_tau_c_us"], "cell, DC"),
        ("cell trap, $B_f$ = 1.3", b2["trap_Bf1p3"], "bunched"),
        ("cell trap, $B_f$ = 5", b2["trap_Bf5"], "bunched"),
        ("main solenoid, DC", ls[("fields", "solenoid")], "line section"),
        ("Q1, DC", ls[("fields", "Q1")], "line section"),
        ("Q2, DC", ls[("fields", "Q2")], "line section"),
        ("main solenoid, $B_f$ = 3", b4[("fields_Bf3", "solenoid")], "bunched"),
        ("main solenoid, $B_f$ = 5.7", b4[("fields_Bf5p7", "solenoid")], "bunched"),
    ]
    colors = {"cell, DC": SERIES[0], "line section": SERIES[1], "bunched": SERIES[2]}
    fig, ax = plt.subplots(figsize=(3.6, 3.4))
    y = np.arange(len(rows))[::-1]
    for yi, (lab, t, grp) in zip(y, rows):
        ax.barh(yi, t, height=0.65, color=colors[grp], label=grp)
        ax.text(t * 1.1, yi, f"{t:.2g}", va="center", fontsize=6, color="0.25")
    ax.set_yticks(y, [r[0] for r in rows], fontsize=6.5)
    ax.tick_params(axis="x", labelsize=7)
    ax.set_xscale("log")
    ax.set_xlim(0.05, 200)
    need = ETA_TARGET * raw["tau_ion_us"]
    ax.axvline(need, color="0.3", ls="--", lw=1)
    ax.text(need * 0.92, y[-1] - 0.4, f"$\\tau_c$ for $\\eta_{{ss}}$ = {ETA_TARGET}\nat $10^{{-5}}$ Torr H$_2$",
            ha="right", va="bottom", fontsize=6, color="0.25")
    ax.set_xlabel(r"electron confinement time $\tau_c$ [$\mu$s]", fontsize=8)
    h, lab = ax.get_legend_handles_labels()
    uniq = dict(zip(lab, h))
    ax.legend([uniq[k] for k in colors], list(colors), fontsize=6, loc="upper right", frameon=False)
    ax.grid(axis="x", alpha=0.3, which="both", lw=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def fig_transmission(d: dict[str, pd.DataFrame]) -> plt.Figure:
    t2, t5 = d["cw2_transmission"], d["cw5_tracking"]
    fig, ax = plt.subplots(figsize=(4.6, 3.5))
    for c, (emit, marker) in zip(SERIES, ((0.25, "o"), (0.5, "s"), (1.0, "^"))):
        e = t2[np.isclose(t2.emittance_n_edge_pi_mm_mrad, emit)].sort_values("eta_downstream")
        ax.plot(e.eta_downstream, e.T_total, color=c, lw=2, label=f"envelope, {emit:g} $\\pi$ mm mrad")
        g = t5[(t5.beam == "gaussian") & np.isclose(t5.emittance_n_edge_pi_mm_mrad, emit)]
        if len(g):
            ax.plot(g.eta_downstream, g.T_total, ls="none", marker=marker, ms=6, mfc="white", mec=c, mew=1.5,
                    label=f"Gaussian tracking, {emit:g}")
    pic = t5[t5.beam == "cw1"]
    ax.plot(pic.eta_downstream, pic.T_total, ls="none", marker="D", ms=6, color="0.35", label="CW1 PIC beam, tracked")
    ax.set_xlabel(r"downstream compensation $\eta_{\rm down}$")
    ax.set_ylabel(r"transmission $T$ into inflector acceptance", fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.3, lw=0.5)
    ax.legend(fontsize=6.5, loc="upper left", frameon=False)
    fig.tight_layout()
    return fig


def fig_bunched_gain(d: dict[str, pd.DataFrame]) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.4), sharey=True)
    x = np.arange(len(POSITIONS))
    for ax, (name, title) in zip(axes, (("b5_sine", "(a) sine buncher"), ("b6_sawtooth", "(b) ideal sawtooth"))):
        s = d[name]
        s = s[np.isclose(s.emittance_n_edge_pi_mm_mrad, EMIT_REF)]
        for c, (eta, marker), dx in zip(SERIES, ((0.0, "o"), (0.5, "s"), (0.9, "^")), (-0.15, 0.0, 0.15)):
            av = [s[(s.position == p) & (s.compensation == "average") & np.isclose(s.eta_downstream, eta)]
                  .accepted_gain_vs_dc.iloc[0] for p in POSITIONS]
            ax.plot(x + dx, av, ls="none", marker=marker, ms=7, color=c, label=f"RF-averaged, $\\eta_{{\\rm down}}$ = {eta:g}")
        ub = [s[(s.position == p) & (s.compensation == "per_slice") & np.isclose(s.eta_downstream, 0.9)]
              .accepted_gain_vs_dc.iloc[0] for p in POSITIONS]
        ax.plot(x + 0.15, ub, ls="none", marker="_", ms=14, mew=2, color="0.3", label="per-slice bound, 0.9")
        ax.axhline(1.0, color="0.3", lw=0.8, ls=":")
        ax.set_xticks(x, POSITION_LABELS, fontsize=7)
        ax.set_title(title, fontsize=9)
        ax.set_yscale("log")
        ax.grid(axis="y", alpha=0.3, which="both", lw=0.5)
    axes[0].set_ylabel(r"accepted-current gain $G$ vs DC")
    axes[0].text(-0.4, 1.08, "DC beam", fontsize=7, color="0.3", ha="left", va="bottom")
    axes[1].legend(fontsize=6.5, loc="lower right", frameon=False)
    fig.tight_layout()
    return fig


def write_macros(macros: dict[str, str], path: Path) -> None:
    lines = ["% Auto-generated by scripts/make_manuscript_study_results.py -- do not edit by hand.",
             "% Values are study results frozen in paper/manuscript/study_data/."]
    lines += [f"\\newcommand{{\\num{k}}}{{\\ensuremath{{{v}}}}}" for k, v in macros.items()]
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    data_dir = args.output_dir / "study_data"
    data = load_frozen(data_dir) if args.from_frozen else collect(args.results_dir)
    macros, raw = build_macros(data)
    bad = [k for k in macros if not k.isalpha()]
    if bad:
        raise ValueError(f"macro names must be letters only: {bad}")
    if args.dry_run:
        for k, v in macros.items():
            print(f"  \\num{k} = {v}")
        print(f"[DRY RUN SUCCESS] {len(SOURCES)} tables, {len(macros)} macros; nothing written.")
        return 0
    if not args.from_frozen:
        data_dir.mkdir(parents=True, exist_ok=True)
        for name, df in data.items():
            df.to_csv(data_dir / f"{name}.csv", index=False, float_format="%.6g")
        (data_dir / "provenance.json").write_text(json.dumps(collect_provenance(args.results_dir), indent=2, default=str))
    setup_publication_style()
    fig_dir = args.output_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    for fig, name in ((fig_confinement(data, raw), "fig9_confinement_times"),
                      (fig_transmission(data), "fig10_transmission_downstream"),
                      (fig_bunched_gain(data), "fig11_bunched_gain")):
        save_figure(fig, fig_dir / name)
        plt.close(fig)
    write_macros(macros, args.output_dir / "numbers_studies.tex")
    print(f"Wrote {data_dir}/, {fig_dir}/fig9-11 and {args.output_dir}/numbers_studies.tex ({len(macros)} macros).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
