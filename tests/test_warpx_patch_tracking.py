"""
tests/test_warpx_patch_tracking.py

Unit tests for WarpX patch tracking and metadata generation.
"""

import sys
from pathlib import Path
import pytest

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from plasma_column.warpx_io import get_git_info


def test_warpx_patch_file_exists():
    patch_file = project_root / "docs" / "warpx_patches" / "warpx_plasma_column_current.patch"
    assert patch_file.exists()
    assert patch_file.stat().st_size > 0


def test_warpx_git_tracking():
    warpx_dir = Path("/home/cspark/Work/simulation_codes-working/warpx")
    target_dir = warpx_dir if warpx_dir.is_dir() else project_root
    git_info = get_git_info(target_dir)

    assert "commit" in git_info
    assert "branch" in git_info
    assert "dirty" in git_info


if __name__ == "__main__":
    pytest.main([__file__])


def test_load_plotfile_densities_from_particles():
    from plasma_column.warpx_io import load_plotfile_densities
    test_plt = project_root / "results" / "callback_Kr_dynamic" / "diags" / "diag1002000"
    if not test_plt.exists():
        pytest.skip("Test plotfile not present in results/")

    data = load_plotfile_densities(test_plt)
    assert data is not None
    assert "ne_3d" in data
    assert "np_3d" in data
    assert "ni_3d" in data
    assert data["np_3d"].any()
    assert data["ne_3d"].any()
    assert data["ni_3d"].any()
