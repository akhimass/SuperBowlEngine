from __future__ import annotations

import argparse
import random

from superbowlengine.data import get_schedules
from gridironiq.matchup_engine import run_matchup


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--mode", type=str, default="regular")
    args = parser.parse_args()

    sched = get_schedules([args.season])
    games = sched[["home_team", "away_team"]].dropna().drop_duplicates().to_dict("records")
    random.shuffle(games)
    games = games[: args.n]

    for g in games:
        a = str(g["home_team"])
        b = str(g["away_team"])
        try:
            r = run_matchup(args.season, a, b, mode=args.mode)
        except Exception as e:
            print(a, "vs", b, "ERROR", str(e))
            continue

        s = r.projected_score
        sa = s.get(a, 0)
        sb = s.get(b, 0)
        print(
            f"{args.season} {a} vs {b} | p={r.win_probability:.3f} winner={r.predicted_winner} "
            f"score={sa}-{sb} margin={r.projected_margin} total={r.projected_total}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

