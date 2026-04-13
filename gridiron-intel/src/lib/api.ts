import type { MatchupResult } from "@/data/mockData";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

// --- Team logo manifest (GET) ---

export interface ApiTeamLogoEntry {
  abbr: string;
  display_name: string;
  normalized_name: string;
  filename: string;
  path: string;
}

export interface ApiTeamLogoManifest {
  teams: Record<string, ApiTeamLogoEntry>;
  unmatched: string[];
  duplicates: Record<string, string[]>;
}

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request to ${path} failed with status ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function getTeamLogos(): Promise<ApiTeamLogoManifest> {
  return getJson<ApiTeamLogoManifest>("/api/assets/team-logos");
}

export interface ApiMatchupResponse {
  team_a: string;
  team_b: string;
  season: number;
  mode: string;
  win_probability: number; // 0–1
  predicted_winner: string;
  projected_score: Record<string, number>;
  projected_margin?: number | null;
  projected_total?: number | null;
  team_efficiency_edges?: Record<string, unknown> | null;
  key_edges: Record<string, number>;
  keys_won: Record<string, number>;
  top_drivers: [string, number][];
}

export interface ApiQBCompareResponse {
  qb_a: string;
  team_a: string;
  qb_b: string;
  team_b: string;
  season: number;
  sustain_score: Record<string, number>;
  situational_score: Record<string, number>;
  offscript_score: Record<string, number>;
  total_score: Record<string, number>;
  avg_def_z: Record<string, number>;
}

export interface ApiScoutingReport {
  summary: string;
  team_a_strengths: string[];
  team_b_strengths: string[];
  offensive_profile: Record<string, Record<string, number>>;
  defensive_profile: Record<string, number>;
  qb_impact: Record<string, unknown>;
  prediction_explanation: string;
  confidence_notes: string[];
  team_a: string;
  team_b: string;
  season: number;
  win_probability: number;
  predicted_winner: string;
  projected_score: Record<string, number>;
  projected_margin?: number | null;
  projected_total?: number | null;
  team_efficiency_edges?: Record<string, unknown> | null;
  keys_won: Record<string, number>;
  top_drivers: [string, number][];
  executive_summary?: {
    headline?: string;
    detail?: string;
    projected_margin?: number;
  };
  risk_factors?: string[];
  ai_statistician?: ApiAiExplanation;
}

export interface ApiBacktestRun {
  season: number;
  week: string;
  home_team: string;
  away_team: string;
  predicted_win_prob: number;
  predicted_score_home: number;
  predicted_score_away: number;
  actual_score_home: number;
  actual_score_away: number;
  correct: boolean;
}

export interface ApiBacktestResponse {
  accuracy: number;
  average_score_error: number;
  calibration_data: ApiBacktestRun[];
}

export interface ApiScheduleGame {
  game_id: string;
  season: number;
  week: number | string | null;
  season_type: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  predicted_winner: string | null;
  predicted_score: Record<string, number>;
  win_probability: number | null;
  correct: boolean;
}

export interface ApiScheduleResponse {
  season: number;
  phase: string;
  games: ApiScheduleGame[];
}

export interface ApiMatchupReportAsset {
  type: string;
  team?: string;
  caption?: string;
  path?: string | null;
  url?: string | null;
  [key: string]: unknown;
}

export interface ApiMatchupReportResponse {
  summary: string;
  team_a: string;
  team_b: string;
  season: number;
  win_probability: number;
  predicted_winner: string;
  projected_score: Record<string, number>;
  situational_edges: Record<string, unknown>;
  offense_vs_defense: Record<string, unknown>;
  report_assets: ApiMatchupReportAsset[];
}

