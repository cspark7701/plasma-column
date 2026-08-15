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


if __name__ == "__main__":
    pytest.main([__file__])
