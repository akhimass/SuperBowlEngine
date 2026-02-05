"""
Reproduce original p1.py output using the SuperBowlEngine package.
Run from repo root: python scripts/p1_repro.py
Or: python -m superbowlengine (CLI) then choose repro, or run this script.
"""

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data.load import load_pbp
from superbowlengine.features.keys import compute_team_keys_from_pbp
from superbowlengine.models.professor_keys import predict_from_keys


def main() -> None:
    year = DEFAULT_CONFIG.default_year
    cols = DEFAULT_CONFIG.pbp_columns
    pbp = load_pbp(years=[year], columns=cols)
    post = pbp[pbp["season_type"] == "POST"].copy()

    sea_keys = compute_team_keys_from_pbp(post, "SEA")
    ne_keys = compute_team_keys_from_pbp(post, "NE")

    print("SEA postseason keys:", sea_keys)
    print("NE postseason keys :", ne_keys)

    out = predict_from_keys(sea_keys, ne_keys)
    print("\nPrediction:", out)


if __name__ == "__main__":
    main()