export interface ApiAiExplanation {
  summary: string;
  top_3_reasons: string[];
  what_matters_most: string;
  what_could_flip_it: string;
  why_prediction_was_right_or_wrong?: string | null;
  confidence_note?: string | null;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request to ${path} failed with status ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function runMatchup(season: number, teamA: string, teamB: string, mode: string = "opp_weighted"): Promise<MatchupResult> {
  const data = await postJson<ApiMatchupResponse>("/api/matchup/run", {
    season,
    team_a: teamA,
    team_b: teamB,
    mode,
  });

  let winProbA = Math.round(data.win_probability * 1000) / 10;
  let winProbB = Math.round((1 - data.win_probability) * 1000) / 10;
  // Clamp for UX so we never show literal 0% / 100%
  if (winProbA <= 0) winProbA = 0.1;
  if (winProbA >= 100) winProbA = 99.9;
  if (winProbB <= 0) winProbB = 0.1;
  if (winProbB >= 100) winProbB = 99.9;
  const scoreA = data.projected_score[teamA] ?? 0;
  const scoreB = data.projected_score[teamB] ?? 0;

  const edges = Object.entries(data.key_edges ?? {}).map(([key, margin]) => {
    let advantage: "A" | "B" | "EVEN" = "EVEN";
    if (margin > 0.5) advantage = "A";
    else if (margin < -0.5) advantage = "B";
    const magnitude = Math.round(Math.abs(margin) * 10) / 10;
    const category: "offense" | "defense" | "qb" | "situational" =
      key === "SOS_z" ? "situational" : key === "TOP" || key === "BIG" || key === "3D" || key === "RZ" ? "offense" : "situational";
    return {
      label: key,
      advantage,
      magnitude,
      category,
    };
  });

  const LABELS: Record<string, string> = {
    TOP: "Time of Possession",
    TO: "Turnover Margin",
    BIG: "Explosive Plays",
    "3D": "3rd Down Conversion Rate",
    RZ: "Red Zone TD %",
    SOS_z: "Strength of Schedule",
    DGI: "Drive/Game Impact",
  };

  const topDrivers = (data.top_drivers ?? []).map(([key, contrib]) => {
    const edge = edges.find((e) => e.label === key);
    const label = LABELS[key] ?? key;
    const dir = contrib >= 0 ? "favors" : "favors";
    const team =
      edge?.advantage === "A" ? teamA : edge?.advantage === "B" ? teamB : data.predicted_winner ?? teamA;
    const magnitude = edge ? `${edge.magnitude.toFixed(1)} pts` : `${contrib.toFixed(2)} units`;
    return `${label}: ${dir} ${team} (${magnitude} edge)`;
  });

  const scoutingReport = `## Matchup Overview

${teamA} vs ${teamB}, season ${data.season}. Model win probability for ${teamA} is ${winProbA.toFixed(
    1,
  )}%, driven primarily by differences in the five keys (TOP, turnovers, big plays, 3rd down, red zone) and schedule strength.

## Key Drivers

- ${topDrivers.join("\n- ")}`;

  return {
    teamA,
    teamB,
    winProbA,
    winProbB,
    projectedScoreA: scoreA,
    projectedScoreB: scoreB,
    projectedMargin: typeof data.projected_margin === "number" ? data.projected_margin : undefined,
    projectedTotal: typeof data.projected_total === "number" ? data.projected_total : undefined,
    efficiencyEdges: data.team_efficiency_edges ?? undefined,
    confidence: winProbA,
    edges,
    metrics: [],
    qbComparison: {
      qbA: { name: teamA, epaPerPlay: 0, cpoe: 0, pressuredRate: 0, aggPct: 0 },
      qbB: { name: teamB, epaPerPlay: 0, cpoe: 0, pressuredRate: 0, aggPct: 0 },
    },
    scoutingReport,
    topDrivers,
  };
}

export async function getMatchupReport(
  season: number,
  teamA: string,
  teamB: string,
): Promise<ApiScoutingReport> {
  return postJson<ApiScoutingReport>("/api/matchup/report", {
    season,
    team_a: teamA,
    team_b: teamB,
    mode: "opp_weighted",
  });
}

export async function getFullMatchupReport(
  season: number,
  teamA: string,
  teamB: string,
  mode: string,
  generateHeatmaps: boolean = true,
): Promise<ApiMatchupReportResponse> {
  return postJson<ApiMatchupReportResponse>("/api/report/matchup", {
    season,
    team_a: teamA,
    team_b: teamB,
    mode,
    generate_heatmaps: generateHeatmaps,
  });
}

// --- Draft Decision Engine (nflverse-backed) ---

export interface ApiDraftRadar {
  athleticism: number;
  production: number;
  efficiency: number;
  scheme_fit: number;
  team_need: number;
}

export interface ApiDraftProspect {
  player_id: string;
  player_name: string;
  pos: string;
  pos_bucket: string;
  school: string;
  combine_season: number;
  prospect_score: number;
  team_need_score: number;
  scheme_fit_score: number;
  final_draft_score: number;
  radar: ApiDraftRadar;
  score_breakdown: {
    prospect: {
      prospect_score: number;
      athletic_score: number;
      production_score: number;
      efficiency_score: number;
      age_adjustment: number;
      production_source: string;
    };
    fusion: Record<string, number>;
    scheme_fit_detail: Record<string, unknown>;
    cfb?: Record<string, unknown> | null;
  };
  forty?: number | null;
  vertical?: number | null;
  bench?: number | null;
  broad_jump?: number | null;
  cone?: number | null;
  shuttle?: number | null;
  /** Model order on this board (1 = top graded). */
  model_rank?: number | null;
  consensus_rank?: number | null;
  avg_pick_position?: number | null;
  consensus_rank_variance?: number | null;
  market_value_score?: number | null;
  /** model_rank − consensus_rank when consensus exists. */
  reach_risk?: number | null;
  consensus_boards_matched?: number | null;
}

export interface ApiDraftBoard {
  team: string;
  combine_season: number;
  eval_season: number;
  cfb_season?: number;
  team_needs: Record<string, unknown>;
  team_scheme: Record<string, unknown>;
  consensus_board: string[];
  prospects: ApiDraftProspect[];
  meta: Record<string, unknown>;
}

export async function getDraftBoard(
  team: string,
  combineSeason: number,
  evalSeason: number,
  cfbSeason?: number | null,
): Promise<ApiDraftBoard> {
  const q = new URLSearchParams({
    team,
    combine_season: String(combineSeason),
    eval_season: String(evalSeason),
  });
  if (cfbSeason != null) q.set("cfb_season", String(cfbSeason));
  return getJson<ApiDraftBoard>(`/api/draft/board?${q.toString()}`);
}

export interface ApiDraftRecommendResponse {
  simulation: {
    pick_number: number;
    n_simulations: number;
    temperature: number;
    top_k?: number;
    availability: Record<string, number>;
  };
  recommendations: Array<Record<string, unknown>>;
  four_ranking_modes?: Record<string, Array<Record<string, unknown>>>;
}

export async function postDraftRecommend(body: {
  team: string;
  combine_season: number;
  eval_season: number;
  pick_number: number;
  n_simulations?: number;
  temperature?: number;
  available_player_ids?: string[] | null;
  cfb_season?: number | null;
}): Promise<ApiDraftRecommendResponse> {
  return postJson<ApiDraftRecommendResponse>("/api/draft/recommend", body);
}

export interface ApiDraftAnalystResponse {
  best_pick_explanation: string;
  risk_analysis: string;
  alternative_picks: string[];
  if_we_pass: string;
  why_not_other_targets?: string[];
  alternate_outcomes?: string;
  provider?: string;
  fallback?: boolean;
}

export async function postDraftAnalyst(body: {
  team: string;
  combine_season: number;
  eval_season: number;
  pick_number: number;
  n_simulations?: number;
  temperature?: number;
  ai_mode?: string;
  cfb_season?: number | null;
  consensus_dirs?: string[] | null;
}): Promise<ApiDraftAnalystResponse> {
  return postJson<ApiDraftAnalystResponse>("/api/ai/draft-analyst", body);
}

export interface ApiDraftTradeScanRow {
  target_pick: number;
  ev_delta: number;
  targets_at_new_slot?: Record<string, number | null | undefined>;
}

export async function postDraftTrade(body: {
  team: string;
  combine_season: number;
  eval_season: number;
  current_pick: number;
  max_target_pick?: number;
  target_player_ids?: string[] | null;
  n_simulations?: number;
  temperature?: number;
  cfb_season?: number | null;
  consensus_dirs?: string[] | null;
}): Promise<{ team: string; current_pick: number; trade_down_scan: ApiDraftTradeScanRow[]; consensus_meta?: unknown }> {
  return postJson("/api/draft/trade", body);
}

export async function postDraftIntelligence(body: {
  team: string;
  combine_season: number;
  eval_season: number;
  pick_number: number;
  n_simulations?: number;
  temperature?: number;
  trade_target_pick?: number | null;
  cfb_season?: number | null;
  consensus_dirs?: string[] | null;
}): Promise<Record<string, unknown>> {
  return postJson("/api/draft/intelligence", body);
}

export async function aiChat(req: {
  question: string;
  context_type: "matchup" | "historical_game" | "draft";
  season?: number;
  team_a?: string;
  team_b?: string;
  mode?: string;
  game_id?: string;
  ai_mode?: string;
  draft_team?: string;
  combine_season?: number;
  eval_season?: number;
  pick_number?: number;
  cfb_season?: number | null;
}): Promise<{ answer: string; provider: string; fallback: boolean }> {
  return postJson<{ answer: string; provider: string; fallback: boolean }>("/api/ai/chat", {
    season: 2024,
    team_a: "",
    team_b: "",
    mode: "opp_weighted",
    ...req,
  });
}

export async function compareQBs(
  season: number,
  qbA: string,
  teamA: string,
  qbB: string,
  teamB: string,
): Promise<ApiQBCompareResponse> {
  return postJson<ApiQBCompareResponse>("/api/qb/compare", {
    season,
    qb_a: qbA,
    team_a: teamA,
    qb_b: qbB,
    team_b: teamB,
  });
}

export async function runBacktest(season: number): Promise<ApiBacktestResponse> {
  return postJson<ApiBacktestResponse>("/api/backtest/run", { season });
}

export async function getSchedule(season: number, phase: string): Promise<ApiScheduleResponse> {
  return getJson<ApiScheduleResponse>(`/api/schedule?season=${season}&phase=${encodeURIComponent(phase)}`);
}

export async function getAiMatchupExplanation(
  season: number,
  teamA: string,
  teamB: string,
  mode: string,
): Promise<ApiAiExplanation> {
  const res = await postJson<{ ai_statistician: ApiAiExplanation }>("/api/ai/explain-matchup", {
    season,
    team_a: teamA,
    team_b: teamB,
    mode,
  });
  return res.ai_statistician;
}

// --- Report endpoints (Python-native, migrated from R engine) ---

export interface ApiReportMatchupRequest {
  season: number;
  team_a: string;
  team_b: string;
  week?: number | null;
  mode?: string;
  generate_heatmaps?: boolean;
}

export interface ApiSituationalResponse {
  team_a: string;
  team_b: string;
  season: number;
  situational_edges: {
    team_a_tendency?: Record<string, unknown>[];
    team_b_tendency?: Record<string, unknown>[];
    team_a_success?: Record<string, unknown>[];
    team_b_success?: Record<string, unknown>[];
    note?: string;
  };
  offense_vs_defense: Record<string, unknown>;
}

export interface ApiBroadcastReportResponse {
  report_type: string;
  season: number;
  week?: number | null;
  team_a: string;
  team_b: string;
  headline: string;
  summary: string;
  headline_stats: { label: string; value: string }[];
  talking_points: string[];
  situational_tendencies_note?: string;
  top_3_storylines: string[];
  confidence_notes: string[];
}

export async function getReportMatchup(
  season: number,
  teamA: string,
  teamB: string,
  options?: { week?: number; generate_heatmaps?: boolean }
): Promise<Record<string, unknown>> {
  return postJson<Record<string, unknown>>("/api/report/matchup", {
    season,
    team_a: teamA,
    team_b: teamB,
    week: options?.week ?? null,
    mode: "opp_weighted",
    generate_heatmaps: options?.generate_heatmaps ?? false,
  });
}

export async function getReportSituational(
  season: number,
  teamA: string,
  teamB: string
): Promise<ApiSituationalResponse> {
  return postJson<ApiSituationalResponse>("/api/report/situational", {
    season,
    team_a: teamA,
    team_b: teamB,
    week: null,
    mode: "opp_weighted",
    generate_heatmaps: false,
  });
}

export async function getReportBroadcast(
  season: number,
  teamA: string,
  teamB: string
): Promise<ApiBroadcastReportResponse> {
  return postJson<ApiBroadcastReportResponse>("/api/report/broadcast", {
    season,
    team_a: teamA,
    team_b: teamB,
    week: null,
    mode: "opp_weighted",
    generate_heatmaps: false,
  });
}

