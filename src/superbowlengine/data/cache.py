"""
Optional disk cache for PBP (manual use).

nflreadpy provides its own caching via env vars (NFLREADPY_CACHE, NFLREADPY_CACHE_DIR).
These helpers are for optional manual save/load of parquet (e.g. custom cache dir).
"""

import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _cache_path(years: List[int], cache_dir: str) -> Path:
    """Path to parquet file for this year set (sorted)."""
    base = Path(cache_dir)
    base.mkdir(parents=True, exist_ok=True)
    key = "_".join(str(y) for y in sorted(years))
    return base / f"pbp_{key}.parquet"


def read_cached_pbp(years: List[int], cache_dir: str) -> Optional[Path]:
    """Return path to cached parquet if it exists, else None."""
    path = _cache_path(years, cache_dir)
    if path.exists():
        logger.debug("Cache hit for years=%s at %s", years, path)
        return path
    logger.debug("Cache miss for years=%s", years)
    return None


def write_cached_pbp(pbp: pd.DataFrame, years: List[int], cache_dir: str) -> None:
    """Write PBP DataFrame to cache directory (parquet)."""
    path = _cache_path(years, cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    pbp.to_parquet(path, index=False)
    logger.info("Cached PBP for years=%s at %s (%d rows)", years, path, len(pbp))
