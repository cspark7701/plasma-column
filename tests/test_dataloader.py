"""
tests/test_dataloader.py

Unit tests for DataLoader diagnostic caching and mtime invalidation.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
import pandas as pd
import pytest

from plasma_column.diagnostics import DataLoader


def test_dataloader_caching(tmp_path: Path):
    DataLoader.clear_cache()
    assert DataLoader.cache_info()["cached_entries"] == 0

    # Create dummy diagnostic CSV
    csv_file = tmp_path / "local_neutralization.csv"
    csv_file.write_text("z,eta_net\n0.0,0.5\n0.1,0.8\n")

    # First load -> cache miss
    df1 = DataLoader.load_local_neutralization(csv_file)
    assert len(df1) == 2
    assert DataLoader.cache_info()["cached_entries"] == 1

    # Second load -> cache hit
    df2 = DataLoader.load_local_neutralization(csv_file)
    assert len(df2) == 2
    assert DataLoader.cache_info()["cached_entries"] == 1

    # Modify file -> cache invalidation
    time.sleep(0.01)
    csv_file.write_text("z,eta_net\n0.0,0.5\n0.1,0.8\n0.2,0.9\n")

    df3 = DataLoader.load_local_neutralization(csv_file)
    assert len(df3) == 3
    assert DataLoader.cache_info()["cached_entries"] == 2

    # Clear cache
    DataLoader.clear_cache()
    assert DataLoader.cache_info()["cached_entries"] == 0


def test_dataloader_metadata(tmp_path: Path):
    DataLoader.clear_cache()
    meta_file = tmp_path / "metadata.json"
    meta_file.write_text('{"case_name": "test_case", "value": 42}')

    meta1 = DataLoader.load_case_metadata(meta_file)
    assert meta1["case_name"] == "test_case"
    assert DataLoader.cache_info()["cached_entries"] == 1

    meta2 = DataLoader.load_case_metadata(meta_file)
    assert meta2["value"] == 42
