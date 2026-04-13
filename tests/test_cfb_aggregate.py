from __future__ import annotations

from gridironiq.draft.cfb_stats import aggregate_cfbd_rows, normalize_person_name, raw_production_efficiency


def test_aggregate_cfbd_rows_groups_player() -> None:
    rows = [
        {
            "playerId": "test-qb-1",
            "player": "Test Qb",
            "team": "Test U",
            "position": "QB",
            "category": "passing",
            "statType": "YDS",
            "stat": "3200",
        },
        {
            "playerId": "test-qb-1",
            "player": "Test Qb",
            "team": "Test U",
            "position": "QB",
            "category": "passing",
            "statType": "ATT",
            "stat": "450",
        },
        {
            "playerId": "test-qb-1",
            "player": "Test Qb",
            "team": "Test U",
            "position": "QB",
            "category": "passing",
            "statType": "TD",
            "stat": "28",
        },
    ]
    by = aggregate_cfbd_rows(rows)
    assert "test-qb-1" in by
    p = by["test-qb-1"]["stats"]["passing"]
    assert p["YDS"] == 3200.0
    assert p["ATT"] == 450.0


def test_normalize_person_name() -> None:
    assert normalize_person_name("Joe Smith Jr.") == normalize_person_name("Joe Smith")


def test_raw_qb_efficiency() -> None:
    blob = {
        "stats": {
            "passing": {"YDS": 3500, "ATT": 500, "TD": 30, "INT": 8},
        }
    }
    out = raw_production_efficiency("QB", blob)
    assert out is not None
    prod, eff = out
    assert prod > 0
    assert eff > 0
