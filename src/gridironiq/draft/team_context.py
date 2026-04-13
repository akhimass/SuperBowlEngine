from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .room_production import build_room_need_score, compute_position_share_trend
from .scheme_fit import build_team_scheme_profile
from .team_needs import NEED_BUCKETS, compute_team_needs


@dataclass
class TeamContext:
    """Runtime, data-derived view of one NFL team for draft scoring (no manual priors)."""

    team: str
    season: int
    needs: Dict[str, float]
    needs_detail: Dict[str, Any]
    scheme_profile: Dict[str, Any]
    room_scores: Dict[str, float]
    snap_depth: Dict[str, float]
    injury_pressure: Dict[str, float]
    te_target_share_trend: float
    wr_target_share_trend: float
    edge_pressure_trend: float
    rb_target_share_trend: float
    pass_rate: float
    shotgun_rate: float
    need_signal_policy: Dict[str, Any]
    draft_pick_positions: List[int] = field(default_factory=list)

    def __repr__(self) -> str:
        ranked = sorted(self.needs.items(), key=lambda x: -x[1])[:11]
        need_s = " | ".join(f"{k}={v:.1f}" for k, v in ranked)
        raw = self.scheme_profile.get("raw", {})
        te_s = float(raw.get("te_target_share", 0.0))
        trend_note = f"te_trend={self.te_target_share_trend:+.3f}"
        src = self.need_signal_policy.get("sources", [])
        return (
            f"TeamContext({self.team} {self.season})\n"
            f"  Need Ranks: {need_s}\n"
            f"  Scheme: pass_rate={self.pass_rate:.2f} | te_share={te_s:.2f} | {trend_note}\n"
            f"  Policy: data_only | manual_need_priors={self.need_signal_policy.get('manual_need_priors')} | "
            f"sources={src}\n"
            f"  Picks: {self.draft_pick_positions}"
        )


def build_team_context(
    team: str,
    season: int,
    *,
    draft_pick_positions: List[int] | None = None,
) -> TeamContext:
    """
    Single load path for team-scoped nflverse-backed signals used by the draft pipeline.
    """
    team_u = str(team).upper()
    needs_payload = compute_team_needs(team_u, int(season))
    layers = needs_payload.get("signal_layers") or {}
    scheme = build_team_scheme_profile(team_u, int(season))
    raw = scheme.get("raw") or {}

    room_scores = {b: float(build_room_need_score(team_u, b, int(season))) for b in NEED_BUCKETS}
    mx_r = max(room_scores.values()) if room_scores else 1.0
    if mx_r <= 0:
        mx_r = 1.0
    room_scores = {b: 100.0 * room_scores[b] / mx_r for b in NEED_BUCKETS}

    s2, s1, s0 = int(season) - 2, int(season) - 1, int(season)
    trend_seasons = [s2, s1, s0]
    te_tr = compute_position_share_trend(team_u, "TE", trend_seasons)
    wr_tr = compute_position_share_trend(team_u, "WR", trend_seasons)
    rb_tr = compute_position_share_trend(team_u, "RB", trend_seasons)
    edge_tr = compute_position_share_trend(team_u, "EDGE", trend_seasons)

    policy = dict(needs_payload["need_signal_policy"])
    policy["trend_window_seasons"] = trend_seasons
    base_sources = list(policy.get("sources") or [])
    for s in (
        "nflverse_player_stats",
        "share_trend_linear_fit",
    ):
        if s not in base_sources:
            base_sources.append(s)
    policy["sources"] = base_sources

    picks = list(draft_pick_positions) if draft_pick_positions else []

    return TeamContext(
        team=team_u,
        season=int(season),
        needs=dict(needs_payload["need_scores"]),
        needs_detail=needs_payload,
        scheme_profile=scheme,
        room_scores=room_scores,
        snap_depth=dict(layers.get("snap_depth_normalized") or {}),
        injury_pressure=dict(layers.get("injury_pressure_normalized") or {}),
        te_target_share_trend=te_tr,
        wr_target_share_trend=wr_tr,
        edge_pressure_trend=edge_tr,
        rb_target_share_trend=rb_tr,
        pass_rate=float(raw.get("off_pass_rate", 0.0)),
        shotgun_rate=float(raw.get("off_shotgun_rate", 0.0)),
        need_signal_policy=policy,
        draft_pick_positions=picks,
    )


def team_context_summary(ctx: TeamContext) -> Dict[str, Any]:
    top = sorted(ctx.needs.items(), key=lambda x: -x[1])[:5]
    return {
        "team": ctx.team,
        "season": ctx.season,
        "top_needs": [{"bucket": b, "score": round(v, 2)} for b, v in top],
        "scheme_highlights": {
            "pass_rate": round(ctx.pass_rate, 4),
            "shotgun_rate": round(ctx.shotgun_rate, 4),
            "te_target_share_trend": round(ctx.te_target_share_trend, 6),
            "wr_target_share_trend": round(ctx.wr_target_share_trend, 6),
            "edge_pressure_trend": round(ctx.edge_pressure_trend, 6),
        },
        "need_signal_policy": ctx.need_signal_policy,
        "draft_pick_positions": ctx.draft_pick_positions,
    }
