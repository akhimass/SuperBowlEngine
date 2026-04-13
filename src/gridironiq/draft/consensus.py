from __future__ import annotations

import csv
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .cfb_stats import normalize_person_name

logger = logging.getLogger(__name__)


@dataclass
class BoardRow:
    rank: int
    player_id: Optional[str] = None
    cfb_id: Optional[str] = None
    name: Optional[str] = None
    school: Optional[str] = None
    pos: Optional[str] = None
    source_file: str = ""


def _slug(name: Any, school: Any, pos: Any) -> str:
    import re

    raw = "|".join(str(x or "") for x in (name, pos, school))
    s = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return s or "unknown"


def consensus_directory() -> Optional[Path]:
    raw = os.getenv("GRIDIRONIQ_DRAFT_CONSENSUS_DIR") or os.getenv("DRAFT_CONSENSUS_DIR")
    if not raw:
        return None
    p = Path(raw).expanduser()
    return p if p.is_dir() else None


def _parse_json_board(path: Path) -> List[BoardRow]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    rows: List[BoardRow] = []
    if isinstance(data, dict):
        items = data.get("rankings") or data.get("players") or data.get("board") or []
    else:
        items = data
    if not isinstance(items, list):
        raise ValueError(f"{path}: expected JSON array or object with rankings/players")
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        r = int(it.get("rank") or it.get("overall") or it.get("position_rank") or (i + 1))
        rows.append(
            BoardRow(
                rank=r,
                player_id=str(it["player_id"]).strip() if it.get("player_id") else None,
                cfb_id=str(it["cfb_id"]).strip() if it.get("cfb_id") else None,
                name=str(it.get("name") or it.get("player_name") or "").strip() or None,
                school=str(it.get("school") or it.get("college") or "").strip() or None,
                pos=str(it.get("pos") or it.get("position") or "").strip() or None,
                source_file=str(path.name),
            )
        )
    return rows


def _parse_csv_board(path: Path) -> List[BoardRow]:
    rows: List[BoardRow] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for it in reader:
            rank_raw = (it.get("rank") or it.get("overall") or it.get("Rank") or "").strip()
            try:
                r = int(float(rank_raw))
            except ValueError:
                continue
            rows.append(
                BoardRow(
                    rank=r,
                    player_id=(it.get("player_id") or it.get("pfr_id") or "").strip() or None,
                    cfb_id=(it.get("cfb_id") or "").strip() or None,
                    name=(it.get("name") or it.get("player_name") or "").strip() or None,
                    school=(it.get("school") or it.get("college") or "").strip() or None,
                    pos=(it.get("pos") or it.get("position") or "").strip() or None,
                    source_file=str(path.name),
                )
            )
    return rows


def load_board_file(path: Path) -> List[BoardRow]:
    suf = path.suffix.lower()
    if suf == ".json":
        return _parse_json_board(path)
    if suf == ".csv":
        return _parse_csv_board(path)
    raise ValueError(f"Unsupported board format: {path}")


def discover_board_files(directory: Path) -> List[Path]:
    out: List[Path] = []
    for pat in ("*.json", "*.csv"):
        out.extend(sorted(directory.glob(pat)))
    return out


