"""
tests/test_dataset_freeze.py

Unit tests for publication dataset freezing, SHA-256 cryptographic hashing, and manifest validation.
"""

import tempfile
import shutil
from pathlib import Path
import pytest

from plasma_column.warpx_io import compute_file_sha256, freeze_dataset


def test_compute_file_sha256():
    import hashlib

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as tmp:
        tmp.write("hello world\n")
        tmp_path = Path(tmp.name)

    try:
        sha = compute_file_sha256(tmp_path)
        expected = hashlib.sha256(b"hello world\n").hexdigest()
        assert sha == expected
    finally:
        tmp_path.unlink()


def test_compute_file_sha256_missing_raises():
    with pytest.raises(FileNotFoundError):
        compute_file_sha256(Path("non_existent_file.csv"))


def test_freeze_dataset_dry_run_and_write():
    src_dir = Path(tempfile.mkdtemp())
    out_dir = Path(tempfile.mkdtemp())

    try:
        # Create dummy csv files in src_dir
        (src_dir / "sample_a.csv").write_text("a,b,c\n1,2,3\n")
        (src_dir / "sample_b.csv").write_text("x,y,z\n4,5,6\n")

        # 1. Dry run
        manifest_dry = freeze_dataset(src_dir, out_dir, dry_run=True)
        assert len(manifest_dry["files"]) == 2
        assert "sample_a.csv" in manifest_dry["files"]
        assert "sample_b.csv" in manifest_dry["files"]
        assert not (out_dir / "sample_a.csv").exists()
        assert not (out_dir / "dataset_manifest.json").exists()

        # 2. Write mode
        manifest_write = freeze_dataset(src_dir, out_dir, dry_run=False)
        assert len(manifest_write["files"]) == 2
        assert (out_dir / "sample_a.csv").exists()
        assert (out_dir / "sample_b.csv").exists()
        assert (out_dir / "dataset_manifest.json").exists()

        # Check recorded sha256 matches actual file
        sha_a = compute_file_sha256(out_dir / "sample_a.csv")
        assert manifest_write["files"]["sample_a.csv"]["sha256"] == sha_a
    finally:
        shutil.rmtree(src_dir)
        shutil.rmtree(out_dir)


if __name__ == "__main__":
    pytest.main([__file__])
