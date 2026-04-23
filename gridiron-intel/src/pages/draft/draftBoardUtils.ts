import type { ApiDraftProspect } from "@/lib/api.ts";

export type TableSortKey =
  | "player_name"
  | "prospect_score"
  | "final_draft_score"
  | "model_rank"
  | "consensus_rank"
  | "reach_risk"
  | "market_value_score";

export function sortProspects(rows: ApiDraftProspect[], key: TableSortKey, dir: "asc" | "desc"): ApiDraftProspect[] {
  const mul = dir === "desc" ? -1 : 1;
  const num = (v: number | null | undefined, nullSentinel: number) =>
    v == null || Number.isNaN(Number(v)) ? nullSentinel : Number(v);

  return [...rows].sort((a, b) => {
    if (key === "player_name") {
      const c = a.player_name.localeCompare(b.player_name);
      return dir === "desc" ? -c : c;
    }
    if (key === "model_rank" || key === "consensus_rank") {
      const va = num(key === "model_rank" ? a.model_rank : a.consensus_rank, 1e6);
      const vb = num(key === "model_rank" ? b.model_rank : b.consensus_rank, 1e6);
      return (va - vb) * mul;
    }
    if (key === "reach_risk") {
      const va = num(a.reach_risk, dir === "desc" ? -1e6 : 1e6);
      const vb = num(b.reach_risk, dir === "desc" ? -1e6 : 1e6);
      return (va - vb) * mul;
    }
    const va = num(
      key === "prospect_score"
        ? a.prospect_score
        : key === "final_draft_score"
          ? a.final_draft_score
          : a.market_value_score,
      dir === "desc" ? -1e6 : 1e6,
    );
    const vb = num(
      key === "prospect_score"
        ? b.prospect_score
        : key === "final_draft_score"
          ? b.final_draft_score
          : b.market_value_score,
      dir === "desc" ? -1e6 : 1e6,
    );
    return (va - vb) * mul;
  });
}

export type DraftModule =
  | "big_board"
  | "r1_projections"
  | "prospect_db"
  | "simulator"
  | "compare"
  | "model_intel"
  | "team_needs"
  | "scheme_fit"
  | "combine_lab"
  | "trend_signals";

export const DRAFT_MODULES: DraftModule[] = [
  "big_board",
  "r1_projections",
  "prospect_db",
  "simulator",
  "compare",
  "model_intel",
  "team_needs",
  "scheme_fit",
  "combine_lab",
  "trend_signals",
];

export function isDraftModule(s: string | null): s is DraftModule {
  return s != null && (DRAFT_MODULES as string[]).includes(s);
}

export type PosFilter = "ALL" | "QB" | "WR" | "RB" | "EDGE_DL" | "OT_IOL" | "DB_LB" | "TE" | "CB" | "S" | "LB";

export type BoardViewTab =
  | "consensus_board"
  | "model_board"
  | "r1_projections_tab"
  | "rmu_predictions"
  | "by_team_fit";

export function filterByPosition(rows: ApiDraftProspect[], f: PosFilter): ApiDraftProspect[] {
  if (f === "ALL") return rows;
  return rows.filter((p) => {
    const pos = (p.pos || "").toUpperCase();
    const bucket = (p.pos_bucket || "").toUpperCase();
    switch (f) {
      case "QB":
        return pos === "QB";
      case "WR":
        return pos.includes("WR");
      case "RB":
        return pos === "RB";
      case "EDGE_DL":
        return (
          ["EDGE", "DE", "DT", "IDL", "DL"].some((x) => pos.includes(x)) ||
          ["EDGE", "IDL", "DL"].some((x) => bucket.includes(x))
        );
      case "OT_IOL":
        return (
          ["OT", "IOL", "OG", "OC", "C", "G"].some((x) => pos.includes(x)) ||
          ["OT", "IOL", "IOL/OT"].some((x) => bucket.includes(x))
        );
      case "DB_LB":
        return ["CB", "S", "SAF", "FS", "SS", "NB", "LB", "ILB", "OLB"].some(
          (x) => pos.includes(x) || bucket.includes(x),
        );
      case "TE":
        return pos.includes("TE");
      case "CB":
        return pos.includes("CB");
      case "S":
        return pos === "S" || pos === "FS" || pos === "SS" || pos.includes("SAF");
      case "LB":
        return pos.includes("LB");
      default:
        return true;
    }
  });
}

export function filterByBoardTab(rows: ApiDraftProspect[], tab: BoardViewTab): ApiDraftProspect[] {
  if (tab === "r1_projections_tab") {
    const ranked = [...rows].sort((a, b) => b.final_draft_score - a.final_draft_score);
    return ranked.slice(0, 32);
  }
  return rows;
}

export function prospectPosPill(pos: string): string {
  const p = (pos || "??").toUpperCase();
  let v = "giq-pos-DEF";
  if (p.includes("QB")) v = "giq-pos-QB";
  else if (p.includes("WR")) v = "giq-pos-WR";
  else if (p === "RB") v = "giq-pos-RB";
  else if (p.includes("TE")) v = "giq-pos-TE";
  else if (p.includes("EDGE") || p === "DE") v = "giq-pos-EDGE";
  else if (p.includes("OT")) v = "giq-pos-OT";
  else if (p.includes("CB")) v = "giq-pos-CB";
  else if (p === "S" || p === "FS" || p === "SS") v = "giq-pos-S";
  else if (p.includes("LB")) v = "giq-pos-LB";
  return `giq-pos-badge ${v}`;
}
