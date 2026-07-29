#!/usr/bin/env python3
"""
scripts/_gen_notebooks.py

Generates all production notebooks under:
  notebooks/runs/     — one per simulation case (vacuum, seeded H2/Kr, callback H2/Kr)
  notebooks/analysis/ — cross-cutting analysis notebooks

Run from project root:
    python scripts/_gen_notebooks.py
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
NB_RUNS     = ROOT / "notebooks" / "runs"
NB_ANALYSIS = ROOT / "notebooks" / "analysis"
NB_RUNS.mkdir(parents=True, exist_ok=True)
NB_ANALYSIS.mkdir(parents=True, exist_ok=True)

# ── cell factories ─────────────────────────────────────────────────────────────
def code(src):
    return {"cell_type": "code", "execution_count": None,
            "metadata": {}, "outputs": [], "source": src}

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src}

def notebook(cells):
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3 (warpx-dev)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.13.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

COMMON_IMPORTS = [
    "from pathlib import Path\n",
    "import os, sys, subprocess, time\n",
    "import numpy as np\n",
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "\n",
    "# Locate project root\n",
    "_ROOT = Path.cwd()\n",
    "while _ROOT.name != 'plasma_column' and _ROOT.parent != _ROOT:\n",
    "    _ROOT = _ROOT.parent\n",
    "if str(_ROOT / 'src') not in sys.path:\n",
    "    sys.path.insert(0, str(_ROOT / 'src'))\n",
    "\n",
    "WORK           = Path.home() / 'Work' / 'simulation_codes-working'\n",
    "WARPX_DATA_DIR = WORK / 'warpx-data'\n",
    "RUNS_DIR       = _ROOT / 'runs'\n",
    "PLOTS_DIR      = _ROOT / 'plots'\n",
    "RUNS_DIR.mkdir(exist_ok=True)\n",
    "PLOTS_DIR.mkdir(exist_ok=True)\n",
    "\n",
    "os.environ['WARPX_DATA_DIR']  = str(WARPX_DATA_DIR)\n",
    "os.environ['LD_LIBRARY_PATH'] = (\n",
    "    str(WORK / 'warpx' / 'install' / 'lib') + ':'\n",
    "    + os.environ.get('LD_LIBRARY_PATH', '')\n",
    ")\n",
    "print('Python :', sys.executable)\n",
    "print('ROOT   :', _ROOT)\n",
    "print('WarpX data:', WARPX_DATA_DIR)\n",
]

PLOT_IMPORTS = [
    "from plasma_column.plotting import (\n",
    "    setup_publication_style,\n",
    "    plot_multi_case_neutralization,\n",
    "    plot_neutralization_evolution,\n",
    "    plot_particle_counts,\n",
    "    plot_keff_over_k0,\n",
    "    plot_species_growth_rates,\n",
    "    plot_neutralization_panel,\n",
    "    plot_bunched_beam_keff,\n",
    "    plot_keff_pressure_scan,\n",
    "    plot_radial_density_profile,\n",
    "    plot_neutralization_vs_z,\n",
    "    plot_phase_space,\n",
    "    save_figure,\n",
    ")\n",
    "from plasma_column.diagnostics import (\n",
    "    load_particle_number_diagnostic,\n",
    "    compute_particle_number_metrics,\n",
    ")\n",
    "import warnings\n",
    "setup_publication_style()\n",
    "print('Plotting helpers loaded.')\n",
]

PHYS_CHECKS = [
    "## Physics checks (AGENTS.md)\n",
    "\n",
    "- [ ] Beam velocity consistent with 30 keV proton energy\n",
    "- [ ] Macroparticle weights are physically meaningful\n",
    "- [ ] Species ordering in ParticleNumber is correct\n",
    "- [ ] Ne and Ni increase for the correct physics reason\n",
    "- [ ] K_eff/K0 never negative unless labelled overcompensation\n",
    "- [ ] Beam envelope changes consistent with sign and magnitude of compensation\n",
    "- [ ] Gas pressure and interaction length acceptable\n",
]


def load_diag_cell(varname, case_dir_expr):
    return code([
        "import warnings\n",
        f"_OUT = {case_dir_expr}\n",
        "_diag_candidates = [\n",
        "    _OUT / 'reducedfiles' / 'ParticleNumber_red.txt',\n",
        "    _OUT / 'neutralization_from_particle_number.csv',\n",
        "]\n",
        "_diag = next((p for p in _diag_candidates if p.exists()), None)\n",
        "if _diag:\n",
        "    with warnings.catch_warnings():\n",
        "        warnings.simplefilter('ignore')\n",
        f"        {varname} = load_particle_number_diagnostic(_diag)\n",
        f"        {varname} = compute_particle_number_metrics({varname})\n",
        f"    print(f'Loaded {{len({varname})}} steps from {{_diag.name}}')\n",
        f"    display({varname}.tail())\n",
        "else:\n",
        "    print('No diagnostic file yet — run the simulation first.')\n",
        f"    {varname} = None\n",
    ])


def plot_diag_cell(varname, case_name):
    return code([
        f"if {varname} is not None:\n",
        f"    plot_neutralization_panel({varname}, PLOTS_DIR, case_name='{case_name}')\n",
        f"    plot_species_growth_rates({varname}, PLOTS_DIR,\n",
        f"                              case_name='{case_name}', smooth_window=7)\n",
        "    plot_bunched_beam_keff(\n",
        f"        {varname}['time'].values * 1e9,\n",
        f"        {varname}['eta_net'].values.clip(0, 1), PLOTS_DIR,\n",
        f"        case_name='{case_name}',\n",
        "        bunching_factors=[1.0, 2.0, 3.0, 5.0],\n",
        "    )\n",
        "    plt.show()\n",
        f"    print('Final eta_net   =', {varname}['eta_net'].iloc[-1])\n",
        f"    print('Final K_eff/K0  =', {varname}['keff_over_k0'].iloc[-1])\n",
    ])


def summary_cell(varname, case_name, gas, pressure):
    return code([
        f"if {varname} is not None:\n",
        "    row = {\n",
        f"        'case':          '{case_name}',\n",
        f"        'gas':           '{gas}',\n",
        f"        'pressure':      '{pressure} Torr',\n",
        f"        'n_steps':       len({varname}),\n",
        f"        'final_eta_e':   {varname}['eta_electron_only'].iloc[-1],\n",
        f"        'final_eta_net': {varname}['eta_net'].iloc[-1],\n",
        f"        'final_keff_K0': {varname}['keff_over_k0'].iloc[-1],\n",
        "    }\n",
        "    display(pd.DataFrame([row]))\n",
    ])


# ── vacuum reference ──────────────────────────────────────────────────────────
def make_vacuum_nb():
    cells = [
        md(["# Vacuum Reference Run\n", "\n",
            "Baseline run **without** a plasma neutralizer.\n",
            "Establishes unneutralized beam propagation and verifies K_eff/K0 ≈ 1.\n",
            "\n",
            "**Beamline**: `buncher → [plasma neutralizer] → solenoid → Q1 → Q2 → spiral inflector`\n",
            "\n",
            "> Tip: set `MAX_STEPS = 500` and `DIAG_PERIOD = 100` for a smoke test first.\n"]),
        code(COMMON_IMPORTS),
        code([
            "from plasma_column.notebook_utils import print_simulation_config\n",
            "SCRIPT = _ROOT / 'plasma_column_mcc_picmi_v7.py'\n",
            "_DEFAULTS = {\n",
            "    'script':               'plasma_column_mcc_picmi_v7.py',\n",
            "    'case':                 'vacuum_reference',\n",
            "    'gas':                  'H2',\n",
            "    'neutralization':       0.0,\n",
            "    'mcc':                  'none',\n",
            "    'pressure_torr':        '1e-5',\n",
            "    'plasma_age [s]':       '2e-4',\n",
            "    'max_steps':            120000,\n",
            "    'diag_period':          5000,\n",
            "    'reduced_diag_period':  100,\n",
            "    'nx / ny / nz':         '32 / 32 / 256',\n",
            "}\n",
            "_OVERRIDES = {}  # e.g. {'max_steps': 500, 'diag_period': 100}\n",
            "print_simulation_config(\n",
            "    notebook_title='Vacuum Reference Run',\n",
            "    defaults=_DEFAULTS, overrides=_OVERRIDES,\n",
            "    extra_info={'output root': str(RUNS_DIR / 'vacuum_reference')},\n",
            ")\n",
        ]),
        md(["## 1. Configure\n"]),
        code([
            "MAX_STEPS      = 120000   # reduce to 500 for smoke test\n",
            "DIAG_PERIOD    = 5000\n",
            "REDUCED_PERIOD = 100\n",
            "NX, NY, NZ     = 32, 32, 256\n",
            "OUT_DIR = RUNS_DIR / 'vacuum_reference'\n",
            "OUT_DIR.mkdir(parents=True, exist_ok=True)\n",
            "cmd = [\n",
            "    sys.executable, str(SCRIPT), '--run',\n",
            "    '--output_dir',          str(OUT_DIR),\n",
            "    '--gas',                 'H2',\n",
            "    '--neutralization',      '0.0',\n",
            "    '--mcc',                 'none',\n",
            "    '--pressure_torr',       '1e-5',\n",
            "    '--plasma_age',          '2e-4',\n",
            "    '--max_steps',           str(MAX_STEPS),\n",
            "    '--diag_period',         str(DIAG_PERIOD),\n",
            "    '--reduced_diag_period', str(REDUCED_PERIOD),\n",
            "    '--reduced_diag_dir',    'reducedfiles/',\n",
            "    '--nx', str(NX), '--ny', str(NY), '--nz', str(NZ),\n",
            "    '--warpx_data_dir',      str(WARPX_DATA_DIR),\n",
            "]\n",
            "print('Command:', ' '.join(cmd))\n",
        ]),
        md(["## 2. Run\n", "\n", "Uncomment `subprocess.run` to start the simulation.\n"]),
        code([
            "# result = subprocess.run(cmd, check=True)\n",
            "# print('Exit code:', result.returncode)\n",
            "print('Ready — uncomment subprocess.run to launch.')\n",
        ]),
        md(["## 3. Load diagnostics\n"]),
        code(PLOT_IMPORTS),
        load_diag_cell("df_vac", "RUNS_DIR / 'vacuum_reference'"),
        md(["## 4. Plots\n", "\n",
            "K_eff/K0 should remain ≈ 1.0 throughout (no compensation).\n"]),
        code([
            "if df_vac is not None:\n",
            "    plot_neutralization_panel(df_vac, PLOTS_DIR, case_name='vacuum_reference')\n",
            "    plot_keff_over_k0(df_vac, PLOTS_DIR, case_name='vacuum_reference')\n",
            "    plt.show()\n",
            "    print('Final K_eff/K0 =', df_vac['keff_over_k0'].iloc[-1])\n",
        ]),
        md(PHYS_CHECKS + ["- [ ] K_eff/K0 ≈ 1.0 (vacuum: no compensation)\n"]),
    ]
    p = NB_RUNS / "nb_vacuum_reference.ipynb"
    p.write_text(json.dumps(notebook(cells), indent=1, ensure_ascii=False))
    print("Written:", p)


# ── seeded run (H2 or Kr) ─────────────────────────────────────────────────────
def make_seeded_nb(gas, pressure, neutralization, fname):
    cn = f"seeded_{gas}"
    cells = [
        md([f"# Seeded Plasma-Column Full Transport — {gas}\n", "\n",
            f"Full-domain seeded neutralization run for **{gas}** at **{pressure} Torr**.\n",
            "\n",
            "> **Caution**: Analytic/data-driven seeded source estimate, not fully\n",
            "> self-consistent proton-impact MCC. Label all results accordingly.\n"]),
        code(COMMON_IMPORTS),
        code([
            "from plasma_column.notebook_utils import print_simulation_config\n",
            "SCRIPT = _ROOT / 'plasma_column_mcc_picmi_v7.py'\n",
            "_DEFAULTS = {\n",
            f"    'script':               'plasma_column_mcc_picmi_v7.py',\n",
            f"    'case':                 '{cn}',\n",
            f"    'gas':                  '{gas}',\n",
            f"    'neutralization':       {neutralization},\n",
            "    'mcc':                  'electron_impact',\n",
            f"    'pressure_torr':        '{pressure}',\n",
            "    'plasma_age [s]':       '2e-4',\n",
            "    'max_steps':            120000,\n",
            "    'diag_period':          5000,\n",
            "    'reduced_diag_period':  100,\n",
            "    'nx / ny / nz':         '32 / 32 / 256',\n",
            "}\n",
            "_OVERRIDES = {}  # e.g. {'max_steps': 500}\n",
            "print_simulation_config(\n",
            f"    notebook_title='Seeded Full Transport — {gas}',\n",
            "    defaults=_DEFAULTS, overrides=_OVERRIDES,\n",
            f"    extra_info={{'output root': str(RUNS_DIR / '{cn}')}},\n",
            ")\n",
        ]),
        md(["## 1. Configure\n"]),
        code([
            "MAX_STEPS      = 120000\n",
            "DIAG_PERIOD    = 5000\n",
            "REDUCED_PERIOD = 100\n",
            "NX, NY, NZ     = 32, 32, 256\n",
            f"OUT_DIR = RUNS_DIR / '{cn}'\n",
            "OUT_DIR.mkdir(parents=True, exist_ok=True)\n",
            "cmd = [\n",
            "    sys.executable, str(SCRIPT), '--run',\n",
            "    '--output_dir',          str(OUT_DIR),\n",
            f"    '--gas',                 '{gas}',\n",
            f"    '--neutralization',      '{neutralization}',\n",
            "    '--mcc',                 'electron_impact',\n",
            f"    '--pressure_torr',       '{pressure}',\n",
            "    '--plasma_age',          '2e-4',\n",
            "    '--max_steps',           str(MAX_STEPS),\n",
            "    '--diag_period',         str(DIAG_PERIOD),\n",
            "    '--reduced_diag_period', str(REDUCED_PERIOD),\n",
            "    '--reduced_diag_dir',    'reducedfiles/',\n",
            "    '--nx', str(NX), '--ny', str(NY), '--nz', str(NZ),\n",
            "    '--warpx_data_dir',      str(WARPX_DATA_DIR),\n",
            "]\n",
            "print('Command:', ' '.join(cmd))\n",
        ]),
        md(["## 2. Run\n"]),
        code(["# result = subprocess.run(cmd, check=True)\n",
              "print('Ready — uncomment subprocess.run to launch.')\n"]),
        md(["## 3. Load diagnostics\n"]),
        code(PLOT_IMPORTS),
        load_diag_cell("df_seeded", f"RUNS_DIR / '{cn}'"),
        md(["## 4. Diagnostic plots\n", "\n",
            "> eta should rise from seed value. K_eff/K0 should decrease.\n"]),
        plot_diag_cell("df_seeded", cn),
        md(PHYS_CHECKS + ["- [ ] Results labelled as analytic/seeded (not self-consistent MCC)\n"]),
        summary_cell("df_seeded", cn, gas, pressure),
    ]
    p = NB_RUNS / fname
    p.write_text(json.dumps(notebook(cells), indent=1, ensure_ascii=False))
    print("Written:", p)


# ── callback run (H2 or Kr) ───────────────────────────────────────────────────
def make_callback_nb(gas, pressure, fname):
    cn = f"callback_{gas}"
    cells = [
        md([f"# Python-Callback Proton-Impact Ionisation Source — {gas}\n", "\n",
            f"Full production run using the **Python callback** source model for **{gas}**.\n",
            "\n",
            "> **Limitation**: Data-driven source estimate — not self-consistent MCC.\n",
            "> Label results accordingly.\n"]),
        code(COMMON_IMPORTS),
        code([
            "from plasma_column.notebook_utils import print_simulation_config\n",
            "SCRIPT = _ROOT / 'plasma_column_callback_source_picmi_v3.py'\n",
            "_DEFAULTS = {\n",
            f"    'script':                'plasma_column_callback_source_picmi_v3.py',\n",
            f"    'case':                  '{cn}',\n",
            f"    'gas':                   '{gas}',\n",
            f"    'pressure_torr':         '{pressure}',\n",
            "    'max_steps':             20000,\n",
            "    'diag_period':           5000,\n",
            "    'reduced_diag_period':   100,\n",
            "    'nx / ny / nz':          '24 / 24 / 128',\n",
            "    'source_every_n_steps':  10,\n",
            "    'enable_ionization_source': 1,\n",
            "}\n",
            "_OVERRIDES = {}  # e.g. {'max_steps': 2000}\n",
            "print_simulation_config(\n",
            f"    notebook_title='Callback Source — {gas}',\n",
            "    defaults=_DEFAULTS, overrides=_OVERRIDES,\n",
            f"    extra_info={{'output root': str(RUNS_DIR / '{cn}')}},\n",
            ")\n",
        ]),
        md(["## 1. Configure\n"]),
        code([
            "MAX_STEPS      = 20000\n",
            "DIAG_PERIOD    = 5000\n",
            "REDUCED_PERIOD = 100\n",
            "NX, NY, NZ     = 24, 24, 128\n",
            f"OUT_DIR = RUNS_DIR / '{cn}'\n",
            "OUT_DIR.mkdir(parents=True, exist_ok=True)\n",
            "cmd = [\n",
            "    sys.executable, str(SCRIPT), '--run',\n",
            "    '--output_dir',             str(OUT_DIR),\n",
            f"    '--gas',                    '{gas}',\n",
            f"    '--pressure_torr',          '{pressure}',\n",
            "    '--max_steps',              str(MAX_STEPS),\n",
            "    '--diag_period',            str(DIAG_PERIOD),\n",
            "    '--reduced_diag_period',    str(REDUCED_PERIOD),\n",
            "    '--reduced_diag_dir',       'reducedfiles/',\n",
            "    '--nx', str(NX), '--ny', str(NY), '--nz', str(NZ),\n",
            "    '--source_every_n_steps',   '10',\n",
            "    '--enable_ionization_source','1',\n",
            "    '--warpx_data_dir',         str(WARPX_DATA_DIR),\n",
            "]\n",
            "print('Command:', ' '.join(cmd))\n",
        ]),
        md(["## 2. Run\n"]),
        code(["# result = subprocess.run(cmd, check=True)\n",
              "print('Ready — uncomment subprocess.run to launch.')\n"]),
        md(["## 3. Load diagnostics\n"]),
        code(PLOT_IMPORTS),
        load_diag_cell("df_cb", f"RUNS_DIR / '{cn}'"),
        md(["## 4. Diagnostic plots\n", "\n",
            "> **Pair-production check**: dNe/dt ≈ dNi/dt expected.\n"]),
        plot_diag_cell("df_cb", cn),
        md(PHYS_CHECKS + [
            "- [ ] dNe/dt ≈ dNi/dt (pair-production validation)\n",
            "- [ ] Cross-section at 30 keV correctly interpolated\n",
            "- [ ] Results labelled as callback/data-driven\n",
        ]),
        summary_cell("df_cb", cn, gas, pressure),
    ]
    p = NB_RUNS / fname
    p.write_text(json.dumps(notebook(cells), indent=1, ensure_ascii=False))
    print("Written:", p)


# ── nb_analysis_plots.ipynb ───────────────────────────────────────────────────
def make_analysis_plots_nb():
    cells = [
        md(["# Plasma-Column Analysis Plots\n", "\n",
            "Auto-discovers completed runs under `runs/`, loads diagnostics,\n",
            "and generates the full publication figure set.\n"]),
        code(COMMON_IMPORTS),
        code([
            "from plasma_column.notebook_utils import print_simulation_config\n",
            "_DEFAULTS = {\n",
            "    'runs root':               str(RUNS_DIR),\n",
            "    'figures root':            str(PLOTS_DIR),\n",
            "    'expected methods':        'vacuum, seeded, callback',\n",
            "    'output format':           'PNG (300 DPI) + PDF',\n",
            "    'beam energy [keV]':       30.0,\n",
            "    'beam current [mA]':       10.0,\n",
            "    'plasma cell length [m]':  0.20,\n",
            "    'inflector aperture [mm]': 5.0,\n",
            "}\n",
            "print_simulation_config(\n",
            "    notebook_title='Plasma-Column Analysis Plots',\n",
            "    defaults=_DEFAULTS, overrides={},\n",
            ")\n",
        ]),
        md(["## 1. Discover and load cases\n"]),
        code(PLOT_IMPORTS),
        code([
            "import warnings\n",
            "\n",
            "def _infer_meta(d):\n",
            "    n = d.name.lower()\n",
            "    return {\n",
            "        'case':   d.name,\n",
            "        'method': ('seeded'   if 'seeded'   in n else\n",
            "                   'callback' if 'callback' in n else\n",
            "                   'vacuum'   if 'vacuum'   in n else 'unknown'),\n",
            "        'gas':    'Kr' if 'kr' in n else 'H2',\n",
            "    }\n",
            "\n",
            "def _find_diag(d):\n",
            "    for p in [d / 'reducedfiles' / 'ParticleNumber_red.txt',\n",
            "               d / 'neutralization_from_particle_number.csv']:\n",
            "        if p.exists(): return p\n",
            "    return None\n",
            "\n",
            "cases = []\n",
            "for case_dir in sorted(RUNS_DIR.iterdir()):\n",
            "    if not case_dir.is_dir(): continue\n",
            "    diag = _find_diag(case_dir)\n",
            "    if diag is None: continue\n",
            "    meta = _infer_meta(case_dir)\n",
            "    with warnings.catch_warnings():\n",
            "        warnings.simplefilter('ignore')\n",
            "        hist = load_particle_number_diagnostic(diag)\n",
            "        hist = compute_particle_number_metrics(hist)\n",
            "    cases.append((case_dir, hist, meta))\n",
            "    print(f\"  {case_dir.name}  ({meta['method']} | {meta['gas']}) — {len(hist)} steps\")\n",
            "print(f'\\nTotal cases loaded: {len(cases)}')\n",
        ]),
        md(["## 2. Multi-case neutralisation overlay\n"]),
        code([
            "multi_pairs = [(f\"{m['case']} | {m['method']} | {m['gas']}\", h)\n",
            "               for _, h, m in cases]\n",
            "for col, ylabel, oname in [\n",
            "    ('eta_net',           r'$(N_e-N_i)/N_p$',   'all_eta_net'),\n",
            "    ('eta_electron_only', r'$N_e/N_p$',           'all_eta_electron'),\n",
            "    ('keff_over_k0',      r'$K_{\\rm eff}/K_0$',  'all_keff'),\n",
            "]:\n",
            "    if not any(col in h.columns for _, h, _ in cases): continue\n",
            "    p, _ = plot_multi_case_neutralization(\n",
            "        multi_pairs, PLOTS_DIR, column=col,\n",
            "        ylabel=ylabel, title=f'All cases — {ylabel}', output_name=oname,\n",
            "    )\n",
            "    print('Saved:', p.name)\n",
            "plt.show()\n",
        ]),
        md(["## 3. Per-case 3-panel summary\n"]),
        code([
            "for _, hist, meta in cases:\n",
            "    p, _ = plot_neutralization_panel(hist, PLOTS_DIR, case_name=meta['case'])\n",
            "    print('Saved:', p.name)\n",
            "plt.show()\n",
        ]),
        md(["## 4. Species growth rates\n"]),
        code([
            "for _, hist, meta in cases:\n",
            "    if not {'Ne','Ni'}.issubset(hist.columns): continue\n",
            "    p, _ = plot_species_growth_rates(hist, PLOTS_DIR,\n",
            "                                     case_name=meta['case'], smooth_window=7)\n",
            "    print('Saved:', p.name)\n",
            "plt.show()\n",
        ]),
        md(["## 5. Bunched-beam perveance\n"]),
        code([
            "for _, hist, meta in cases:\n",
            "    if 'eta_net' not in hist.columns: continue\n",
            "    p, _ = plot_bunched_beam_keff(\n",
            "        hist['time'].values * 1e9,\n",
            "        hist['eta_net'].values.clip(0, 1), PLOTS_DIR,\n",
            "        case_name=meta['case'],\n",
            "        bunching_factors=[1.0, 2.0, 3.0, 5.0, 8.0],\n",
            "    )\n",
            "    print('Saved:', p.name)\n",
            "plt.show()\n",
        ]),
        md(["## 6. Final-value summary table\n"]),
        code([
            "rows = []\n",
            "for _, hist, meta in cases:\n",
            "    row = dict(meta)\n",
            "    for col in ['eta_electron_only', 'eta_net', 'keff_over_k0']:\n",
            "        row[f'final_{col}'] = hist[col].iloc[-1] if col in hist.columns else float('nan')\n",
            "    row['n_steps'] = len(hist)\n",
            "    rows.append(row)\n",
            "display(pd.DataFrame(rows))\n",
        ]),
    ]
    p = NB_ANALYSIS / "nb_analysis_plots.ipynb"
    p.write_text(json.dumps(notebook(cells), indent=1, ensure_ascii=False))
    print("Written:", p)


# ── nb_bunched_beam_perveance.ipynb ───────────────────────────────────────────
def make_bb_perveance_nb():
    cells = [
        md(["# Bunched-Beam Effective Perveance Analysis\n", "\n",
            "$$K_{\\rm eff,peak}/K_0 \\approx 1 - \\bar{\\eta}/B_f$$\n", "\n",
            "Primary interpretation limit for any H2/Kr neutralisation result.\n"]),
        code(COMMON_IMPORTS),
        code([
            "from plasma_column.notebook_utils import print_simulation_config\n",
            "_DEFAULTS = {\n",
            "    'beam energy [keV]':       30.0,\n",
            "    'beam current [mA]':       10.0,\n",
            "    'bunching factors B_f':    '1, 2, 3, 5, 8',\n",
            "    'f_RF [MHz]':              72.0,\n",
            "    'bunch phase width [deg]': 30.0,\n",
            "}\n",
            "print_simulation_config(\n",
            "    notebook_title='Bunched-Beam Effective Perveance',\n",
            "    defaults=_DEFAULTS, overrides={},\n",
            ")\n",
        ]),
        md(["## 1. Beam parameters\n"]),
        code([
            "import math\n",
            "from plasma_column.beam import ProtonBeam\n",
            "from plasma_column.plotting import setup_publication_style, plot_bunched_beam_keff\n",
            "setup_publication_style()\n",
            "\n",
            "beam = ProtonBeam(energy_keV=30.0, current_mA=10.0, radius_m=2e-3)\n",
            "K0   = beam.perveance_K0\n",
            "B_f_values = [1.0, 2.0, 3.0, 5.0, 8.0]\n",
            "f_RF_MHz, phase_width_deg = 72.0, 30.0\n",
            "T_RF = 1.0 / (f_RF_MHz * 1e6)\n",
            "dt_b = (phase_width_deg / 360.0) * T_RF\n",
            "dz_b = beam.velocity * dt_b\n",
            "print(f'K0={K0:.4e}  beta={beam.beta:.6f}  v={beam.velocity:.4e} m/s')\n",
            "print(f'T_RF={T_RF*1e9:.3f} ns  dt_b={dt_b*1e9:.3f} ns  dz_b={dz_b*1e3:.2f} mm')\n",
        ]),
        md(["## 2. Load eta_avg(t) from first available run\n"]),
        code([
            "import warnings\n",
            "from plasma_column.diagnostics import load_particle_number_diagnostic, compute_particle_number_metrics\n",
            "\n",
            "_hist = None\n",
            "for _cd in sorted(RUNS_DIR.iterdir()):\n",
            "    for _p in [_cd / 'reducedfiles' / 'ParticleNumber_red.txt',\n",
            "                _cd / 'neutralization_from_particle_number.csv']:\n",
            "        if _p.exists():\n",
            "            with warnings.catch_warnings():\n",
            "                warnings.simplefilter('ignore')\n",
            "                _hist = compute_particle_number_metrics(\n",
            "                    load_particle_number_diagnostic(_p))\n",
            "            print(f'Using: {_cd.name} ({len(_hist)} steps)')\n",
            "            break\n",
            "    if _hist is not None: break\n",
            "\n",
            "if _hist is None:\n",
            "    print('No runs found — using synthetic ramp.')\n",
            "    _t_ns    = np.linspace(0, 400, 300)\n",
            "    _eta_avg = np.clip(np.linspace(0, 0.75, 300), 0, 1)\n",
            "else:\n",
            "    _t_ns    = _hist['time'].values * 1e9\n",
            "    _eta_avg = _hist['eta_net'].values.clip(0, 1)\n",
        ]),
        code([
            "p, _ = plot_bunched_beam_keff(\n",
            "    _t_ns, _eta_avg, PLOTS_DIR,\n",
            "    case_name='bunched_beam_analysis',\n",
            "    bunching_factors=B_f_values,\n",
            ")\n",
            "plt.show()\n",
            "print('Saved:', p.name)\n",
        ]),
        md(["## 3. Final K_eff,peak table\n"]),
        code([
            "eta_f = float(_eta_avg[-1])\n",
            "rows  = [{'B_f': Bf, 'eta_avg_final': eta_f,\n",
            "           'K_eff_peak_over_K0': max(0.0, 1.0 - eta_f / Bf)}\n",
            "          for Bf in B_f_values]\n",
            "display(pd.DataFrame(rows).set_index('B_f').style.format('{:.4f}'))\n",
        ]),
    ]
    p = NB_ANALYSIS / "nb_bunched_beam_perveance.ipynb"
    p.write_text(json.dumps(notebook(cells), indent=1, ensure_ascii=False))
    print("Written:", p)


# ── nb_cross_section_comparison.ipynb ────────────────────────────────────────
def make_xs_nb():
    cells = [
        md(["# H2 vs Kr Proton-Impact Ionisation Cross-Section Comparison\n", "\n",
            "Loads tabulated cross sections, plots sigma(E), and highlights the 30 keV point.\n"]),
        code(COMMON_IMPORTS),
        code([
            "from plasma_column.notebook_utils import print_simulation_config\n",
            "_DEFAULTS = {\n",
            "    'beam energy [keV]':   30.0,\n",
            "    'cross-section source':'warpx-data/MCC_cross_sections/',\n",
            "    'gases':               'H2, Kr',\n",
            "    'energy range [keV]':  '1 - 1000',\n",
            "}\n",
            "print_simulation_config(\n",
            "    notebook_title='H2 vs Kr Cross-Section Comparison',\n",
            "    defaults=_DEFAULTS, overrides={},\n",
            ")\n",
        ]),
        md(["## 1. Plot sigma(E)\n"]),
        code([
            "from plasma_column.gas import load_cross_section_table, get_h2_cross_section, get_kr_cross_section\n",
            "from plasma_column.plotting import setup_publication_style, save_figure\n",
            "setup_publication_style()\n",
            "\n",
            "BEAM_KEV = 30.0\n",
            "XS_ROOT  = WARPX_DATA_DIR / 'MCC_cross_sections'\n",
            "GAS_META = {\n",
            "    'H2': {'path': XS_ROOT / 'H2' / 'proton_impact_ionization.dat',\n",
            "           'color': 'tab:blue',   'label': r'H$_2$'},\n",
            "    'Kr': {'path': XS_ROOT / 'Kr' / 'proton_impact_ionization.dat',\n",
            "           'color': 'tab:orange', 'label': 'Kr'},\n",
            "}\n",
            "\n",
            "fig, ax = plt.subplots(figsize=(9, 5))\n",
            "for gas, meta in GAS_META.items():\n",
            "    if not meta['path'].exists():\n",
            "        print(f'{gas}: not found — {meta[\"path\"]}')\n",
            "        continue\n",
            "    df_xs = load_cross_section_table(meta['path'])\n",
            "    ax.loglog(df_xs.iloc[:,0] * 1e-3, df_xs.iloc[:,1],\n",
            "              color=meta['color'], lw=2, label=meta['label'])\n",
            "\n",
            "ax.axvline(BEAM_KEV, color='gray', lw=1.2, ls='--',\n",
            "           label=f'{BEAM_KEV:.0f} keV operating point')\n",
            "ax.set_xlabel('Proton kinetic energy [keV]', fontsize=12)\n",
            "ax.set_ylabel(r'Cross section [m$^2$]', fontsize=12)\n",
            "ax.set_title(r'Proton-impact ionisation: H$_2$ vs Kr', fontsize=13)\n",
            "ax.legend(fontsize=10)\n",
            "ax.grid(True, ls='--', alpha=0.5, which='both')\n",
            "p, _ = save_figure(fig, PLOTS_DIR / 'h2_kr_cross_sections')\n",
            "plt.show()\n",
            "print('Saved:', p.name)\n",
        ]),
        md(["## 2. Operating-point read-out\n"]),
        code([
            "s_h2 = get_h2_cross_section(BEAM_KEV)\n",
            "s_kr = get_kr_cross_section(BEAM_KEV)\n",
            "print(f'sigma(H2, {BEAM_KEV} keV) = {s_h2:.4e} m2')\n",
            "print(f'sigma(Kr, {BEAM_KEV} keV) = {s_kr:.4e} m2')\n",
            "print(f'Ratio sigma_Kr / sigma_H2  = {s_kr/s_h2:.2f}')\n",
        ]),
    ]
    p = NB_ANALYSIS / "nb_cross_section_comparison.ipynb"
    p.write_text(json.dumps(notebook(cells), indent=1, ensure_ascii=False))
    print("Written:", p)


# ── nb_local_neutralization_profiles.ipynb ───────────────────────────────────
def make_local_profiles_nb():
    cells = [
        md(["# Local Neutralisation Profiles — Radial and Axial\n", "\n",
            "Core-averaged density profiles and eta(z) from 3-D WarpX field arrays.\n", "\n",
            "> Global ParticleNumber ratios are necessary but **not sufficient** to claim\n",
            "> local space-charge compensation. This notebook provides spatial evidence.\n"]),
        code(COMMON_IMPORTS),
        code([
            "from plasma_column.notebook_utils import print_simulation_config\n",
            "_DEFAULTS = {\n",
            "    'plasma cell z-range [m]':  '0.00 - 0.20',\n",
            "    'beam-core radius [mm]':    2.0,\n",
            "    'r_max for profiles [mm]':  15.0,\n",
            "    'radial bins':              60,\n",
            "    'grid (synthetic)':         '31 x 31 x 50',\n",
            "    'eta_target (synthetic)':   0.70,\n",
            "}\n",
            "print_simulation_config(\n",
            "    notebook_title='Local Neutralisation Profiles',\n",
            "    defaults=_DEFAULTS, overrides={},\n",
            ")\n",
        ]),
        md(["## 1. 3-D density arrays (synthetic demo)\n", "\n",
            "Replace `ne_3d, ni_3d, np_3d, x, y, z` with arrays from a WarpX plotfile\n",
            "(e.g. via `yt`) for production use.\n"]),
        code([
            "from plasma_column.plotting import (\n",
            "    setup_publication_style, plot_radial_density_profile, plot_neutralization_vs_z,\n",
            ")\n",
            "from plasma_column.diagnostics import (\n",
            "    generate_synthetic_3d_grid,\n",
            "    compute_radial_density_profiles,\n",
            "    compute_local_neutralization_vs_z,\n",
            "    compute_local_core_neutralization,\n",
            ")\n",
            "setup_publication_style()\n",
            "\n",
            "ETA_TARGET = 0.70\n",
            "R_CORE_M   = 0.002\n",
            "\n",
            "ne_3d, ni_3d, np_3d, x, y, z = generate_synthetic_3d_grid(\n",
            "    nx=31, ny=31, nz=50, n_proton_peak=1e15, eta_target=ETA_TARGET,\n",
            ")\n",
            "print('Grid shape:', ne_3d.shape, '  z:', f'{z[0]:.3f} - {z[-1]:.3f} m')\n",
        ]),
        md(["## 2. Radial density profiles\n"]),
        code([
            "radial_df = compute_radial_density_profiles(\n",
            "    ne_3d, ni_3d, np_3d, x, y, z,\n",
            "    z_min_col=0.0, z_max_col=0.20, r_max=0.015, n_bins=60,\n",
            ")\n",
            "p, _ = plot_radial_density_profile(\n",
            "    radial_df, PLOTS_DIR,\n",
            "    case_name='local_profiles_demo', highlight_core_r=R_CORE_M,\n",
            ")\n",
            "plt.show()\n",
            "print('Saved:', p.name)\n",
            "display(radial_df.head())\n",
        ]),
        md(["## 3. Axial neutralisation profile eta(z)\n"]),
        code([
            "z_df = compute_local_neutralization_vs_z(\n",
            "    ne_3d, ni_3d, np_3d, x, y, z, r_core=R_CORE_M,\n",
            ")\n",
            "p, _ = plot_neutralization_vs_z(\n",
            "    z_df, PLOTS_DIR, case_name='local_profiles_demo', z_col_range=(0.0, 0.20),\n",
            ")\n",
            "plt.show()\n",
            "print('Saved:', p.name)\n",
            "display(z_df[['z','eta_electron_only_local_z','eta_net_local_z','keff_over_k0_local_z']].head(10))\n",
        ]),
        md(["## 4. Core-volume summary\n"]),
        code([
            "core = compute_local_core_neutralization(\n",
            "    ne_3d, ni_3d, np_3d, x, y, z,\n",
            "    z_min_col=0.0, z_max_col=0.20, r_core=R_CORE_M,\n",
            ")\n",
            "print('Core-averaged diagnostics:')\n",
            "for k, v in core.items():\n",
            "    print(f'  {k:<38} {v:.4g}')\n",
        ]),
    ]
    p = NB_ANALYSIS / "nb_local_neutralization_profiles.ipynb"
    p.write_text(json.dumps(notebook(cells), indent=1, ensure_ascii=False))
    print("Written:", p)


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    make_vacuum_nb()
    make_seeded_nb("H2", "1e-5", "0.5", "nb_seeded_h2.ipynb")
    make_seeded_nb("Kr", "1e-6", "0.5", "nb_seeded_kr.ipynb")
    make_callback_nb("H2", "1e-5", "nb_callback_h2.ipynb")
    make_callback_nb("Kr", "1e-6", "nb_callback_kr.ipynb")
    make_analysis_plots_nb()
    make_bb_perveance_nb()
    make_xs_nb()
    make_local_profiles_nb()
    print("\nAll notebooks written successfully.")
