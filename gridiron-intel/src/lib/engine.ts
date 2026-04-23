/**
 * GridironIQ game-prediction engine outputs served as static JSON/CSV under `/engine/`.
 *
 * Source artifacts are produced by the Python pipeline (`outputs/model_artifacts/*`,
 * `outputs/score_model.json`, `outputs/schedule_predictions/*`, `outputs/prediction.json`,
 * `outputs/def_strength_2025.csv`, `outputs/real_predictions/r1_board_combined.csv`)
 * and copied into `gridiron-intel/public/engine/` by `scripts/run_real_draft_engine.py`.
 *
 * This hook is intentionally separate from the RMU/SAC overlay (`src/lib/rmu.ts`)
 * because the two engines target different problems:
 *   - RMU/SAC: per-prospect P(R1) for the 2026 NFL Draft (QB / WR / RB).
 *   - Game prediction: per-matchup P(win), margin, and total points.
 */
import Papa from "papaparse";
import { useQuery } from "@tanstack/react-query";

export type FeatureKey = string;

export interface WinProbModel {
  intercept: number;
  coef: Record<FeatureKey, number>;
  feature_cols: FeatureKey[];
  metrics: {
    n_rows: number;
    log_loss: number;
    brier: number;
    accuracy: number;
    p_mean: number;
    p_min: number;
    p_max: number;
    calibrated: boolean;
  };
}

export interface RegressionModel {
  intercept: number;
  coef: Record<FeatureKey, number>;
  feature_cols: FeatureKey[];
  metrics: {
    n_rows: number;
    mae: number;
    rmse: number;
    pred_min: number;
    pred_max: number;
  };
}

export interface ScoreModel {
  margin_coef: Record<string, number>;
  margin_intercept: number;
  margin_std: number;
  total_coef: Record<string, number>;
  total_intercept: number;
  total_std: number;
  feature_names: string[];
  n_samples: number;
}

export interface ScheduleGame {
  game_id: string;
  season: number;
  week: number;
  season_type: string;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  predicted_winner: string;
  predicted_score: Record<string, number>;
  win_probability: number;
  correct: boolean | null;
}

export interface SeasonAccuracy {
  season: number;
  total: number;
  correct: number;
  accuracy: number;
}

export interface DefStrengthRow {
  defteam: string;
  def_z: number;
}

export interface SamplePrediction {
  p_team_a_win: number;
  p_team_b_win: number;
  predicted_winner: string;
  predicted_score: Record<string, number>;
  predicted_margin: number;
  predicted_total: number;
  score_ci: { margin_sd: number; total_sd: number };
  top_3_drivers: Array<[string, number]>;
  logit: number;
  explanation: {
    key_winners: Record<string, string>;
    margin_table: Record<string, number>;
    driver_ranking: Array<[string, number]>;
  };
}

export interface R1BoardRow {
  overall_rank: number;
  name: string;
  position: string;
  college_team: string;
  college_conference: string;
  r1_probability: number;
  r1_predicted: 0 | 1;
  confidence: string;
  height: number | null;
  weight: number | null;
  stat_line: string;
}

export interface TeamRecord {
  team: string;
  wins: number;
  losses: number;
  ties: number;
  games_played: number;
  win_pct: number;
  point_diff: number;
}

export interface DraftPick {
  pick: number;
  team: string;
  record: TeamRecord;
}

export interface EngineData {
  winProb: WinProbModel;
  margin: RegressionModel;
  total: RegressionModel;
  score: ScoreModel;
  schedule: ScheduleGame[];
  perSeason: SeasonAccuracy[];
  overall: SeasonAccuracy;
  defStrength: DefStrengthRow[];
  sample: SamplePrediction;
  r1Board: R1BoardRow[];
  /** 2025 final standings (descending by wins). */
  standings2025: TeamRecord[];
  /** 2026 first-round pick order derived from reverse 2025 standings. */
  draftOrder2026: DraftPick[];
}

const SEASONS = [2020, 2021, 2022, 2023, 2024, 2025] as const;

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`engine: ${url} -> ${res.status}`);
  return (await res.json()) as T;
}

async function fetchCsv<T>(url: string): Promise<T[]> {
  const res = await fetch(url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`engine: ${url} -> ${res.status}`);
  const text = await res.text();
  return Papa.parse<T>(text, { header: true, dynamicTyping: true, skipEmptyLines: true }).data;
}

function summarizeAccuracy(games: ScheduleGame[]): SeasonAccuracy {
  const valid = games.filter((g) => g.correct !== null);
  const correct = valid.filter((g) => g.correct === true).length;
  return {
    season: 0,
    total: valid.length,
    correct,
    accuracy: valid.length === 0 ? 0 : correct / valid.length,
  };
}

