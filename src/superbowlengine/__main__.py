"""CLI entrypoint: python -m superbowlengine [repro|app|predict]."""

import sys
from pathlib import Path

# Ensure src is on path when run as python -m superbowlengine
if __name__ == "__main__":
    src = Path(__file__).resolve().parent.parent
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data.load import load_pbp
from superbowlengine.features.keys import compute_team_keys_from_pbp
from superbowlengine.models.professor_keys import predict_from_keys


def _repro() -> None:
    pbp = load_pbp(years=[DEFAULT_CONFIG.default_year], columns=DEFAULT_CONFIG.pbp_columns)
    post = pbp[pbp["season_type"] == "POST"].copy()
    sea_keys = compute_team_keys_from_pbp(post, "SEA")
    ne_keys = compute_team_keys_from_pbp(post, "NE")
    print("SEA postseason keys:", sea_keys)
    print("NE postseason keys :", ne_keys)
    out = predict_from_keys(sea_keys, ne_keys)
    print("\nPrediction:", out)


def _app() -> None:
    import subprocess
    app_path = Path(__file__).resolve().parent / "app" / "streamlit_app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=True)


def _predict(year: int, team_a: str, team_b: str) -> None:
    from superbowlengine.data.cache import get_cached_pbp
    pbp = get_cached_pbp([year])
    post = pbp[pbp["season_type"] == "POST"].copy()
    if post.empty:
        print(f"No postseason data for {year}")
        return
    keys_a = compute_team_keys_from_pbp(post, team_a)
    keys_b = compute_team_keys_from_pbp(post, team_b)
    out = predict_from_keys(keys_a, keys_b)
    print("Prediction:", out)


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="SuperBowlEngine")
    p.add_argument("cmd", nargs="?", default="repro", choices=["repro", "app", "predict"],
                   help="repro: p1.py output; app: Streamlit; predict: two teams")
    p.add_argument("--year", type=int, default=DEFAULT_CONFIG.default_year)
    p.add_argument("--team-a", default="SEA")
    p.add_argument("--team-b", default="NE")
    args = p.parse_args()
    if args.cmd == "repro":
        _repro()
    elif args.cmd == "app":
        _app()
    else:
        _predict(args.year, args.team_a, args.team_b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
