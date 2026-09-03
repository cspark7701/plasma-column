"""
tests/test_plotting.py

Unit tests for plotting pipeline helpers and manifest generation.
"""

import sys
from pathlib import Path
import tempfile
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

# Ensure project root and src/ are in sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from plasma_column.plotting import (
    save_figure,
    plot_particle_counts,
    plot_neutralization_evolution,
    plot_keff_over_k0,
    plot_beam_envelope_transport,
    plot_multi_case_beam_envelopes,
    plot_inflector_phase_space_comparison,
    plot_transmission_comparison_bar,
    plot_peak_keff_vs_bunching_factor,
    plot_bunch_length_vs_phase_width,
    plot_average_vs_peak_compensation,
    plot_analytic_vs_simulated_ionization_rate,
    generate_fig01_axial_injection_concept,
    generate_fig02_plasma_neutralizer_module,
    generate_fig03_cross_sections,
    generate_fig04_neutralization_evolution,
    generate_fig05_inflector_phase_space,
    write_plot_manifest,
)


def test_save_figure():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])

    with tempfile.TemporaryDirectory() as tmp_dir:
        base_path = Path(tmp_dir) / "test_fig"
        png_path, pdf_path = save_figure(fig, base_path)
        plt.close(fig)

        assert png_path.exists()
        assert pdf_path.exists()
        assert png_path.stat().st_size > 0
        assert pdf_path.stat().st_size > 0


def test_plot_manifest_writer():
    entries = [
        {
            "filename_png": "test.png",
            "filename_pdf": "test.pdf",
            "figure_title": "Test Title",
            "description": "Test description",
        }
    ]
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_csv = Path(tmp_dir) / "manifest.csv"
        written_path = write_plot_manifest(entries, out_csv)

        assert written_path.exists()
        df = pd.read_csv(written_path)
        assert len(df) == 1
        assert df.loc[0, "figure_title"] == "Test Title"


def test_notebook_utils_common_imports():
    """Verify COMMON_IMPORTS in notebook_utils defines distinct RESULTS_DIR and RUNS_DIR."""
    from plasma_column.notebook_utils import COMMON_IMPORTS

    joined = "".join(COMMON_IMPORTS)
    assert "RESULTS_DIR    = _ROOT / 'results'" in joined
    assert "RUNS_DIR       = _ROOT / 'runs'" in joined
    assert "PLOTS_DIR      = _ROOT / 'plots'" in joined


def test_plot_beam_envelope_transport_2d_and_schematic():
    """Verify plot_beam_envelope_transport handles DataFrame (Rx, Ry) and tuple inputs with schematic overlay."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        z = np.linspace(0.0, 1.12, 100)
        rx = 0.002 + 0.005 * z**2
        ry = 0.002 + 0.003 * z**2
        df = pd.DataFrame({"z": z, "Rx": rx, "Ry": ry})

        # Test with DataFrame and element schematic overlay
        png1, pdf1 = plot_beam_envelope_transport(df, tmp_dir, case_name="test_2d", show_elements=True)
        assert png1.exists() and pdf1.exists()
        assert png1.stat().st_size > 0
        assert pdf1.stat().st_size > 0

        # Test with tuple (z, rx, ry) without element schematic
        png2, pdf2 = plot_beam_envelope_transport((z, rx, ry), tmp_dir, case_name="test_tuple", show_elements=False)
        assert png2.exists() and pdf2.exists()
        assert png2.stat().st_size > 0
        assert pdf2.stat().st_size > 0


def test_paper_figure_generators():
    """Verify all 5 publication figure generators produce valid non-empty .png and .pdf files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        generators = [
            generate_fig01_axial_injection_concept,
            generate_fig02_plasma_neutralizer_module,
            generate_fig03_cross_sections,
            generate_fig04_neutralization_evolution,
            generate_fig05_inflector_phase_space,
        ]

        for gen in generators:
            png_p, pdf_p = gen(tmp_dir)
            assert png_p.exists()
            assert pdf_p.exists()
            assert png_p.stat().st_size > 1000  # Non-trivial image
            assert pdf_p.stat().st_size > 1000  # Non-trivial vector PDF
            plt.close("all")