/** Compute final standings from completed games. */
function computeStandings(games: ScheduleGame[]): TeamRecord[] {
  const map = new Map<string, { w: number; l: number; t: number; gp: number; pf: number; pa: number }>();
  for (const g of games) {
    if (g.home_score == null || g.away_score == null) continue;
    const h = g.home_team;
    const a = g.away_team;
    const hs = g.home_score;
    const as_ = g.away_score;
    if (!map.has(h)) map.set(h, { w: 0, l: 0, t: 0, gp: 0, pf: 0, pa: 0 });
    if (!map.has(a)) map.set(a, { w: 0, l: 0, t: 0, gp: 0, pf: 0, pa: 0 });
    const hr = map.get(h)!;
    const ar = map.get(a)!;
    hr.gp += 1;
    ar.gp += 1;
    hr.pf += hs;
    hr.pa += as_;
    ar.pf += as_;
    ar.pa += hs;
    if (hs > as_) {
      hr.w += 1;
      ar.l += 1;
    } else if (as_ > hs) {
      ar.w += 1;
      hr.l += 1;
    } else {
      hr.t += 1;
      ar.t += 1;
    }
  }
  const records: TeamRecord[] = [...map.entries()].map(([team, r]) => ({
    team,
    wins: r.w,
    losses: r.l,
    ties: r.t,
    games_played: r.gp,
    win_pct: r.gp === 0 ? 0 : (r.w + 0.5 * r.t) / r.gp,
    point_diff: r.pf - r.pa,
  }));
  records.sort((a, b) => {
    if (b.wins !== a.wins) return b.wins - a.wins;
    if (b.win_pct !== a.win_pct) return b.win_pct - a.win_pct;
    return b.point_diff - a.point_diff;
  });
  return records;
}

/** Reverse standings → 2026 pick order (first 32 picks = first round). */
function computeDraftOrder(standings: TeamRecord[]): DraftPick[] {
  const reversed = [...standings].sort((a, b) => {
    if (a.wins !== b.wins) return a.wins - b.wins;
    if (a.win_pct !== b.win_pct) return a.win_pct - b.win_pct;
    return a.point_diff - b.point_diff;
  });
  return reversed.slice(0, 32).map((record, i) => ({ pick: i + 1, team: record.team, record }));
}

async function loadEngine(): Promise<EngineData> {
  const [winProb, margin, total, score, sample, defStrength, r1Board, ...seasonGames] =
    await Promise.all([
      fetchJson<WinProbModel>("/engine/win_prob_model.json"),
      fetchJson<RegressionModel>("/engine/margin_model.json"),
      fetchJson<RegressionModel>("/engine/total_model.json"),
      fetchJson<ScoreModel>("/engine/score_model.json"),
      fetchJson<SamplePrediction>("/engine/sample_prediction.json"),
      fetchCsv<DefStrengthRow>("/engine/def_strength_2025.csv"),
      fetchCsv<R1BoardRow>("/engine/r1_board_combined.csv"),
      ...SEASONS.map((y) => fetchJson<ScheduleGame[]>(`/engine/schedule_${y}.json`)),
    ]);

  const perSeason: SeasonAccuracy[] = SEASONS.map((season, i) => ({
    ...summarizeAccuracy(seasonGames[i] as ScheduleGame[]),
    season,
  }));

  const allGames = (seasonGames as ScheduleGame[][]).flat();
  const overall = { ...summarizeAccuracy(allGames), season: 0 };

  const games2025 = (seasonGames as ScheduleGame[][])[SEASONS.indexOf(2025)] ?? [];
  const standings2025 = computeStandings(games2025);
  const draftOrder2026 = computeDraftOrder(standings2025);

  return {
    winProb,
    margin,
    total,
    score,
    schedule: allGames,
    perSeason,
    overall,
    defStrength,
    sample,
    r1Board,
    standings2025,
    draftOrder2026,
  };
}

/** React Query hook that resolves the entire game-prediction engine once per session. */
export function useEngineData() {
  return useQuery({
    queryKey: ["engine-data"],
    queryFn: loadEngine,
    staleTime: Infinity,
    gcTime: Infinity,
  });
}

/** Format a 0-1 probability as a percentage string (e.g. 0.659 -> "65.9%"). */
export function pct(p: number, digits = 1): string {
  return `${(p * 100).toFixed(digits)}%`;
}

/** Top-N |coefficient| features for the given linear model. */
export function topFeatures(
  model: { coef: Record<string, number>; feature_cols: string[] },
  n = 5,
): Array<{ feature: string; coef: number; abs: number }> {
  return model.feature_cols
    .map((feature) => ({ feature, coef: model.coef[feature] ?? 0, abs: Math.abs(model.coef[feature] ?? 0) }))
    .sort((a, b) => b.abs - a.abs)
    .slice(0, n);
}