def build_prospect_lookup(prospects: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Map alternate keys -> gridiron player_id.
    """
    lu: Dict[str, str] = {}
    for p in prospects:
        pid = str(p.get("player_id") or "")
        if not pid:
            continue
        pfr = p.get("pfr_id")
        if pfr is not None and str(pfr).strip():
            lu[str(pfr).strip()] = pid
        cid = p.get("cfb_id")
        if cid is not None and str(cid).strip():
            lu[str(cid).strip()] = pid
        slug = _slug(p.get("player_name"), p.get("school"), p.get("pos"))
        lu[f"slug:{slug}"] = pid
        team = normalize_person_name(str(p.get("school") or ""))
        nm = normalize_person_name(str(p.get("player_name") or ""))
        if team and nm:
            lu[f"name:{team}|{nm}"] = pid
    return lu


def resolve_board_row(row: BoardRow, lookup: Dict[str, str]) -> Optional[str]:
    if row.player_id and row.player_id in lookup:
        return lookup[row.player_id]
    if row.cfb_id and row.cfb_id in lookup:
        return lookup[row.cfb_id]
    if row.name and row.school:
        k = f"name:{normalize_person_name(row.school)}|{normalize_person_name(row.name)}"
        if k in lookup:
            return lookup[k]
    slug = _slug(row.name, row.school, row.pos)
    k2 = f"slug:{slug}"
    if k2 in lookup:
        return lookup[k2]
    return None


def aggregate_market_consensus(
    prospects: List[Dict[str, Any]],
    *,
    extra_directories: Optional[List[str]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    Load all JSON/CSV boards from GRIDIRONIQ_DRAFT_CONSENSUS_DIR and optional extra dirs.
    Returns per gridiron player_id aggregates and meta (no fabricated ranks).
    """
    dirs: List[Path] = []
    d0 = consensus_directory()
    if d0:
        dirs.append(d0)
    if extra_directories:
        for x in extra_directories:
            p = Path(x).expanduser()
            if p.is_dir():
                dirs.append(p)

    if not dirs:
        return {}, {
            "consensus_configured": False,
            "note": "Set GRIDIRONIQ_DRAFT_CONSENSUS_DIR to a folder of real board JSON/CSV files.",
        }

    lookup = build_prospect_lookup(prospects)
    ranks_by_player: Dict[str, List[float]] = {}
    sources: List[str] = []
    unmatched: List[Dict[str, Any]] = []

    for d in dirs:
        for path in discover_board_files(d):
            try:
                board = load_board_file(path)
            except Exception as e:  # noqa: BLE001
                logger.warning("Skip board %s: %s", path, e)
                continue
            sources.append(path.name)
            for row in board:
                gid = resolve_board_row(row, lookup)
                if not gid:
                    unmatched.append(
                        {
                            "file": row.source_file,
                            "rank": row.rank,
                            "player_id": row.player_id,
                            "cfb_id": row.cfb_id,
                            "name": row.name,
                            "school": row.school,
                        }
                    )
                    continue
                ranks_by_player.setdefault(gid, []).append(float(row.rank))

    if not ranks_by_player:
        return {}, {
            "consensus_configured": True,
            "board_files": sources,
            "matched_players": 0,
            "note": "No board rows matched combine prospects — check IDs or name/school fields.",
            "unmatched_sample": unmatched[:40],
            "unmatched_count": len(unmatched),
        }

    n_boards = len(sources)
    out: Dict[str, Dict[str, Any]] = {}
    max_rank_observed = max(max(v) for v in ranks_by_player.values())

    for pid, ranks in ranks_by_player.items():
        import statistics

        avg = float(statistics.mean(ranks))
        var = float(statistics.pstdev(ranks)) if len(ranks) > 1 else 0.0
        med = float(statistics.median(ranks))
        # Market value: lower rank is better -> score 100 at rank 1
        mvs = max(0.0, min(100.0, 100.0 * (1.0 - (med - 1.0) / max(max_rank_observed, 1.0))))
        out[pid] = {
            "consensus_rank": round(med, 2),
            "avg_pick_position": round(avg, 2),
            "rank_variance": round(var, 3),
            "consensus_rank_std": round(var, 3),
            "board_count": len(ranks),
            "market_value_score": round(mvs, 2),
            "ranks_observed": [round(x, 2) for x in sorted(ranks)],
        }

    return out, {
        "consensus_configured": True,
        "board_files": sources,
        "directories": [str(d) for d in dirs],
        "matched_players": len(out),
        "board_file_count": n_boards,
        "unmatched_count": len(unmatched),
        "unmatched_sample": unmatched[:40],
    }


def compute_reach_risk(model_rank: int, consensus_rank: Optional[float]) -> Optional[float]:
    if consensus_rank is None:
        return None
    return round(float(model_rank) - float(consensus_rank), 2)


def build_simulation_board_order(
    prospects: List[Dict[str, Any]],
    market: Dict[str, Dict[str, Any]],
) -> List[str]:
    """
    Order for Monte Carlo: market consensus rank when present, then model prospect_score.
    """
    with_cons = [p for p in prospects if p["player_id"] in market]
    without = [p for p in prospects if p["player_id"] not in market]
    with_cons.sort(key=lambda p: (market[p["player_id"]]["consensus_rank"], -p["prospect_score"]))
    without.sort(key=lambda p: -p["prospect_score"])
    return [p["player_id"] for p in with_cons + without]
