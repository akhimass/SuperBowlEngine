import nfl_data_py as nfl
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Tuple
import math

# ----------------------------
# Utils
# ----------------------------
def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))

def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0

def mmss_to_seconds(mmss: str) -> int:
    # drive_time_of_possession is commonly "MM:SS" (may have NaNs)
    if pd.isna(mmss):
        return 0
    parts = str(mmss).split(":")
    if len(parts) != 2:
        return 0
    return int(parts[0]) * 60 + int(parts[1])

# ----------------------------
# 5 Keys dataclass
# ----------------------------
@dataclass
class TeamKeys:
    team: str
    top_min: float
    turnovers: int
    big_plays: int
    third_down_pct: float
    redzone_td_pct: float

# ----------------------------
# Feature engineering from PBP
# ----------------------------
def compute_team_keys_from_pbp(pbp: pd.DataFrame, team: str) -> TeamKeys:
    """
    Requires pbp columns typically present in nflverse pbp:
      posteam, defteam, down, ydstogo, yards_gained, play_type, touchdown,
      interception, fumble_lost, drive, game_id, drive_time_of_possession, yardline_100
    """
    tdf = pbp[pbp["posteam"] == team].copy()

    # --- 1) TOP: sum drive_time_of_possession over unique drives (offense drives)
    # drive_time_of_possession is defined as time of possession in a given drive.  [oai_citation:4‡nflfastr.com](https://nflfastr.com/reference/fast_scraper.html?utm_source=chatgpt.com)
    drive_top = (
        tdf.dropna(subset=["game_id", "drive"])
           .drop_duplicates(subset=["game_id", "drive"])
    )
    top_seconds = drive_top["drive_time_of_possession"].apply(mmss_to_seconds).sum()
    top_min = top_seconds / 60.0

    # --- 2) Turnovers: interceptions + fumbles lost
    ints = int(tdf.get("interception", 0).fillna(0).sum())
    fum_lost = int(tdf.get("fumble_lost", 0).fillna(0).sum())
    turnovers = ints + fum_lost

    # --- 3) Big plays: 20+ yards rush/pass
    # (You can refine to exclude penalties/no_plays later)
    big_play_mask = (
        tdf["play_type"].isin(["pass", "run"]) &
        (tdf["yards_gained"].fillna(0) >= 20)
    )
    big_plays = int(big_play_mask.sum())

    # --- 4) 3rd down efficiency: 3rd down plays that earn 1st down or TD
    third = tdf[(tdf["down"] == 3) & tdf["play_type"].isin(["pass", "run"])].copy()
    third_attempts = len(third)

    # "Conversion" proxy: gained >= ydstogo OR touchdown==1
    third_converted = int(((third["yards_gained"].fillna(0) >= third["ydstogo"].fillna(999)) |
                           (third.get("touchdown", 0).fillna(0) == 1)).sum())
    third_down_pct = 100.0 * safe_div(third_converted, third_attempts)

    # --- 5) Red zone efficiency: TDs per red-zone trip
    # Define a "red zone trip" as a drive where offense runs ANY play with yardline_100 <= 20
    rz = tdf[tdf["yardline_100"].fillna(999) <= 20].copy()
    rz_drives = rz.dropna(subset=["game_id", "drive"]).drop_duplicates(subset=["game_id", "drive"])
    rz_trips = len(rz_drives)

    rz_tds = int(rz.get("touchdown", 0).fillna(0).sum())
    # This counts TD plays in red zone; you can refine to "drive ended in TD" later.
    redzone_td_pct = 100.0 * safe_div(rz_tds, rz_trips)

    return TeamKeys(
        team=team,
        top_min=round(top_min, 2),
        turnovers=turnovers,
        big_plays=big_plays,
        third_down_pct=round(third_down_pct, 2),
        redzone_td_pct=round(redzone_td_pct, 2),
    )

