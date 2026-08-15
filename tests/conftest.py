"""
tests/conftest.py

Shared pytest fixtures for plasma column tests.
"""

from __future__ import annotations

import pytest
from plasma_column._testing import generate_synthetic_3d_grid


@pytest.fixture
def synthetic_3d_grid():
    """Provides a synthetic 3D spatial grid and density arrays for tests."""
    return generate_synthetic_3d_grid()
