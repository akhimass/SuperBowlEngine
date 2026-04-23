/**
 * Full-pool Round-1 mock scoring: nflverse-backed combine grades + consensus /
 * market signals, ESPN-declared team needs, positional-value priors (aligned
 * with ``POSITIONAL_VALUE`` in ``src/gridironiq/draft/positions.py``), and an
 * RMU first-round probability overlay for QB/WR/RB when names line up.
 *
 * Division-level “arms race” boosts are not applied here yet — the draft API
 * only builds division intel for the single ``team`` query; a future pass can
 * hydrate per–on-clock-team context server-side.
 */

import type { ApiDraftProspect } from "@/lib/api.ts";
import type { NflDraftPick, R1BoardRow } from "@/lib/engine.ts";
import { normalizeName } from "@/lib/rmu.ts";

/** Mirrors ``src/gridironiq/draft/positions.py`` POSITIONAL_VALUE. */
export const POSITIONAL_VALUE: Record<string, number> = {
  QB: 1.18,
  OT: 1.1,
  EDGE: 1.12,
  CB: 1.06,
  WR: 1.05,
  TE: 1.02,
  IOL: 1.04,
  IDL: 1.03,
  LB: 1.02,
  SAF: 1.03,
  RB: 0.93,
  ST: 0.85,
  UNK: 1.0,
};

/** Map RMU / board position strings to ESPN need tokens (QB, WR, OL, …). */
export function r1PositionToNeedToken(pos: string | null | undefined): string {
  const p = (pos ?? "").toUpperCase();
  if (p === "QB") return "QB";
  if (p === "WR") return "WR";
  if (p === "RB" || p === "FB") return "RB";
  if (p === "TE") return "TE";
  if (p === "OT" || p === "OG" || p === "C" || p === "IOL" || p.includes("OL")) return "OL";
  if (p === "DE" || p === "EDGE" || p.includes("EDGE")) return "EDGE";
  if (p === "DT" || p === "NT" || p === "IDL" || p.includes("DL")) return "DL";
  if (p === "CB") return "CB";
  if (p === "S" || p === "FS" || p === "SS" || p === "SAF") return "S";
  if (p.includes("LB")) return "LB";
  return p;
}

/** True when an ESPN need string matches a pipeline ``pos_bucket``. */
export function espnNeedMatchesBucket(need: string, posBucket: string): boolean {
  const n = (need || "").toUpperCase();
  const b = (posBucket || "").toUpperCase();
  if (n === "QB") return b === "QB";
  if (n === "WR") return b === "WR";
  if (n === "RB") return b === "RB";
  if (n === "TE") return b === "TE";
  if (n === "OL") return b === "OT" || b === "IOL";
  if (n === "DL") return b === "IDL";
  if (n === "EDGE") return b === "EDGE";
  if (n === "LB") return b === "LB";
  if (n === "CB") return b === "CB";
  if (n === "S") return b === "SAF";
  return false;
}

export function findR1Overlay(r1Board: R1BoardRow[], playerName: string): R1BoardRow | undefined {
  const key = normalizeName(playerName);
  return r1Board.find((r) => normalizeName(r.name) === key);
}

function positionalEarlyPremium(overallPick: number, posBucket: string): number {
  const pv = POSITIONAL_VALUE[posBucket] ?? POSITIONAL_VALUE.UNK;
  const delta = pv - 1.0;
  if (overallPick <= 8) return delta * 0.12;
  if (overallPick <= 16) return delta * 0.07;
  if (overallPick <= 32) return delta * 0.04;
  return delta * 0.02;
}

function needLineBonus(
  orderedNeeds: string[],
  posBucket: string,
): { bonus: number; idx: number } {
  for (let i = 0; i < orderedNeeds.length; i++) {
    if (espnNeedMatchesBucket(orderedNeeds[i]!, posBucket)) {
      return { bonus: 0.19 - 0.036 * i, idx: i };
    }
  }
  return { bonus: 0, idx: -1 };
}

function buildTalentNormalizer(all: ApiDraftProspect[]): (p: ApiDraftProspect) => number {
  const scores = all.map((p) => p.prospect_score);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  if (!(max > min)) return () => 0.5;
  return (p: ApiDraftProspect) => (p.prospect_score - min) / (max - min);
}

function buildMarketNormalizer(all: ApiDraftProspect[]): (p: ApiDraftProspect) => number {
  const ranks = all
    .map((p) => p.consensus_rank)
    .filter((x): x is number => typeof x === "number" && x > 0);
  const maxR = ranks.length ? Math.max(...ranks, 320) : 320;
  const n = Math.max(all.length, 2);
  return (p: ApiDraftProspect) => {
    if (typeof p.consensus_rank === "number" && p.consensus_rank > 0) {
      return 1 - Math.min(p.consensus_rank, maxR) / maxR;
    }
    if (typeof p.avg_pick_position === "number" && p.avg_pick_position > 0) {
      return 1 - Math.min(p.avg_pick_position, 260) / 260;
    }
    const mr = p.model_rank ?? n;
    return 1 - Math.min(Math.max(mr - 1, 0), n - 1) / (n - 1);
  };
}

export interface MockDraftScoreParts {
  talent: number;
  market: number;
  need: number;
  positional: number;
  rmu: number;
  total: number;
}

export interface MockDraftPickRowFull {
  slot: NflDraftPick;
  needs: string[];
  selected: ApiDraftProspect | null;
  fitRank: number | null;
  alternates: ApiDraftProspect[];
  parts: MockDraftScoreParts | null;
  r1Overlay: R1BoardRow | undefined;
}

