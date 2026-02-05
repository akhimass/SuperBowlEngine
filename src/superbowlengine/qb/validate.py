"""
Strict data validation for QB extraction: ensure we use correct postseason games and QB plays.

Schedules are ground truth for team postseason games; PBP is cross-checked for QB involvement.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


def _qb_name_matches(pbp_name: str, qb: str) -> bool:
    """True if pbp_name matches qb: exact (strip/upper) or any token of qb appears in pbp_name."""
    if pd.isna(pbp_name) or str(pbp_name).strip() == "":
        return False
    a = str(pbp_name).strip().upper()
    b = str(qb).strip().upper()
    if a == b:
        return True
    # Token match: "Drake Maye" -> tokens ["DRAKE", "MAYE"]; "D.Maye" or "Drake Maye" matches "Maye"
    tokens = b.split()
    for t in tokens:
        if t and t in a:
            return True
    return False


def qb_teams_in_post(pbp_post: pd.DataFrame, qb: str) -> List[str]:
    """
    Return list of team abbrs (posteam) for which this QB has at least one passer or rusher play in POST.
    Uses passer_player_name / rusher_player_name; if missing, returns [] (cannot infer).
    """
    if pbp_post.empty:
        return []
    teams: List[str] = []
    if "passer_player_name" in pbp_post.columns and "posteam" in pbp_post.columns:
        pass_plays = pbp_post[pbp_post["passer_player_name"].apply(lambda x: _qb_name_matches(x, qb))]
        teams.extend(pass_plays["posteam"].dropna().unique().tolist())
    if "rusher_player_name" in pbp_post.columns and "posteam" in pbp_post.columns:
        rush_plays = pbp_post[pbp_post["rusher_player_name"].apply(lambda x: _qb_name_matches(x, qb))]
        teams.extend(rush_plays["posteam"].dropna().unique().tolist())
    return sorted(set(str(t) for t in teams))


def _schedule_post_game_ids(schedules: pd.DataFrame, team: str, year: int) -> List[str]:
    """Ground truth: game_ids for this team in POST for this year from schedules."""
    if schedules is None or schedules.empty or "game_id" not in schedules.columns:
        return []
    s = schedules.copy()
    if "home_team" not in s.columns or "away_team" not in s.columns:
        return []
    team_games = s[(s["home_team"] == team) | (s["away_team"] == team)]
    if "season" in s.columns:
        team_games = team_games[team_games["season"].astype(str) == str(year)]
    if "game_type" in s.columns:
        gt = team_games["game_type"].astype(str).str.upper()
        # POST = not REG (i.e. WC, DIV, CON, SB)
        team_games = team_games[gt != "REG"]
    if "season_type" in s.columns:
        team_games = team_games[team_games["season_type"].astype(str).str.upper() == "POST"]
    return team_games["game_id"].dropna().unique().tolist()


def _opponent_for_game(schedules: pd.DataFrame, game_id: str, team: str) -> str:
    if schedules is None or schedules.empty:
        return ""
    row = schedules[schedules["game_id"] == game_id]
    if row.empty:
        return ""
    r = row.iloc[0]
    return str(r["away_team"]) if r.get("home_team") == team else str(r.get("home_team", ""))


def _game_round(schedules: pd.DataFrame, game_id: str) -> str:
    if schedules is None or "game_type" not in schedules.columns:
        return ""
    row = schedules[schedules["game_id"] == game_id]
    if row.empty:
        return ""
    return str(row.iloc[0].get("game_type", ""))


@dataclass
class QBGameCheck:
    qb: str
    team: str
    season: int
    season_type: str
    game_ids: List[str]
    opponents: List[str]
    qb_dropbacks_by_game: Dict[str, int]
    qb_plays_by_game: Dict[str, int]  # pass + qb rush + sacks


def find_qb_games_post(
    pbp_post: pd.DataFrame,
    schedules: pd.DataFrame,
    qb: str,
    team: str,
    year: int,
) -> QBGameCheck:
    """
    Determine which POST games belong to the QB+team using schedules as ground truth,
    then cross-check PBP for QB involvement.

    Raises ValueError if:
      - Schedule has games for team but QB has 0 plays in those games (wrong QB/team).
      - QB has plays in game_ids not in that team's POST schedule (data inconsistency).
    """
    schedule_game_ids = _schedule_post_game_ids(schedules, team, year)
    game_ids = list(schedule_game_ids)
    opponents = [_opponent_for_game(schedules, gid, team) for gid in game_ids]

    team_pbp = pbp_post[pbp_post["posteam"] == team] if not pbp_post.empty else pd.DataFrame()
    pbp_game_ids = team_pbp["game_id"].dropna().unique().tolist() if "game_id" in team_pbp.columns else []

    has_passer = "passer_player_name" in team_pbp.columns
    has_rusher = "rusher_player_name" in team_pbp.columns
    qb_dropbacks_by_game: Dict[str, int] = {gid: 0 for gid in game_ids}
    qb_plays_by_game: Dict[str, int] = {gid: 0 for gid in game_ids}

    for gid in game_ids:
        g_pbp = team_pbp[team_pbp["game_id"] == gid]
        if g_pbp.empty:
            continue
        # QB pass attempts (incl. sacks): passer == qb
        if has_passer:
            pass_plays = g_pbp[g_pbp["passer_player_name"].apply(lambda x: _qb_name_matches(x, qb))]
            dropbacks = pass_plays[pass_plays["play_type"].isin(["pass", "sack"])] if "play_type" in g_pbp.columns else pass_plays
            qb_dropbacks_by_game[gid] = len(dropbacks)
            qb_plays_by_game[gid] = len(pass_plays)
        # QB rushes
        if has_rusher:
            rush_plays = g_pbp[g_pbp["rusher_player_name"].apply(lambda x: _qb_name_matches(x, qb))]
            qb_plays_by_game[gid] = qb_plays_by_game.get(gid, 0) + len(rush_plays)
        # Sacks with passer: already in pass_plays if passer_player_name set on sack; else count play_type==sack for team
        if has_passer and "play_type" in g_pbp.columns:
            sacks = g_pbp[g_pbp["play_type"] == "sack"]
            sack_qb = sacks[sacks["passer_player_name"].apply(lambda x: _qb_name_matches(x, qb))]
            # dropbacks = pass + sack; we counted pass_plays above which may include sack if passer present
            pass_and_sack = g_pbp[g_pbp["play_type"].isin(["pass", "sack"])]
            pass_and_sack_qb = pass_and_sack[pass_and_sack["passer_player_name"].apply(lambda x: _qb_name_matches(x, qb))]
            qb_dropbacks_by_game[gid] = len(pass_and_sack_qb)

    total_qb_plays = sum(qb_plays_by_game.values())
    total_qb_dropbacks = sum(qb_dropbacks_by_game.values())

    if game_ids and total_qb_plays == 0:
        teams_with_qb = qb_teams_in_post(pbp_post, qb)
        raise ValueError(
            f"QB {qb!r} has 0 plays in team {team!r} postseason games (year={year}). "
            f"Schedule says {team} played POST games: {game_ids}. "
            f"QB appears in PBP for teams: {teams_with_qb or ['(none—check passer_player_name)']}. "
            "Fix --team or --qb so they match."
        )

    # Check for QB plays in games not in schedule (team's POST)
    if has_passer or has_rusher:
        for gid in pbp_game_ids:
            if gid in game_ids:
                continue
            g_pbp = team_pbp[team_pbp["game_id"] == gid]
            qb_in_g = False
            if has_passer:
                qb_in_g = g_pbp["passer_player_name"].apply(lambda x: _qb_name_matches(x, qb)).any()
            if not qb_in_g and has_rusher:
                qb_in_g = g_pbp["rusher_player_name"].apply(lambda x: _qb_name_matches(x, qb)).any()
            if qb_in_g:
                raise ValueError(
                    f"QB {qb!r} has plays in game_id={gid} but that game is not in team {team!r} POST schedule (year={year}). "
                    "Schedule POST game_ids do not match PBP."
                )

    return QBGameCheck(
        qb=qb,
        team=team,
        season=year,
        season_type="POST",
        game_ids=game_ids,
        opponents=opponents,
        qb_dropbacks_by_game=qb_dropbacks_by_game,
        qb_plays_by_game=qb_plays_by_game,
    )


def print_validation_table(check: QBGameCheck, schedules: pd.DataFrame) -> None:
    """Print a clear validation table: game_id, opp, qb_pass_att, qb_rush_att, sacks."""
    if not check.game_ids:
        print(f"  {check.qb} ({check.team}): no POST games in schedule.")
        return
    print(f"  {check.qb} ({check.team}) POST {check.season}:")
    print("  game_id          opp   qb_dropbacks  qb_plays")
    for gid, opp in zip(check.game_ids, check.opponents):
        db = check.qb_dropbacks_by_game.get(gid, 0)
        pl = check.qb_plays_by_game.get(gid, 0)
        rnd = _game_round(schedules, gid)
        print(f"  {gid}  {opp:4}  {db:12}  {pl:8}  ({rnd})")
    print(f"  TOTAL:           dropbacks={sum(check.qb_dropbacks_by_game.values())}  plays={sum(check.qb_plays_by_game.values())}")
