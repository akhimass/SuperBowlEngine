"""
Game listing helpers: who a team played, how many games, game type (WC/DIV/CON/SB).

Used to verify matchup validity before trusting aggregated 5 Keys (e.g. NE 3 games vs SEA 2 games).
"""

import pandas as pd


def list_team_games(
    pbp: pd.DataFrame,
    team: str,
    schedule: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    List games for one team from PBP: game_id, home_team, away_team, opponent.
    If schedule is provided and has game_type, includes game_type (e.g. WC, DIV, CON, SB).
    """
    team_pbp = pbp[pbp["posteam"] == team][["game_id", "home_team", "away_team"]].drop_duplicates()
    if team_pbp.empty:
        cols = ["game_id", "home_team", "away_team", "opponent"]
        if schedule is not None and "game_type" in schedule.columns:
            cols.append("game_type")
        return pd.DataFrame(columns=cols)

    def opponent(row: pd.Series) -> str:
        if row["home_team"] == team:
            return str(row["away_team"])
        return str(row["home_team"])

    team_pbp = team_pbp.reset_index(drop=True)
    team_pbp["opponent"] = team_pbp.apply(opponent, axis=1)

    if schedule is not None and "game_id" in schedule.columns and "game_type" in schedule.columns:
        sched_sub = schedule[["game_id", "game_type"]].drop_duplicates()
        team_pbp = team_pbp.merge(sched_sub, on="game_id", how="left")
    return team_pbp


def team_games_summary(
    pbp: pd.DataFrame,
    team: str,
    schedule: pd.DataFrame | None = None,
) -> str:
    """Human-readable summary: number of games, list of opponents, game types if available."""
    df = list_team_games(pbp, team, schedule)
    if df.empty:
        return f"{team}: 0 games"
    n = len(df)
    lines = [f"{team}: {n} game(s)"]
    for _, row in df.iterrows():
        opp = row["opponent"]
        at = "vs" if row["home_team"] == team else "@"
        gt = f"  ({row['game_type']})" if "game_type" in row and pd.notna(row.get("game_type")) else ""
        lines.append(f"  {at} {opp}{gt}")
    return "\n".join(lines)
