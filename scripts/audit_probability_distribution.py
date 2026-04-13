from __future__ import annotations

import argparse
import random

import pandas as pd

from superbowlengine.data import get_schedules
from gridironiq.matchup_engine import run_matchup


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--n", type=int, default=100)
    args = parser.parse_args()

    sched = get_schedules([args.season])
    if sched.empty:
        print("No schedules.")
        return 0

    games = sched[["home_team", "away_team"]].dropna().drop_duplicates().to_dict("records")
    random.shuffle(games)
    games = games[: args.n]

    probs = []
    for g in games:
        try:
            r = run_matchup(args.season, str(g["home_team"]), str(g["away_team"]), mode="regular")
            probs.append(float(r.win_probability))
        except Exception:
            continue

    s = pd.Series(probs)
    if s.empty:
        print("No probabilities computed.")
        return 0

    print("n:", int(s.count()))
    print("min:", float(s.min()), "p1:", float(s.quantile(0.01)), "p5:", float(s.quantile(0.05)))
    print("p50:", float(s.quantile(0.5)), "p95:", float(s.quantile(0.95)), "p99:", float(s.quantile(0.99)), "max:", float(s.max()))
    print("extreme (<0.05 or >0.95):", int(((s < 0.05) | (s > 0.95)).sum()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

