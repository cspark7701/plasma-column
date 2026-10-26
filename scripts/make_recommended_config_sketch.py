#!/usr/bin/env python3
"""
scripts/make_recommended_config_sketch.py

Schematic of the recommended neutralizer configurations for a CW (DC) and an RF-bunched beam
(docs/physics_notes/neutralizer_efficiency_strategy.md, section 6). Not to scale.

The cell solenoid field and plug voltage are provisional until the confinement scan (task 107)
finishes. Bunched-beam numbers (B_f 1.3 -> 5.7, transmission 0.001-0.004 with cell-only
compensation) come from tasks 105 and 106; the seeded plasma is an analytic source
estimate.

Output (committed, small):
    docs/physics_notes/figures/recommended_configurations.{png,pdf}

Usage:
    python scripts/make_recommended_config_sketch.py --dry_run
    python scripts/make_recommended_config_sketch.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

try:
    from _path_setup import PROJECT_ROOT
except ImportError:
    from scripts._path_setup import PROJECT_ROOT

from plasma_column.plotting import save_figure

DEFAULT_OUT = PROJECT_ROOT / "docs" / "physics_notes" / "figures" / "recommended_configurations"

def elem(ax, x, w, h, color, label, y=0, fs=8, hatch=None, alpha=1):
    ax.add_patch(Rectangle((x, y - h/2), w, h, fc=color, ec="k", lw=1, hatch=hatch, alpha=alpha))
    ax.text(x + w/2, y - h/2 - 0.12, label, ha="center", va="top", fontsize=fs)


def row(ax, title, bunched):
    ax.set_xlim(-0.5, 12.6); ax.set_ylim(-2.3, 1.9); ax.axis("off")
    ax.set_title(title, fontsize=12, loc="left", fontweight="bold")
    ax.annotate("", xy=(12.4, 0), xytext=(-0.3, 0), arrowprops=dict(arrowstyle="-|>", color="crimson", lw=2))
    ax.text(-0.3, 0.12, "p$^+$ 30 keV, 10 mA", color="crimson", fontsize=8)
    elem(ax, 0.2, 0.6, 0.9, "0.75", "ion\nsource")
    if bunched:
        elem(ax, 1.2, 0.4, 0.8, "gold", "buncher\n(sawtooth/\nsine, 50 MHz)")
    # gas region
    gx0 = 1.9; gx1 = 11.0 if bunched else 5.6
    ax.add_patch(Rectangle((gx0, -0.75), gx1 - gx0, 1.5, fc="lightskyblue", ec="none", alpha=0.35))
    ax.text((gx0 + gx1)/2, 0.82, ("H$_2$ ~1e-5 Torr along the WHOLE line (cell + drifts + solenoid + quads)"
             if bunched else "H$_2$ 1e-5 Torr cell (20 cm)"), ha="center", fontsize=8, color="navy")
    # cell with solenoid coil + plugs
    cx, cw = 2.0, 3.4
    for yy in (0.55, -0.55):
        for k in range(10):
            ax.add_patch(Rectangle((cx + 0.15 + k*0.31, yy - 0.08), 0.22, 0.16, fc="peru", ec="k", lw=0.5))
    ax.text(cx + cw/2, 1.25, "cell solenoid 0.05-0.15 T\n(value from confinement scan)", ha="center", fontsize=8, color="saddlebrown")
    for px in (cx - 0.05, cx + cw - 0.05):
        ax.add_patch(Rectangle((px, -0.45), 0.1, 0.9, fc="mediumpurple", ec="k"))
    ax.text(cx - 0.05, -0.62, "-300 V\nplug", ha="center", va="top", fontsize=7, color="indigo")
    ax.text(cx + cw - 0.05, -0.62, "-300 V\nplug", ha="center", va="top", fontsize=7, color="indigo")
    ax.text(cx + cw/2, -0.35, "e$^-$ trapped:  radial by B,  axial by plugs", ha="center", fontsize=7.5, color="indigo")
    # main solenoid, quads, inflector
    elem(ax, 6.0, 1.3, 1.1, "orange", "main\nsolenoid")
    elem(ax, 7.9, 0.5, 0.9, "tab:green", "Q1")
    elem(ax, 8.8, 0.5, 0.9, "tab:green", "Q2")
    elem(ax, 11.1, 0.8, 1.1, "slategray", "spiral\ninflector")
    ax.add_patch(Rectangle((10.75, -0.5), 0.12, 1.0, fc="mediumpurple", ec="k"))
    ax.text(10.8, 0.62, "e$^-$ suppressor\n(-V)", ha="center", fontsize=7, color="indigo")
    if bunched:
        txt = ("Why: bunching factor rises 1.3 (cell) -> 5.7 (inflector); peak space charge is downstream.\n"
               "Compensation must exist where the beam is bunched; cell-only gives T ~ 0.001-0.004.\n"
               "Caveat: electrons compensate the RF-AVERAGE charge (tau_ion 80 us >> T_RF 20 ns):\n"
               "K_peak/K0,peak ~ 1 - eta_avg/B_f, so keep B_f low until the last drift (late bunching).")
    else:
        txt = ("Why: DC beam, steady state eta_ss ~ min(1, tau_c/tau_ion), tau_ion ~ 80 us.\n"
               "Cell B + plugs raise tau_c, keep eta -> 1 after the beam's own potential well vanishes.\n"
               "Gain in transmission is modest (T 0.17 -> 0.20) unless residual gas also compensates downstream.")
    ax.text(0.2, -1.55, txt, fontsize=8, va="top", family="monospace",
            bbox=dict(boxstyle="round", fc="whitesmoke", ec="0.6"))


def main() -> int:
    p = argparse.ArgumentParser(description="Draw the recommended CW and bunched-beam configurations.")
    p.add_argument("--output", type=Path, default=DEFAULT_OUT, help="Output basename (.png and .pdf).")
    p.add_argument("--dry_run", action="store_true", help="Print the output path; write nothing.")
    args = p.parse_args()
    if args.dry_run:
        print(f"Would write {args.output}.png/.pdf")
        print("[DRY RUN SUCCESS] nothing written.")
        return 0
    fig, axes = plt.subplots(2, 1, figsize=(13, 8.5))
    row(axes[0], "(a) CW / DC beam - recommended", bunched=False)
    row(axes[1], "(b) RF-bunched beam - recommended", bunched=True)
    fig.text(0.5, 0.005, "Schematic, not to scale. Plug voltage and cell B are provisional until the confinement "
             "scan (task 107) finishes; seeded plasma = analytic source estimate.", ha="center", fontsize=8,
             style="italic")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    png, pdf = save_figure(fig, args.output)
    plt.close(fig)
    print(f"Wrote {png} and {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
