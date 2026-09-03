"""
src/plasma_column/plotting/scan.py

Plotting pipeline routines for parameter scans, multi-case comparison bars,
heatmaps, small-multiple time-series grids, and gas-pressure sweeps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .neutralization import save_figure, setup_publication_style


def plot_keff_pressure_scan(
    scan_df: pd.DataFrame,
    output_dir: str | Path,
    output_name: str = "keff_pressure_scan",
    pressure_col: str = "pressure_torr",
    keff_col: str = "keff_over_k0",
    gas_col: Optional[str] = "gas",
    title: str = r"Effective Perveance vs Gas Pressure",
) -> tuple[Path, Path]:
    """Plot K_eff/K0 versus gas pressure from scan summary DataFrame."""
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(8, 5))

    GAS_STYLE: dict[str, dict] = {
        "H2": {"color": "tab:blue",   "marker": "o", "label": r"H$_2$"},
        "Kr": {"color": "tab:orange", "marker": "s", "label": "Kr"},
    }
    DEFAULT_STYLE = {"color": "tab:gray", "marker": "D", "label": "unknown"}

    if gas_col and gas_col in scan_df.columns:
        groups = scan_df.groupby(gas_col)
        for gas, gdf in groups:
            style = GAS_STYLE.get(str(gas), {**DEFAULT_STYLE, "label": str(gas)})
            gdf_s = gdf.sort_values(pressure_col)
            ax.semilogx(
                gdf_s[pressure_col], gdf_s[keff_col],
                marker=style["marker"], color=style["color"],
                label=style["label"], lw=2, markersize=7,
            )
    else:
        dfs = scan_df.sort_values(pressure_col)
        ax.semilogx(dfs[pressure_col], dfs[keff_col], marker="o", lw=2, markersize=7,
                    color="tab:blue", label="")

    ax.axhline(1.0, color="gray", lw=1, ls="--", label="No compensation")
    ax.axhline(0.0, color="black", lw=1, ls=":", label="Full compensation")
    ax.set_xlabel("Gas Pressure [Torr]", fontsize=12)
    ax.set_ylabel(r"Effective Perveance $K_\mathrm{eff}/K_0$", fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.set_ylim(-0.05, 1.15)
    ax.legend(fontsize=10)
    ax.grid(True, ls="--", alpha=0.5, which="both")

    out_basename = Path(output_dir) / output_name
    return save_figure(fig, out_basename)


def plot_scan_eta_vs_pressure(
    scan_df: pd.DataFrame,
    output_dir: str | Path,
    *,
    eta_col: str = "final_eta_net",
    title: str = r"Final Neutralisation $\eta$ vs Gas Pressure",
    output_name: str = "scan_eta_vs_pressure",
) -> tuple[Path, Path]:
    """Semi-log plot of final neutralisation η vs gas pressure."""
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(9, 5))

    group_col = "method" if "method" in scan_df.columns else "method_category"
    if group_col not in scan_df.columns:
        scan_df = scan_df.copy()
        scan_df[group_col] = "unknown"

    palette = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    markers = ["o", "s", "^", "D", "v", "P", "*", "X"]

    groups = scan_df.groupby(["gas", group_col])
    for idx, ((gas, method), grp) in enumerate(groups):
        grp = grp.sort_values("pressure_torr")
        col = palette[idx % len(palette)]
        mk  = markers[idx % len(markers)]
        label = f"{gas} — {method}"
        ax.semilogx(
            grp["pressure_torr"], grp[eta_col],
            marker=mk, lw=2, ms=7, color=col, label=label,
        )

    ax.axhline(1.0, color="gray", lw=1, ls=":", label="full compensation (η=1)")
    ax.axhline(0.0, color="gray", lw=0.8, ls="--", alpha=0.4)
    ax.set_xlabel("Gas pressure [Torr]", fontsize=12)
    ax.set_ylabel(r"Final $\eta_{\rm net}$", fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.legend(fontsize=9, loc="lower right")
    ax.set_ylim(-0.05, 1.15)
    ax.grid(True, which="both", ls="--", alpha=0.5)
    fig.tight_layout()

    out = Path(output_dir) / output_name
    return save_figure(fig, out)


def plot_scan_keff_vs_pressure(
    scan_df: pd.DataFrame,
    output_dir: str | Path,
    *,
    keff_col: str = "final_keff_over_k0",
    title: str = r"$K_{\rm eff}/K_0$ vs Gas Pressure — Method Comparison",
    output_name: str = "scan_keff_vs_pressure",
) -> tuple[Path, Path]:
    """Semi-log plot of final K_eff/K0 vs pressure for each (gas, method) group."""
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(9, 5))

    group_col = "method" if "method" in scan_df.columns else "method_category"
    if group_col not in scan_df.columns:
        scan_df = scan_df.copy()
        scan_df[group_col] = "unknown"

    palette = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    markers = ["o", "s", "^", "D", "v", "P", "*", "X"]

    groups = scan_df.groupby(["gas", group_col])
    for idx, ((gas, method), grp) in enumerate(groups):
        grp = grp.sort_values("pressure_torr")
        col = palette[idx % len(palette)]
        mk  = markers[idx % len(markers)]
        ax.semilogx(
            grp["pressure_torr"], grp[keff_col],
            marker=mk, lw=2, ms=7, color=col,
            label=f"{gas} — {method}",
        )

    ax.axhline(1.0, color="dimgray", lw=1.2, ls="--", label="no compensation ($K_{\\rm eff}=K_0$)")
    ax.axhline(0.0, color="seagreen", lw=1.2, ls="--", label="full compensation ($K_{\\rm eff}=0$)")
    ax.set_xlabel("Gas pressure [Torr]", fontsize=12)
    ax.set_ylabel(r"$K_{\rm eff}/K_0$", fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.legend(fontsize=9, loc="upper right")
    ax.set_ylim(-0.1, 1.2)
    ax.grid(True, which="both", ls="--", alpha=0.5)
    fig.tight_layout()

    out = Path(output_dir) / output_name
    return save_figure(fig, out)


def plot_scan_method_comparison_bar(
    scan_df: pd.DataFrame,
    output_dir: str | Path,
    *,
    metric_col: str = "final_keff_over_k0",
    ylabel: str = r"$K_{\rm eff}/K_0$",
    title: str = "Method Comparison — Final Effective Perveance",
    output_name: str = "scan_method_comparison_bar",
    reference_line: Optional[float] = 1.0,
) -> tuple[Path, Path]:
    """Grouped bar chart comparing a scalar metric across methods and gases."""
    setup_publication_style()
    fig, ax = plt.subplots(figsize=(max(8, len(scan_df) * 0.9), 5))

    gas_palette = {"H2": "tab:blue", "Kr": "tab:orange", "none": "tab:gray"}
    x_pos = np.arange(len(scan_df))
    colors = [gas_palette.get(g, "tab:purple") for g in scan_df.get("gas", ["unknown"] * len(scan_df))]

    bars = ax.bar(x_pos, scan_df[metric_col].fillna(0), color=colors,
                  edgecolor="black", linewidth=0.7, width=0.65)

    for bar, val in zip(bars, scan_df[metric_col].fillna(float("nan"))):
        if np.isfinite(val):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                    f"{val:.3f}", ha="center", va="bottom", fontsize=8.5)

    if reference_line is not None:
        ax.axhline(reference_line, color="dimgray", lw=1.2, ls="--",
                   label=f"reference ({ylabel} = {reference_line})")

    labels = scan_df.get("case_name", scan_df.index).tolist() if hasattr(scan_df.get("case_name", None), "tolist") else list(range(len(scan_df)))
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13)

    import matplotlib.patches as mpatches
    legend_patches = [mpatches.Patch(color=c, label=g)
                      for g, c in gas_palette.items() if g in scan_df.get("gas", pd.Series()).values]
    if reference_line is not None:
        import matplotlib.lines as mlines
        legend_patches.append(mlines.Line2D([], [], color="dimgray", ls="--",
                                            label=f"ref = {reference_line}"))
    ax.legend(handles=legend_patches, fontsize=9)
    ax.set_ylim(0, max(1.3, scan_df[metric_col].max() * 1.2 + 0.1))
    ax.grid(True, axis="y", ls="--", alpha=0.5)
    fig.tight_layout()

    out = Path(output_dir) / output_name
    return save_figure(fig, out)


def plot_scan_heatmap(
    scan_df: pd.DataFrame,
    output_dir: str | Path,
    *,
    row_col: str = "gas",
    col_col: str = "pressure_torr",
    value_col: str = "final_keff_over_k0",
    title: str = r"$K_{\rm eff}/K_0$ — Parameter Scan Heatmap",
    output_name: str = "scan_heatmap",
    cmap: str = "RdYlGn_r",
    fmt: str = ".3f",
) -> tuple[Path, Path]:
    """Heatmap (pivot table) of a scan metric."""
    setup_publication_style()
    pivot = scan_df.pivot_table(
        index=row_col, columns=col_col, values=value_col, aggfunc="mean"
    )

    fig, ax = plt.subplots(figsize=(max(6, len(pivot.columns) * 1.4), max(3, len(pivot) * 1.2)))
    im = ax.imshow(pivot.values, aspect="auto", cmap=cmap, vmin=0.0, vmax=1.0)
    plt.colorbar(im, ax=ax, label=value_col.replace("_", " "))

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(
        [f"{v:.1e}" if isinstance(v, float) else str(v) for v in pivot.columns],
        rotation=30, ha="right", fontsize=9,
    )
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=10)
    ax.set_xlabel(col_col.replace("_", " "), fontsize=11)
    ax.set_ylabel(row_col.replace("_", " "), fontsize=11)
    ax.set_title(title, fontsize=13)

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if np.isfinite(val):
                txt = f"{val:{fmt}}"
                text_color = "white" if val < 0.4 or val > 0.85 else "black"
                ax.text(j, i, txt, ha="center", va="center", fontsize=9, color=text_color)

    fig.tight_layout()
    out = Path(output_dir) / output_name
    return save_figure(fig, out)


def plot_scan_neutralization_timeseries_grid(
    cases: Sequence[tuple[str, pd.DataFrame]],
    output_dir: str | Path,
    *,
    eta_col: str = "eta_net",
    ncols: int = 3,
    output_name: str = "scan_timeseries_grid",
    title: str = "Neutralisation History — Scan Overview",
) -> tuple[Path, Path]:
    """Small-multiple grid of η(t) curves, one panel per scan case."""
    setup_publication_style()
    n     = len(cases)
    ncols = min(ncols, n)
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(4.5 * ncols, 3.2 * nrows),
        sharex=False, sharey=True,
        squeeze=False,
    )
    fig.suptitle(title, fontsize=13, y=1.01)

    for idx, (label, df) in enumerate(cases):
        row, col = divmod(idx, ncols)
        ax = axes[row][col]
        if eta_col in df.columns and "time" in df.columns:
            t_ns = df["time"].values * 1e9
            ax.plot(t_ns, df[eta_col].clip(0, 1), lw=1.8, color="tab:blue")
        ax.set_title(label, fontsize=8, pad=3)
        ax.set_ylim(-0.05, 1.1)
        ax.axhline(1.0, color="gray", lw=0.8, ls=":")
        ax.set_xlabel("Time [ns]", fontsize=8)
        ax.set_ylabel(r"$\eta_{\rm net}$", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, ls="--", alpha=0.4)

    for idx in range(n, nrows * ncols):
        row, col = divmod(idx, ncols)
        axes[row][col].set_visible(False)

    fig.tight_layout()
    out = Path(output_dir) / output_name
    return save_figure(fig, out)


def plot_scan_final_eta_bar_by_gas(
    scan_df: pd.DataFrame,
    output_dir: str | Path,
    *,
    eta_col: str = "final_eta_net",
    group_col: str = "method",
    title: str = "Final Neutralisation by Method and Gas",
    output_name: str = "scan_final_eta_bar",
) -> tuple[Path, Path]:
    """Grouped bar chart: one cluster per method, bars coloured by gas."""
    setup_publication_style()
    if group_col not in scan_df.columns:
        group_col = "method_category" if "method_category" in scan_df.columns else "case_name"

    methods = list(scan_df[group_col].unique())
    gases   = ["H2", "Kr"] if "gas" in scan_df.columns else [None]
    gas_palette = {"H2": "tab:blue", "Kr": "tab:orange", None: "tab:gray"}

    x = np.arange(len(methods))
    width = 0.35
    fig, ax = plt.subplots(figsize=(max(7, len(methods) * 1.5), 5))

    for g_idx, gas in enumerate(gases):
        if gas is not None:
            subset = scan_df[scan_df["gas"] == gas]
        else:
            subset = scan_df
        vals = [
            subset.loc[subset[group_col] == m, eta_col].mean()
            if m in subset[group_col].values else float("nan")
            for m in methods
        ]
        offset = (g_idx - len(gases) / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width,
                      color=gas_palette.get(gas, "tab:gray"),
                      label=gas if gas else "all",
                      edgecolor="black", linewidth=0.6)
        for bar, v in zip(bars, vals):
            if np.isfinite(v):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                        f"{v:.3f}", ha="center", va="bottom", fontsize=8)

    ax.axhline(1.0, color="gray", lw=1, ls="--", label="full compensation")
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=20, ha="right", fontsize=10)
    ax.set_ylabel(r"Final $\eta_{\rm net}$", fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.set_ylim(0, 1.3)
    ax.legend(fontsize=9)
    ax.grid(True, axis="y", ls="--", alpha=0.5)
    fig.tight_layout()

    out = Path(output_dir) / output_name
    return save_figure(fig, out)


__all__ = [
    "plot_keff_pressure_scan",
    "plot_scan_eta_vs_pressure",
    "plot_scan_keff_vs_pressure",
    "plot_scan_method_comparison_bar",
    "plot_scan_heatmap",
    "plot_scan_neutralization_timeseries_grid",
    "plot_scan_final_eta_bar_by_gas",
]
