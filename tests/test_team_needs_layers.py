from __future__ import annotations

import pytest

from gridironiq.draft.room_production import build_room_need_raw_by_team, clear_room_cache
from gridironiq.draft.scheme_fit import TE_ARCHETYPE_PREFS, _player_archetype_vector, build_team_scheme_profile, infer_te_archetype


@pytest.mark.parametrize("team", ["KC", "GB", "DET"])
def test_scheme_vector_dimension_matches_player_embedding(team: str) -> None:
    scheme = build_team_scheme_profile(team, 2024)
    team_vec = scheme["vector"]
    prof = {"pos_bucket": "TE", "pos": "TE", "height_in": 76.0, "weight_lb": 250.0, "forty": 4.65}
    pvec = _player_archetype_vector(prof, scheme.get("raw"))
    assert len(team_vec) == len(pvec) == 10


def test_infer_te_archetype_explicit_tag_overrides() -> None:
    p = {
        "pos_bucket": "TE",
        "te_scheme_archetype": "inline_blocker",
        "forty": 4.5,
        "weight_lb": 240,
    }
    assert infer_te_archetype(p) == "inline_blocker"
    assert TE_ARCHETYPE_PREFS["receiving_weapon"][0] > TE_ARCHETYPE_PREFS["inline_blocker"][0]


def test_room_cache_hit() -> None:
    """Second call with same season returns same object (identity), confirming cache is used."""
    clear_room_cache()
    first = build_room_need_raw_by_team(2024)
    second = build_room_need_raw_by_team(2024)
    assert first is second


def test_te_room_raw_correlates_with_normalized_need() -> None:
    """Top TE room-weakness teams (raw) should average at least as high TE need as bottom group."""
    from statistics import mean

    from gridironiq.draft.team_needs import compute_team_needs

    raw_map, _ = build_room_need_raw_by_team(2024)
    if not raw_map:
        pytest.skip("no player_stats")
    te_raw = [(t, raw_map[t].get("TE", 0.0)) for t in raw_map]
    te_raw.sort(key=lambda x: -x[1])
    top5 = [t for t, _ in te_raw[:5]]
    bot5 = [t for t, _ in te_raw[-5:]]
    mt = mean(compute_team_needs(t, 2024)["need_scores"]["TE"] for t in top5)
    mb = mean(compute_team_needs(t, 2024)["need_scores"]["TE"] for t in bot5)
    assert mt >= mb
