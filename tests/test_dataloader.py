"""
tests/test_dataloader.py

Unit tests for DataLoader thread-safety, concurrency, cache hit/miss semantics,
and mtime invalidation.
"""

import sys
import tempfile
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import pytest

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plasma_column.diagnostics import DataLoader, load_particle_number_diagnostic


def test_dataloader_cache_hit_and_invalidation():
    """Verify DataLoader caches content and invalidates when file mtime changes."""
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as tmp:
        tmp.write("# step time Np Ne Ni\n0 0.0 1000 0 0\n1 1e-9 1000 500 100\n")
        tmp_path = Path(tmp.name)

    try:
        # Initial load -> cache miss, entry added
        assert DataLoader.cache_info()["cached_entries"] == 0
        df1 = DataLoader.load_particle_number(tmp_path, use_cache=True)
        assert len(df1) == 2
        assert DataLoader.cache_info()["cached_entries"] == 1

        # Second load -> cache hit
        df2 = DataLoader.load_particle_number(tmp_path, use_cache=True)
        assert len(df2) == 2

        # Direct modification without cache -> no cache entry added
        DataLoader.clear_cache()
        df_no_cache = DataLoader.load_particle_number(tmp_path, use_cache=False)
        assert len(df_no_cache) == 2
        assert DataLoader.cache_info()["cached_entries"] == 0

        # Load with cache, then modify file with new mtime
        df_cached = DataLoader.load_particle_number(tmp_path, use_cache=True)
        assert DataLoader.cache_info()["cached_entries"] == 1

        # Small sleep to ensure mtime timestamp differs
        time.sleep(0.05)
        with open(tmp_path, "a", encoding="utf-8") as f:
            f.write("2 2e-9 1000 900 200\n")

        df_updated = DataLoader.load_particle_number(tmp_path, use_cache=True)
        assert len(df_updated) == 3
    finally:
        tmp_path.unlink()


def test_dataloader_metadata_caching():
    """Verify metadata.json caching and retrieval."""
    meta = {"case_name": "test_case", "method": "vacuum"}
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as tmp:
        json.dump(meta, tmp)
        tmp_path = Path(tmp.name)

    try:
        data1 = DataLoader.load_case_metadata(tmp_path, use_cache=True)
        assert data1["case_name"] == "test_case"
        assert DataLoader.cache_info()["cached_entries"] == 1

        data2 = DataLoader.load_case_metadata(tmp_path, use_cache=True)
        assert data2 == data1
    finally:
        tmp_path.unlink()


def test_dataloader_concurrent_access():
    """Verify concurrent thread reads/writes to DataLoader do not raise exceptions."""
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as tmp:
        tmp.write("# step time Np Ne Ni\n0 0.0 1000 0 0\n1 1e-9 1000 500 100\n")
        tmp_path = Path(tmp.name)

    try:
        def worker(_):
            df = DataLoader.load_particle_number(tmp_path, use_cache=True)
            return len(df)

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(worker, range(50)))

        assert all(r == 2 for r in results)
        assert DataLoader.cache_info()["cached_entries"] == 1
    finally:
        tmp_path.unlink()