/** Rounds 1–3 pick count in the encoded 2026 order (32 + 32 + 36). */
export const MOCK_DRAFT_3R_PICKS = 100;

/**
 * Simulate each draft slot (typically rounds 1–3) using the **full**
 * combine-class board. Each selection is the highest composite score among
 * players not yet taken.
 */
export function buildMockDraftFullPoolRows(
  slots: NflDraftPick[],
  teamNeeds: Record<string, string[]>,
  allProspects: ApiDraftProspect[],
  r1Board: R1BoardRow[],
): MockDraftPickRowFull[] {
  const talentN = buildTalentNormalizer(allProspects);
  const marketN = buildMarketNormalizer(allProspects);
  const taken = new Set<string>();
  const out: MockDraftPickRowFull[] = [];

  for (const slot of slots) {
    const needs = teamNeeds[slot.team] ?? [];
    const pool = allProspects.filter((p) => !taken.has(p.player_id));
    const scored = pool.map((cand) => {
      const { bonus: needB, idx: needIdx } = needLineBonus(needs, cand.pos_bucket);
      const r1 = findR1Overlay(r1Board, cand.player_name);
      const rmu = r1 ? 0.44 * (r1.r1_probability ?? 0) : 0;
      const posEarly = positionalEarlyPremium(slot.overall, cand.pos_bucket);
      const t = talentN(cand);
      const m = marketN(cand);
      const total = 0.34 * t + 0.24 * m + needB + posEarly + rmu;
      const parts: MockDraftScoreParts = {
        talent: t,
        market: m,
        need: needB,
        positional: posEarly,
        rmu,
        total,
      };
      return { cand, total, needIdx, parts, r1 };
    });
    scored.sort((a, b) => b.total - a.total);
    const top = scored[0];
    if (top) taken.add(top.cand.player_id);
    out.push({
      slot,
      needs,
      selected: top?.cand ?? null,
      fitRank: top ? (top.needIdx === -1 ? null : top.needIdx + 1) : null,
      alternates: scored.slice(1, 3).map((s) => s.cand),
      parts: top?.parts ?? null,
      r1Overlay: top?.r1,
    });
  }
  return out;
}

export interface RmuMockLanding {
  name: string;
  position: string;
  r1_probability: number | null;
  confidence: string | null;
  model_r1_flag: boolean | null;
  mock_overall: number | null;
  mock_round: number | null;
  mock_team: string | null;
  /** Selected in rounds 1–3 mock; overall slot vs first round. */
  band: "IN_R1" | "R2_R3" | "OUT";
}

/** For every RMU-board prospect, where the 3-round composite mock took them. */
export function buildRmuMockLandings(
  r1Board: R1BoardRow[],
  picks: Array<{ slot: NflDraftPick; selectedName: string | null }>,
): RmuMockLanding[] {
  const hit = new Map<
    string,
    { overall: number; round: number; team: string }
  >();
  for (const { slot, selectedName } of picks) {
    if (!selectedName) continue;
    hit.set(normalizeName(selectedName), {
      overall: slot.overall,
      round: slot.round,
      team: slot.team,
    });
  }
  return r1Board.map((prospect) => {
    const h = hit.get(normalizeName(prospect.name));
    const mock_overall = h?.overall ?? null;
    let band: RmuMockLanding["band"];
    if (mock_overall == null) band = "OUT";
    else if (mock_overall <= 32) band = "IN_R1";
    else band = "R2_R3";
    return {
      name: prospect.name,
      position: prospect.position,
      r1_probability: prospect.r1_probability ?? null,
      confidence: prospect.confidence ?? null,
      model_r1_flag: prospect.r1_predicted === 1,
      mock_overall,
      mock_round: h?.round ?? null,
      mock_team: h?.team ?? null,
      band,
    };
  });
}

/** Skill-only fallback (RMU rows) — same need-weighting as before. */
export function buildMockDraftSkillOnlyRows(
  round1Slots: NflDraftPick[],
  teamNeeds: Record<string, string[]>,
  r1BoardSorted: R1BoardRow[],
): Array<{
  slot: NflDraftPick;
  needs: string[];
  selected: R1BoardRow | null;
  fitRank: number | null;
  alternates: R1BoardRow[];
}> {
  const taken = new Set<string>();
  const rows: Array<{
    slot: NflDraftPick;
    needs: string[];
    selected: R1BoardRow | null;
    fitRank: number | null;
    alternates: R1BoardRow[];
  }> = [];

  for (const slot of round1Slots) {
    const needs = teamNeeds[slot.team] ?? [];
    const pool = r1BoardSorted.filter((r) => !taken.has(r.name));
    const scored = pool.map((cand) => {
      const token = r1PositionToNeedToken(cand.position);
      const needIdx = needs.indexOf(token);
      const needBonus = needIdx === -1 ? 0 : 0.2 - 0.04 * needIdx;
      return { cand, score: (cand.r1_probability ?? 0) + needBonus, needIdx };
    });
    scored.sort((a, b) => b.score - a.score);
    const top = scored[0];
    const selected = top?.cand ?? null;
    if (selected) taken.add(selected.name);
    rows.push({
      slot,
      needs,
      selected,
      fitRank: top ? (top.needIdx === -1 ? null : top.needIdx + 1) : null,
      alternates: scored.slice(1, 3).map((s) => s.cand),
    });
  }
  return rows;
}
