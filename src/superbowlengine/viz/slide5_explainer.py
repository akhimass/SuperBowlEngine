"""
Slide 5 explainer: tall portrait layout (long square) to avoid overlay.

Single column of sections with generous spacing; each section has its own axis.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.image as mimage
import pandas as pd

from superbowlengine.features.keys import TeamKeys
from superbowlengine.analysis.rank_keys import get_ranks_meta

KEY_ORDER = ["TOP", "TO", "BIG", "3D", "RZ"]
# Short labels so Key column shows fully (no truncation) with colWidths[0]=0.52
KEY_LABELS = {
    "TOP": "TOP (min/g)",
    "TO": "TO (giveaways/g)",
    "BIG": "BIG (plays/g)",
    "3D": "3D (%)",
    "RZ": "RZ TD (%)",
}
TEAM_COLORS: Dict[str, str] = {
    "SEA": "#69BE28",
    "NE": "#C60C30",
    "SF": "#AA0000",
    "KC": "#E31837",
}
DEFAULT_COLOR_A = "#69BE28"
DEFAULT_COLOR_B = "#C60C30"

# Typography (pt) — per-section, no free-floating overlap
TITLE_PT = 45
SUBTITLE_PT = 27
CARD_LABEL_PT = 23
CARD_WINNER_PT = 40
CARD_BODY_PT = 25
TABLE_TITLE_PT = 36
TABLE_HEADER_PT = 29
TABLE_CELL_PT = 26
FOOTNOTE_PT = 23
BAR_LABEL_PT = 26
AXIS_LABEL_PT = 25
AXIS_TICK_PT = 22

# Logo filenames for scoreboard (team abbr -> filename under logo_dir)
TEAM_LOGO_FILES: Dict[str, str] = {
    "SEA": "seahawkslogo.png",
    "NE": "patriotslogo.png",
}


def _get_explanation(pred: dict) -> Any:
    return pred.get("explanation") or pred


def _key_value(keys: TeamKeys, key: str) -> str:
    if key == "TOP":
        return f"{keys.top_min:.1f}"
    if key == "TO":
        return f"{float(keys.turnovers):.1f}"
    if key == "BIG":
        return f"{float(keys.big_plays):.1f}"
    if key == "3D":
        return f"{keys.third_down_pct:.1f}%"
    if key == "RZ":
        return f"{keys.redzone_td_pct:.1f}%"
    return ""


def _context_line(
    team_a: str,
    team_b: str,
    margin_table: Dict[str, float],
    per_game_a: Optional[pd.DataFrame],
    per_game_b: Optional[pd.DataFrame],
) -> str:
    """Single line for footnote: Context: [SOS] | [dampened games]."""
    parts: List[str] = []
    sos_z = margin_table.get("SOS_z") if margin_table else None
    if sos_z is not None:
        if sos_z > 0:
            parts.append(f"{team_a} tougher opponents (SOS_z {sos_z:+.2f})")
        else:
            parts.append(f"{team_b} tougher opponents (SOS_z {-sos_z:+.2f})")
    for team, per_game in [(team_a, per_game_a), (team_b, per_game_b)]:
        if per_game is None or per_game.empty or "weight" not in per_game.columns:
            continue
        damp = (per_game["weight"] < 1.0).sum()
        if damp > 0:
            opps = per_game.loc[per_game["weight"] < 1.0, "opp"].tolist() if "opp" in per_game.columns else []
            opp_str = ", ".join(str(o) for o in opps[:2]) + ("..." if len(opps) > 2 else "")
            parts.append(f"{team} dampened game: {opp_str} (opp TO ≥4)")
    if not parts:
        return "Context: Opponent-adjusted per-game keys."
    return "Context: " + " | ".join(parts)


def render_slide5_explainer(
    pred: dict,
    keys_a: TeamKeys,
    keys_b: TeamKeys,
    per_game_a: Optional[pd.DataFrame] = None,
    per_game_b: Optional[pd.DataFrame] = None,
    ranks: Optional[Dict[str, Dict[str, float]]] = None,
    outpath: str = "outputs/slide5_explainer.png",
    year: Optional[int] = None,
    mode: str = "opp_weighted",
    show_percentiles: bool = False,
    logo_dir: Optional[Path] = None,
) -> str:
    """
    Render a slide-ready explainer PNG as a tall portrait (long square) to avoid overlay.
    Figure size 10x16 inches; sections stacked with generous spacing.
    """
    path = Path(outpath)
    path.parent.mkdir(parents=True, exist_ok=True)

    expl = _get_explanation(pred)
    if isinstance(expl, dict):
        key_winners = expl.get("key_winners") or {}
        margin_table = expl.get("margin_table") or {}
        top_3_drivers = pred.get("top_3_drivers") or (expl.get("driver_ranking") or [])[:3]
    else:
        key_winners = getattr(expl, "key_winners", None) or pred.get("key_winners") or {}
        margin_table = getattr(expl, "margin_table", None) or {}
        top_3_drivers = pred.get("top_3_drivers") or (getattr(expl, "driver_ranking", None) or [])[:3]
    p_a = pred.get("p_team_a_win", pred.get("p_sea_win", 0.5))
    p_b = pred.get("p_team_b_win", pred.get("p_ne_win", 0.5))
    winner = pred.get("predicted_winner", "")
    team_a = keys_a.team
    team_b = keys_b.team
    color_a = TEAM_COLORS.get(str(team_a).upper(), DEFAULT_COLOR_A)
    color_b = TEAM_COLORS.get(str(team_b).upper(), DEFAULT_COLOR_B)
    keys_a_won = [k for k in KEY_ORDER if key_winners.get(k) == team_a]
    keys_b_won = [k for k in KEY_ORDER if key_winners.get(k) == team_b]
    tied_keys_list = pred.get("tied_keys") or [k for k in KEY_ORDER if key_winners.get(k) == "TIE"]
    n_a, n_b = len(keys_a_won), len(keys_b_won)
    ties_count = pred.get("ties", len(tied_keys_list))
    year_str = str(year) if year is not None else ""
    subtitle = f"{team_a} vs {team_b} | POST {year_str} | mode={mode}".strip(" |")

    # Tall portrait with extra row for scoreboard between win prob and predicted winner
    fig = plt.figure(figsize=(10, 18), dpi=220)
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(
        nrows=39,
        ncols=12,
        left=0.05,
        right=0.95,
        top=0.97,
        bottom=0.03,
        wspace=0.35,
        hspace=0.5,
    )

    # 1. Header (rows 0-4)
    ax_header = fig.add_subplot(gs[0:4, 0:12])
    ax_header.axis("off")
    ax_header.text(0.5, 0.78, "Super Bowl LX Prediction", ha="center", va="center", fontsize=TITLE_PT - 2, fontweight="bold", transform=ax_header.transAxes)
    ax_header.text(0.5, 0.48, "Opponent-Adjusted 5 Keys", ha="center", va="center", fontsize=TITLE_PT - 6, fontweight="bold", transform=ax_header.transAxes)
    ax_header.text(0.5, 0.18, subtitle, ha="center", va="center", fontsize=SUBTITLE_PT, transform=ax_header.transAxes)

    # 2. Win probability only (rows 5-8) — no score text here to avoid overlay
    ax_prob = fig.add_subplot(gs[5:8, 0:12])
    ax_prob.set_xlim(0, 100)
    ax_prob.set_ylim(-5, 105)
    y_a, y_b = 70, 30
    bar_height = 18
    ax_prob.barh(y_a, p_a * 100, height=bar_height, color=color_a, align="center")
    ax_prob.barh(y_b, p_b * 100, height=bar_height, color=color_b, align="center")
    ax_prob.set_xticks([0, 25, 50, 75, 100])
    ax_prob.set_xticklabels(["0", "25", "50", "75", "100"], fontsize=AXIS_TICK_PT)
    ax_prob.set_yticks([y_a, y_b])
    ax_prob.set_yticklabels([team_a, team_b], fontsize=24)
    ax_prob.set_xlabel("Win Probability", fontsize=AXIS_LABEL_PT)
    ax_prob.text(min(p_a * 100 + 1, 98), y_a, f"{p_a * 100:.1f}%", ha="left", va="center", fontsize=BAR_LABEL_PT, fontweight="bold")
    ax_prob.text(min(p_b * 100 + 1, 98), y_b, f"{p_b * 100:.1f}%", ha="left", va="center", fontsize=BAR_LABEL_PT, fontweight="bold")
    ax_prob.spines["top"].set_visible(False)
    ax_prob.spines["right"].set_visible(False)
    ax_prob.tick_params(axis="both", labelsize=AXIS_TICK_PT)

    # 3. Scoreboard (rows 10-13): logos + score in a box, no "Proj:" text — shifted down a bit
    predicted_score = pred.get("predicted_score") or {}
    score_ci = pred.get("score_ci") or {}
    ax_scoreboard = fig.add_subplot(gs[10:13, 0:12])
    ax_scoreboard.set_xlim(0, 1)
    ax_scoreboard.set_ylim(0, 1)
    ax_scoreboard.axis("off")
    if predicted_score and team_a in predicted_score and team_b in predicted_score:
        sd = score_ci.get("margin_sd")
        pm = int(sd) if sd is not None else 7
        sa, sb = predicted_score[team_a], predicted_score[team_b]
        # Outer box for scoreboard
        box = mpatches.FancyBboxPatch(
            (0.08, 0.1), 0.84, 0.8,
            boxstyle="round,pad=0.02,rounding_size=0.04",
            facecolor="#f0f0f0", edgecolor="#333", linewidth=2,
            transform=ax_scoreboard.transAxes,
        )
        ax_scoreboard.add_patch(box)
        # Left logo (team_a)
        logo_path_a = logo_dir and (Path(logo_dir) / TEAM_LOGO_FILES.get(team_a, ""))
        if logo_path_a and Path(logo_path_a).exists():
            img_a = mimage.imread(logo_path_a)
            ax_scoreboard.imshow(img_a, extent=[0.10, 0.28, 0.25, 0.75], aspect="auto", zorder=1)
        # Right logo (team_b)
        logo_path_b = logo_dir and (Path(logo_dir) / TEAM_LOGO_FILES.get(team_b, ""))
        if logo_path_b and Path(logo_path_b).exists():
            img_b = mimage.imread(logo_path_b)
            ax_scoreboard.imshow(img_b, extent=[0.72, 0.90, 0.25, 0.75], aspect="auto", zorder=1)
        # Score in center box (no team text, just numbers) — y positions lowered for clearance from top
        score_box = mpatches.FancyBboxPatch(
            (0.36, 0.22), 0.28, 0.56,
            boxstyle="round,pad=0.02,rounding_size=0.03",
            facecolor="white", edgecolor="#333", linewidth=1.5,
            transform=ax_scoreboard.transAxes,
        )
        ax_scoreboard.add_patch(score_box)
        ax_scoreboard.text(0.5, 0.54, f"{sa}  –  {sb}", ha="center", va="center", fontsize=32, fontweight="bold", transform=ax_scoreboard.transAxes)
        ax_scoreboard.text(0.5, 0.30, f"(±{pm})", ha="center", va="center", fontsize=18, transform=ax_scoreboard.transAxes)

    # 4. Predicted winner card (rows 13-21) — shifted down with scoreboard, clear box
    ax_card = fig.add_subplot(gs[13:21, 0:12])
    ax_card.set_xlim(0, 1)
    ax_card.set_ylim(0, 1)
    ax_card.axis("off")
    # Predicted winner in a clear box
    card = mpatches.FancyBboxPatch(
        (0.04, 0.06), 0.92, 0.88,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        facecolor="#f8f8f8", edgecolor="#333", linewidth=2,
        transform=ax_card.transAxes,
    )
    ax_card.add_patch(card)
    # More vertical spacing so predicted winner block is not compressed
    ax_card.text(0.5, 0.85, "Predicted Winner", ha="center", va="center", fontsize=CARD_LABEL_PT, transform=ax_card.transAxes)
    ax_card.text(0.5, 0.68, winner, ha="center", va="center", fontsize=CARD_WINNER_PT, fontweight="bold", transform=ax_card.transAxes)
    ax_card.text(0.5, 0.54, f"Win Prob: {team_a} {p_a * 100:.1f}% | {team_b} {p_b * 100:.1f}%", ha="center", va="center", fontsize=CARD_BODY_PT, transform=ax_card.transAxes)
    keys_line_a = f"Keys: {team_a} {n_a}/5" + (f" ({', '.join(keys_a_won)})" if keys_a_won else "")
    ax_card.text(0.5, 0.40, keys_line_a, ha="center", va="center", fontsize=CARD_BODY_PT, transform=ax_card.transAxes)
    keys_line_b = f"{team_b} {n_b}/5" + (f" ({', '.join(keys_b_won)})" if keys_b_won else "")
    if ties_count > 0:
        keys_line_b += f" | Ties {ties_count} ({', '.join(tied_keys_list)})"
    ax_card.text(0.5, 0.28, keys_line_b, ha="center", va="center", fontsize=CARD_BODY_PT, transform=ax_card.transAxes)
    drivers_str = " | ".join(f"{n} {c:+.2f}" for n, c in top_3_drivers[:2]) if top_3_drivers else "—"
    ax_card.text(0.5, 0.14, f"Drivers: {drivers_str}", ha="center", va="center", fontsize=CARD_LABEL_PT, transform=ax_card.transAxes)

    # 5. Table title (rows 22-24)
    ax_table_title = fig.add_subplot(gs[22:24, 0:12])
    ax_table_title.axis("off")
    ax_table_title.text(0.5, 0.5, "5 Keys Comparison (Opponent-adjusted per game)", ha="center", va="center", fontsize=TABLE_TITLE_PT, fontweight="bold", transform=ax_table_title.transAxes)

    # 6. Table (rows 24-36) — full width, more room per column
    ax_table = fig.add_subplot(gs[24:36, 0:12])
    ax_table.axis("off")
    table_data: List[List[str]] = []
    for key in KEY_ORDER:
        val_a = _key_value(keys_a, key)
        val_b = _key_value(keys_b, key)
        w = key_winners.get(key, "")
        win_str = w if w in (team_a, team_b) else "TIE"
        table_data.append([KEY_LABELS.get(key, key), val_a, val_b, win_str])
    # Wider columns: Key + three value columns with more room each
    col_widths = [0.38, 0.22, 0.22, 0.18]
    tbl = ax_table.table(
        cellText=table_data,
        colLabels=["Key", team_a, team_b, "Winner"],
        loc="center",
        bbox=[0.0, 0.0, 1.0, 1.0],
        colWidths=col_widths,
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(TABLE_CELL_PT)
    tbl.scale(1.0, 2.0)
    for (r, c), cell in tbl.get_celld().items():
        t = cell.get_text()
        t.set_ha("center")
        t.set_va("center")
        cell.set_text_props(color="black")
        if r == 0:
            cell.set_text_props(fontweight="bold", fontsize=TABLE_HEADER_PT)
            cell.set_facecolor("#e0e0e0")
        else:
            if c == 3:
                cell.set_text_props(fontweight="bold")
                cell.set_facecolor("#f0f0f0")
            else:
                cell.set_facecolor("white")
        cell.set_edgecolor("#333")
        cell.set_linewidth(1.5)

    # 7. Footnote (rows 37-39)
    ax_foot = fig.add_subplot(gs[37:39, 0:12])
    ax_foot.axis("off")
    ctx = _context_line(team_a, team_b, margin_table, per_game_a, per_game_b)
    if show_percentiles:
        meta = get_ranks_meta(year=year, mode=mode)
        ctx = ctx + "  |  Percentile = league-relative (not head-to-head). " + meta["population"] + "; " + meta["metric_definition"]
    ax_foot.text(0.5, 0.5, ctx, ha="center", va="center", fontsize=FOOTNOTE_PT, transform=ax_foot.transAxes)

    plt.savefig(path, dpi=220, bbox_inches="tight", pad_inches=0.35, facecolor="white")
    plt.close(fig)
    return str(path.resolve())