def test_scan_plotting_module():
    """Verify all scan plotting routines work when imported from plotting.scan and plotting."""
    import plasma_column.plotting.scan as scan_mod
    from plasma_column.plotting import (
        plot_keff_pressure_scan,
        plot_scan_eta_vs_pressure,
        plot_scan_keff_vs_pressure,
        plot_scan_method_comparison_bar,
        plot_scan_heatmap,
        plot_scan_neutralization_timeseries_grid,
        plot_scan_final_eta_bar_by_gas,
    )

    # Test direct module exports
    for fn in [
        "plot_keff_pressure_scan",
        "plot_scan_eta_vs_pressure",
        "plot_scan_keff_vs_pressure",
        "plot_scan_method_comparison_bar",
        "plot_scan_heatmap",
        "plot_scan_neutralization_timeseries_grid",
        "plot_scan_final_eta_bar_by_gas",
    ]:
        assert hasattr(scan_mod, fn)

    # Create synthetic scan DataFrame
    df = pd.DataFrame({
        "case_name": ["h2_1e5", "h2_3e5", "kr_1e6", "kr_3e6"],
        "gas": ["H2", "H2", "Kr", "Kr"],
        "method": ["seeded", "seeded", "seeded", "seeded"],
        "pressure_torr": [1.0e-5, 3.0e-5, 1.0e-6, 3.0e-6],
        "final_eta_net": [0.85, 0.92, 0.88, 0.95],
        "final_keff_over_k0": [0.15, 0.08, 0.12, 0.05],
        "keff_over_k0": [0.15, 0.08, 0.12, 0.05],
    })

    with tempfile.TemporaryDirectory() as tmp_dir:
        p1, p2 = plot_keff_pressure_scan(df, tmp_dir)
        assert p1.exists() and p2.exists()

        p1, p2 = plot_scan_eta_vs_pressure(df, tmp_dir)
        assert p1.exists() and p2.exists()

        p1, p2 = plot_scan_keff_vs_pressure(df, tmp_dir)
        assert p1.exists() and p2.exists()

        p1, p2 = plot_scan_method_comparison_bar(df, tmp_dir)
        assert p1.exists() and p2.exists()

        p1, p2 = plot_scan_heatmap(df, tmp_dir)
        assert p1.exists() and p2.exists()

        p1, p2 = plot_scan_final_eta_bar_by_gas(df, tmp_dir)
        assert p1.exists() and p2.exists()

        # Test timeseries grid
        ts_df = pd.DataFrame({
            "time": np.linspace(0, 1e-8, 20),
            "eta_net": np.linspace(0, 0.9, 20),
        })
        cases = [("case_1", ts_df), ("case_2", ts_df)]
        p1, p2 = plot_scan_neutralization_timeseries_grid(cases, tmp_dir)
        assert p1.exists() and p2.exists()
        plt.close("all")


def test_transport_multi_case_and_phase_space_plots():
    """Verify plot_multi_case_beam_envelopes, plot_inflector_phase_space_comparison, and plot_transmission_comparison_bar."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        z = np.linspace(0.0, 1.12, 50)
        rx = 0.002 + 0.003 * z**2
        ry = 0.002 + 0.002 * z**2
        envelopes = {
            "vacuum": (z, rx, ry, "tab:blue"),
            "neutralized": (z, rx * 0.5, ry * 0.5, "tab:green"),
        }
        p1, p2 = plot_multi_case_beam_envelopes(envelopes, tmp_dir)
        assert p1.exists() and p2.exists()

        vac_df = pd.DataFrame({"x_mm": np.random.randn(20), "xp_mrad": np.random.randn(20),
                               "y_mm": np.random.randn(20), "yp_mrad": np.random.randn(20)})
        neut_df = pd.DataFrame({"x_mm": np.random.randn(20)*0.5, "xp_mrad": np.random.randn(20)*0.5,
                                "y_mm": np.random.randn(20)*0.5, "yp_mrad": np.random.randn(20)*0.5})

        p1, p2 = plot_inflector_phase_space_comparison(vac_df, neut_df, tmp_dir, plane="x")
        assert p1.exists() and p2.exists()

        p1, p2 = plot_inflector_phase_space_comparison(vac_df, neut_df, tmp_dir, plane="y")
        assert p1.exists() and p2.exists()

        summary_df = pd.DataFrame({
            "case_name": ["vacuum", "seeded_h2"],
            "transmission_percent": [45.2, 94.8],
        })
        p1, p2 = plot_transmission_comparison_bar(summary_df, tmp_dir)
        assert p1.exists() and p2.exists()
        plt.close("all")


def test_bunched_beam_plotting_helpers():
    """Verify plot_peak_keff_vs_bunching_factor, plot_bunch_length_vs_phase_width, and plot_average_vs_peak_compensation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        from plasma_column.beam import compute_bunched_beam_compensation_scan

        df_scan = compute_bunched_beam_compensation_scan(
            bunching_factors=[1.0, 2.0, 5.0],
            eta_avg_values=[0.50, 0.90],
        )

        p1, p2 = plot_peak_keff_vs_bunching_factor(df_scan, tmp_dir)
        assert p1.exists() and p2.exists()

        p1, p2 = plot_bunch_length_vs_phase_width(tmp_dir, energy_keV=30.0, rf_frequency_hz=50.0e6)
        assert p1.exists() and p2.exists()

        p1, p2 = plot_average_vs_peak_compensation(df_scan, tmp_dir, bunching_factor=5.0)
        assert p1.exists() and p2.exists()

        df_rate = pd.DataFrame({
            "time": np.linspace(0, 1e-9, 20),
            "Ne": np.linspace(0, 100, 20),
        })
        p1, p2 = plot_analytic_vs_simulated_ionization_rate(df_rate, tmp_dir)
        assert p1.exists() and p2.exists()
        plt.close("all")


if __name__ == "__main__":
    pytest.main([__file__])
