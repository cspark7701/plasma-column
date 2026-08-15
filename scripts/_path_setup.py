"""
scripts/_path_setup.py

Authoritative path setup module for standalone scripts execution.
Ensures plasma_column package (src/) is on sys.path without boilerplate duplication.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Project root directory containing src/ and scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
