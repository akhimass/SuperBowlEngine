"""
CLI entrypoint: run repro, app, or predict.
Usage:
  python scripts/run.py repro
  python scripts/run.py app
  python scripts/run.py predict --year 2025 --team-a SEA --team-b NE
"""

import argparse

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data.load import load_pbp
from superbowlengine.features.keys import compute_team_keys_from_pbp
from superbowlengine.models.professor_keys import predict_from_keys


def cmd_repro() -> None:
    """Reproduce p1.py output."""
    from superbowlengine.config import DEFAULT_CONFIG
    from superbowlengine.data.load import load_pbp
    from superbowlengine.features.keys import compute_team_keys_from_pbp
    from superbowlengine.models.professor_keys import predict_from_keys
    year = DEFAULT_CONFIG.default_year
    pbp = load_pbp(years=[year], columns=DEFAULT_CONFIG.pbp_columns)
    post = pbp[pbp["season_type"] == "POST"].copy()
    sea_keys = compute_team_keys_from_pbp(post, "SEA")
    ne_keys = compute_team_keys_from_pbp(post, "NE")
    print("SEA postseason keys:", sea_keys)
    print("NE postseason keys :", ne_keys)
    out = predict_from_keys(sea_keys, ne_keys)
    print("\nPrediction:", out)


def cmd_app() -> None:
    """Launch Streamlit app."""
    import subprocess
    import sys
    from pathlib import Path
    app_path = Path(__file__).resolve().parent.parent / "src" / "superbowlengine" / "app" / "streamlit_app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=True)


def cmd_predict(year: int, team_a: str, team_b: str, use_cache: bool = True) -> None:
    """Load PBP, compute keys, print prediction."""
    years = [year]
    if use_cache:
        from superbowlengine.data.cache import get_cached_pbp
        pbp = get_cached_pbp(years)
    else:
        pbp = load_pbp(years=years)
    post = pbp[pbp["season_type"] == "POST"].copy()
    if post.empty:
        print(f"No postseason data for {year}")
        return
    keys_a = compute_team_keys_from_pbp(post, team_a)
    keys_b = compute_team_keys_from_pbp(post, team_b)
    out = predict_from_keys(keys_a, keys_b)
    print(f"Keys {team_a}:", keys_a)
    print(f"Keys {team_b}:", keys_b)
    print("Prediction:", out)


def main() -> None:
    parser = argparse.ArgumentParser(description="SuperBowlEngine CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("repro", help="Reproduce p1.py output")
    sub.add_parser("app", help="Run Streamlit app")
    p = sub.add_parser("predict", help="Run professor predictor for two teams")
    p.add_argument("--year", type=int, default=DEFAULT_CONFIG.default_year)
    p.add_argument("--team-a", default="SEA")
    p.add_argument("--team-b", default="NE")
    p.add_argument("--no-cache", action="store_true", help="Disable PBP cache")
    args = parser.parse_args()

    if args.command == "repro":
        cmd_repro()
    elif args.command == "app":
        cmd_app()
    elif args.command == "predict":
        cmd_predict(args.year, args.team_a, args.team_b, use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