# ----------------------------
# SOS (simple, defendable)
# ----------------------------
def compute_team_sos(season_games: pd.DataFrame, team: str) -> float:
    """
    Simple SOS: average opponent win% (regular season).
    You can compute from schedule results; this is a lightweight baseline.
    """
    # season_games should be game-level. Easiest way: derive from pbp at game level.
    # We'll build game outcomes from season_games with columns:
    # game_id, home_team, away_team, home_score, away_score
    g = season_games.copy()

    # Compute win/loss for each team
    g["home_win"] = (g["home_score"] > g["away_score"]).astype(int)
    g["away_win"] = (g["away_score"] > g["home_score"]).astype(int)

    # Team win totals
    home_wins = g.groupby("home_team")["home_win"].sum()
    away_wins = g.groupby("away_team")["away_win"].sum()
    wins = home_wins.add(away_wins, fill_value=0)

    # Games played
    home_gp = g["home_team"].value_counts()
    away_gp = g["away_team"].value_counts()
    gp = home_gp.add(away_gp, fill_value=0)

    win_pct = (wins / gp).fillna(0)

    # Opponents faced by team
    opps_home = g.loc[g["home_team"] == team, "away_team"]
    opps_away = g.loc[g["away_team"] == team, "home_team"]
    opps = pd.concat([opps_home, opps_away], ignore_index=True)

    if len(opps) == 0:
        return 0.0

    return float(win_pct.reindex(opps).mean())

# ----------------------------
# Super Bowl predictor (your professor rule + turnover emphasis)
# ----------------------------
def predict_from_keys(sea: TeamKeys, ne: TeamKeys,
                      turnover_weight=1.35, key_weight=0.55, rule_bonus=0.40) -> Dict[str, object]:
    def key_winners(a: TeamKeys, b: TeamKeys) -> Dict[str, str]:
        return {
            "TOP": "SEA" if a.top_min > b.top_min else "NE",
            "TO":  "SEA" if a.turnovers < b.turnovers else "NE",
            "BIG": "SEA" if a.big_plays > b.big_plays else "NE",
            "3D":  "SEA" if a.third_down_pct > b.third_down_pct else "NE",
            "RZ":  "SEA" if a.redzone_td_pct > b.redzone_td_pct else "NE",
        }

    winners = key_winners(sea, ne)
    counts = {"SEA": 0, "NE": 0}
    for _, w in winners.items():
        counts[w] += 1

    # Margins SEA-NE
    m_top = sea.top_min - ne.top_min
    m_to  = ne.turnovers - sea.turnovers
    m_big = sea.big_plays - ne.big_plays
    m_3d  = sea.third_down_pct - ne.third_down_pct
    m_rz  = sea.redzone_td_pct - ne.redzone_td_pct

    logit = 0.0
    logit += key_weight * (m_top / 6.0)
    logit += turnover_weight * (m_to / 1.0)
    logit += key_weight * (m_big / 2.0)
    logit += key_weight * (m_3d / 10.0)
    logit += key_weight * (m_rz / 12.0)

    if counts["SEA"] >= 3:
        logit += rule_bonus
    if counts["NE"] >= 3:
        logit -= rule_bonus

    p_sea = sigmoid(logit)
    return {
        "p_sea_win": round(p_sea, 3),
        "p_ne_win": round(1 - p_sea, 3),
        "predicted_winner": "SEA" if p_sea >= 0.5 else "NE",
        "keys_won": counts,
        "key_winners": winners,
        "margins_sea_minus_ne": {"TOP": m_top, "TO": m_to, "BIG": m_big, "3D": m_3d, "RZ": m_rz},
    }

# ----------------------------
# Run: pull PBP and compute postseason keys
# ----------------------------
if __name__ == "__main__":
    YEAR = 2025

    # 1) Pull pbp. nfl_data_py provides import_pbp_data years+columns.  [oai_citation:5‡PyPI](https://pypi.org/project/nfl-data-py/0.0.5/?utm_source=chatgpt.com)
    cols = [
        "game_id","season_type","week","posteam","defteam","home_team","away_team",
        "down","ydstogo","yards_gained","play_type","touchdown",
        "interception","fumble_lost","drive","drive_time_of_possession","yardline_100",
        "home_score","away_score"
    ]
    pbp = nfl.import_pbp_data([YEAR], columns=cols)

    # 2) Filter postseason
    post = pbp[pbp["season_type"] == "POST"].copy()

    # 3) Compute team keys from postseason pbp
    sea_keys = compute_team_keys_from_pbp(post, "SEA")
    ne_keys  = compute_team_keys_from_pbp(post, "NE")

    print("SEA postseason keys:", sea_keys)
    print("NE postseason keys :", ne_keys)

    # 4) Predict Super Bowl from keys
    out = predict_from_keys(sea_keys, ne_keys)
    print("\nPrediction:", out)