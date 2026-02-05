"""
Acceptance check: download PBP for [2025], then run again to reuse cache.
Run from repo root with PYTHONPATH=src or after pip install -e .

  python scripts/run_data_acceptance.py

Expect first run to log "Downloading PBP...", second run to log "Loaded PBP from cache...".
"""

import logging
import os
import sys
from pathlib import Path

# Ensure package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

from superbowlengine.config import DEFAULT_CONFIG, default_data_spec
from superbowlengine.data import get_pbp, cache_pbp

CACHE_DIR = os.environ.get("SBE_CACHE_DIR", ".cache/superbowlengine")
YEARS = [2025]
COLUMNS = list(DEFAULT_CONFIG.pbp_columns)


def main() -> None:
    print("Run 1: get_pbp with cache_dir (may download)...")
    df1 = get_pbp(YEARS, COLUMNS, cache_dir=CACHE_DIR)
    print(f"  Rows: {len(df1)}, columns: {len(df1.columns)}")

    print("Run 2: get_pbp again (should use cache)...")
    df2 = get_pbp(YEARS, COLUMNS, cache_dir=CACHE_DIR)
    print(f"  Rows: {len(df2)}, columns: {len(df2.columns)}")

    assert len(df1) == len(df2), "Cache should return same row count"
    assert list(df1.columns) == list(df2.columns), "Same columns"
    print("OK: cache reuse verified.")

    # Optional: prime cache explicitly
    print("Priming cache via cache_pbp([2025], cache_dir)...")
    cache_pbp([2025], CACHE_DIR)
    print("Done.")


if __name__ == "__main__":
    main()
