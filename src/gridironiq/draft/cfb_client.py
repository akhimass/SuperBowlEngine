from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CFBD_BASE = "https://api.collegefootballdata.com"


def cfbd_api_key() -> Optional[str]:
    return os.getenv("CFBD_API_KEY") or os.getenv("GRIDIRONIQ_CFBD_API_KEY")


def cfbd_get_json(path: str, params: Dict[str, Any], api_key: str, *, timeout: int = 90) -> Any:
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{CFBD_BASE}{path}?{q}" if q else f"{CFBD_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "GridironIQ/1.0",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_cfbd_team_conferences(year: int, api_key: str) -> Dict[str, str]:
    """
    Map CFBD school name -> conference name for a season (/teams).
    """
    try:
        data = cfbd_get_json("/teams", {"year": year}, api_key)
    except Exception:
        logger.exception("CFBD /teams fetch failed year=%s", year)
        raise
    if not isinstance(data, list):
        return {}
    out: Dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        school = row.get("school") or row.get("team")
        conf = row.get("conference")
        if school and conf:
            out[str(school)] = str(conf)
    return out


def fetch_player_season_stats_for_team(year: int, team: str, api_key: str) -> List[Dict[str, Any]]:
    """
    GET /stats/player/season — returns flat rows (one per statType/category/player).
    """
    try:
        data = cfbd_get_json(
            "/stats/player/season",
            {"year": year, "team": team, "seasonType": "regular"},
            api_key,
        )
    except urllib.error.HTTPError as e:
        if e.code in (400, 404):
            logger.warning("CFBD no stats for team=%s year=%s: %s", team, year, e)
            return []
        logger.exception("CFBD HTTP error team=%s year=%s", team, year)
        raise
    except Exception:
        logger.exception("CFBD request failed team=%s year=%s", team, year)
        raise
    if not isinstance(data, list):
        return []
    return data


def fetch_stats_for_schools(
    year: int,
    schools: List[str],
    api_key: str,
    *,
    max_workers: int = 8,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parallel fetch per CFBD `team` string. Key = school string attempted (for cache lookup).
    """
    uniq = []
    seen = set()
    for s in schools:
        t = (s or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        uniq.append(t)

    out: Dict[str, List[Dict[str, Any]]] = {}

    def job(team: str) -> tuple[str, List[Dict[str, Any]]]:
        rows = fetch_player_season_stats_for_team(year, team, api_key)
        return team, rows

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(job, t): t for t in uniq}
        for fut in as_completed(futs):
            team, rows = fut.result()
            out[team] = rows
    return out
