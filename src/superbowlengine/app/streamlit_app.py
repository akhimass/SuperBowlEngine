"""Minimal Streamlit app: load PBP, compute 5 Keys, run professor predictor."""

from typing import List, Optional

import pandas as pd
import streamlit as st

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data.load import load_pbp
from superbowlengine.data import get_schedules
from superbowlengine.data.availability import assess_5keys_availability, AvailabilityReport
from superbowlengine.features.keys import TeamKeys, compute_team_keys_from_pbp
from superbowlengine.features.keys_pipeline import prepare_keys_for_matchup
from superbowlengine.models.professor_keys import predict_from_keys


def _render_availability_badge(report: AvailabilityReport) -> None:
    """Render Data Availability / Readiness badge from an AvailabilityReport."""
    st.subheader("Data Availability / Readiness")
    status = report.overall_status
    color = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(status, "⚪")
    st.markdown(f"**{color} {status}** — %s" % (" ".join(report.notes)))
    for key_name in ["TOP", "Turnovers", "Big Plays", "3rd Down", "Red Zone"]:
        missing = report.missing_by_key.get(key_name, [])
        if missing:
            st.caption(f"  • {key_name}: missing → {missing}")
        else:
            st.caption(f"  • {key_name}: ✓")
    st.divider()


def run_app(
    default_year: Optional[int] = None,
    default_team_a: str = "SEA",
    default_team_b: str = "NE",
) -> None:
    """Run Streamlit UI with optional defaults."""
    year = default_year or DEFAULT_CONFIG.default_year
    st.title("SuperBowlEngine — 5 Keys Predictor")
    st.write("Load PBP, compute 5 Keys for two teams, and run the professor-style predictor.")

    year_input = st.number_input("Season year", min_value=1999, max_value=2030, value=year)
    team_a = st.text_input("Team A (e.g. SEA)", value=default_team_a)
    team_b = st.text_input("Team B (e.g. NE)", value=default_team_b)
    mode = st.selectbox(
        "Keys aggregation",
        options=["aggregate", "per_game", "opp_weighted"],
        index=2,
        help="aggregate=sum over games; per_game=simple avg; opp_weighted=avg by opponent strength + TO dampen",
    )
    use_cache = st.checkbox("Use cache (if available)", value=True)

    if st.button("Load PBP & Predict"):
        with st.spinner("Loading PBP..."):
            if use_cache:
                from superbowlengine.data.cache import get_cached_pbp
                pbp = get_cached_pbp([year_input])
            else:
                pbp = load_pbp(years=[year_input])
        availability = assess_5keys_availability(pbp)
        _render_availability_badge(availability)
        if availability.overall_status == "RED":
            st.error("Cannot compute 5 Keys from this dataset. Check notes above.")
            return
        post = pbp[pbp["season_type"] == "POST"].copy()
        if post.empty:
            st.warning("No postseason data for this year.")
            return
        pbp_reg = pbp[pbp["season_type"] == "REG"] if "season_type" in pbp.columns else pd.DataFrame()
        schedules = get_schedules([int(year_input)])
        keys_a, keys_b, per_game_a, per_game_b = prepare_keys_for_matchup(
            post, schedules, team_a, team_b, mode=mode, reg_pbp=pbp_reg,
        )
        sea_keys = TeamKeys(team=team_a, top_min=keys_a.top_min, turnovers=keys_a.turnovers,
            big_plays=keys_a.big_plays, third_down_pct=keys_a.third_down_pct,
            redzone_td_pct=keys_a.redzone_td_pct)
        ne_keys = TeamKeys(team=team_b, top_min=keys_b.top_min, turnovers=keys_b.turnovers,
            big_plays=keys_b.big_plays, third_down_pct=keys_b.third_down_pct,
            redzone_td_pct=keys_b.redzone_td_pct)
        out = predict_from_keys(sea_keys, ne_keys)
        out_display = {**out, "predicted_winner": team_a if out["predicted_winner"] == "SEA" else team_b}
        out = out_display
        st.subheader("5 Keys")
        st.write(f"**{team_a}**: TOP={keys_a.top_min}, TO={keys_a.turnovers}, Big={keys_a.big_plays}, "
                 f"3rd%={keys_a.third_down_pct}, RZ%={keys_a.redzone_td_pct}")
        st.write(f"**{team_b}**: TOP={keys_b.top_min}, TO={keys_b.turnovers}, Big={keys_b.big_plays}, "
                 f"3rd%={keys_b.third_down_pct}, RZ%={keys_b.redzone_td_pct}")
        with st.expander("Show per-game keys"):
            if per_game_a is not None and not per_game_a.empty:
                cols = [c for c in ["game_id", "opp", "top_min", "turnovers", "big_plays", "third_down_pct", "redzone_td_pct", "weight"] if c in per_game_a.columns]
                st.dataframe(per_game_a[cols], use_container_width=True)
            if per_game_b is not None and not per_game_b.empty:
                cols = [c for c in ["game_id", "opp", "top_min", "turnovers", "big_plays", "third_down_pct", "redzone_td_pct", "weight"] if c in per_game_b.columns]
                st.dataframe(per_game_b[cols], use_container_width=True)
            if (per_game_a is None or per_game_a.empty) and (per_game_b is None or per_game_b.empty):
                st.caption("Per-game keys only available for per_game or opp_weighted mode.")
        st.subheader("Prediction")
        st.json(out)


if __name__ == "__main__":
    run_app()
