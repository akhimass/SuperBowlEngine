export const NFL_TEAMS = [
  { abbr: "ARI", name: "Arizona Cardinals", conference: "NFC", division: "West" },
  { abbr: "ATL", name: "Atlanta Falcons", conference: "NFC", division: "South" },
  { abbr: "BAL", name: "Baltimore Ravens", conference: "AFC", division: "North" },
  { abbr: "BUF", name: "Buffalo Bills", conference: "AFC", division: "East" },
  { abbr: "CAR", name: "Carolina Panthers", conference: "NFC", division: "South" },
  { abbr: "CHI", name: "Chicago Bears", conference: "NFC", division: "North" },
  { abbr: "CIN", name: "Cincinnati Bengals", conference: "AFC", division: "North" },
  { abbr: "CLE", name: "Cleveland Browns", conference: "AFC", division: "North" },
  { abbr: "DAL", name: "Dallas Cowboys", conference: "NFC", division: "East" },
  { abbr: "DEN", name: "Denver Broncos", conference: "AFC", division: "West" },
  { abbr: "DET", name: "Detroit Lions", conference: "NFC", division: "North" },
  { abbr: "GB", name: "Green Bay Packers", conference: "NFC", division: "North" },
  { abbr: "HOU", name: "Houston Texans", conference: "AFC", division: "South" },
  { abbr: "IND", name: "Indianapolis Colts", conference: "AFC", division: "South" },
  { abbr: "JAX", name: "Jacksonville Jaguars", conference: "AFC", division: "South" },
  { abbr: "KC", name: "Kansas City Chiefs", conference: "AFC", division: "West" },
  { abbr: "LAC", name: "Los Angeles Chargers", conference: "AFC", division: "West" },
  { abbr: "LAR", name: "Los Angeles Rams", conference: "NFC", division: "West" },
  { abbr: "LV", name: "Las Vegas Raiders", conference: "AFC", division: "West" },
  { abbr: "MIA", name: "Miami Dolphins", conference: "AFC", division: "East" },
  { abbr: "MIN", name: "Minnesota Vikings", conference: "NFC", division: "North" },
  { abbr: "NE", name: "New England Patriots", conference: "AFC", division: "East" },
  { abbr: "NO", name: "New Orleans Saints", conference: "NFC", division: "South" },
  { abbr: "NYG", name: "New York Giants", conference: "NFC", division: "East" },
  { abbr: "NYJ", name: "New York Jets", conference: "AFC", division: "East" },
  { abbr: "PHI", name: "Philadelphia Eagles", conference: "NFC", division: "East" },
  { abbr: "PIT", name: "Pittsburgh Steelers", conference: "AFC", division: "North" },
  { abbr: "SEA", name: "Seattle Seahawks", conference: "NFC", division: "West" },
  { abbr: "SF", name: "San Francisco 49ers", conference: "NFC", division: "West" },
  { abbr: "TB", name: "Tampa Bay Buccaneers", conference: "NFC", division: "South" },
  { abbr: "TEN", name: "Tennessee Titans", conference: "AFC", division: "South" },
  { abbr: "WAS", name: "Washington Commanders", conference: "NFC", division: "East" },
];

export const SEASONS = [2025, 2024, 2023, 2022, 2021, 2020];
export const WEEKS = Array.from({ length: 18 }, (_, i) => `Week ${i + 1}`);
export const POSTSEASON_ROUNDS = ["Wild Card", "Divisional", "Conference Championship", "Super Bowl"];

export interface MatchupResult {
  teamA: string;
  teamB: string;
  winProbA: number;
  winProbB: number;
  projectedScoreA: number;
  projectedScoreB: number;
  projectedMargin?: number;
  projectedTotal?: number;
  efficiencyEdges?: Record<string, unknown>;
  confidence: number;
  edges: MatchupEdge[];
  metrics: MetricComparison[];
  qbComparison: QBComparison;
  scoutingReport: string;
  topDrivers: string[];
}

export interface MatchupEdge {
  label: string;
  advantage: "A" | "B" | "EVEN";
  magnitude: number;
  category: "offense" | "defense" | "qb" | "situational";
}

export interface MetricComparison {
  metric: string;
  teamAValue: number;
  teamBValue: number;
  unit: string;
  higherIsBetter: boolean;
}

export interface QBComparison {
  qbA: { name: string; epaPerPlay: number; cpoe: number; pressuredRate: number; aggPct: number; };
  qbB: { name: string; epaPerPlay: number; cpoe: number; pressuredRate: number; aggPct: number; };
}

export interface BacktestRecord {
  season: number;
  week: string;
  teamA: string;
  teamB: string;
  predictedWinProbA: number;
  predictedScoreA: number;
  predictedScoreB: number;
  actualScoreA: number;
  actualScoreB: number;
  correct: boolean;
}

export interface SavedReport {
  id: string;
  season: number;
  week: string;
  teamA: string;
  teamB: string;
  predictedWinner: string;
  actualWinner: string;
  confidence: number;
  generatedAt: string;
}

export function generateMockMatchup(teamA: string, teamB: string): MatchupResult {
  const winProb = 40 + Math.random() * 35;
  return {
    teamA,
    teamB,
    winProbA: Math.round(winProb * 10) / 10,
    projectedScoreA: Math.round(17 + Math.random() * 17),
    projectedScoreB: Math.round(14 + Math.random() * 17),
    confidence: Math.round((55 + Math.random() * 30) * 10) / 10,
    edges: [
      { label: `${teamA} Pass Rush vs ${teamB} O-Line`, advantage: "A", magnitude: 3.2, category: "defense" },
      { label: `${teamB} Run Game vs ${teamA} Front Seven`, advantage: "B", magnitude: 2.1, category: "offense" },
      { label: `${teamA} Red Zone Offense`, advantage: "A", magnitude: 1.8, category: "offense" },
      { label: `${teamB} Turnover Margin`, advantage: "B", magnitude: 1.4, category: "situational" },
      { label: `${teamA} QB Mobility`, advantage: "A", magnitude: 2.6, category: "qb" },
      { label: `${teamB} Secondary Coverage`, advantage: "B", magnitude: 1.9, category: "defense" },
    ],
    metrics: [
      { metric: "Off. EPA/Play", teamAValue: 0.12, teamBValue: 0.08, unit: "", higherIsBetter: true },
      { metric: "Def. EPA/Play", teamAValue: -0.05, teamBValue: -0.11, unit: "", higherIsBetter: false },
      { metric: "Pass Rate Over Exp.", teamAValue: 3.2, teamBValue: -1.4, unit: "%", higherIsBetter: true },
      { metric: "Rush Yards/Att", teamAValue: 4.8, teamBValue: 4.2, unit: "yds", higherIsBetter: true },
      { metric: "3rd Down Conv.", teamAValue: 44.2, teamBValue: 38.7, unit: "%", higherIsBetter: true },
      { metric: "Red Zone TD%", teamAValue: 62.5, teamBValue: 55.1, unit: "%", higherIsBetter: true },
      { metric: "Turnover Rate", teamAValue: 1.2, teamBValue: 1.8, unit: "/gm", higherIsBetter: false },
      { metric: "Pressure Rate", teamAValue: 28.4, teamBValue: 24.1, unit: "%", higherIsBetter: true },
    ],
    qbComparison: {
      qbA: { name: "Brock Purdy", epaPerPlay: 0.18, cpoe: 3.2, pressuredRate: 26.4, aggPct: 15.8 },
      qbB: { name: "Jalen Hurts", epaPerPlay: 0.14, cpoe: 1.8, pressuredRate: 22.1, aggPct: 18.2 },
    },
    scoutingReport: `## Matchup Overview\n\n${teamA} enters this contest as a slight favorite based on opponent-adjusted efficiency metrics. The primary advantage stems from their pass rush, which ranks in the top 5 in pressure rate generated.\n\n## Key Matchup: ${teamA} Pass Rush vs ${teamB} Protection\n\nThis is the fulcrum of the game. ${teamA}'s edge rushers have generated a 28.4% pressure rate this season, while ${teamB}'s offensive line has allowed pressure on 24.1% of dropbacks. When ${teamA} generates pressure, opposing QBs see their EPA/play drop from +0.12 to -0.31.\n\n## QB Assessment\n\nBoth quarterbacks are performing above league average in CPOE. ${teamA}'s QB shows higher efficiency under clean pockets, while ${teamB}'s QB demonstrates more resilience under pressure—a factor that could neutralize the pass rush advantage.\n\n## Game Script Projection\n\nIf ${teamA} builds an early lead, their defensive front becomes even more dangerous in obvious passing situations. ${teamB}'s path to victory requires establishing the run early and keeping the game in neutral script, where their offensive efficiency is significantly higher.\n\n## Bottom Line\n\n${teamA} has the edge in this matchup, but the margin is thin. The game likely comes down to early-down efficiency and turnover margin.`,
    topDrivers: [
      "Pass rush pressure differential (+4.3%)",
      "Red zone touchdown rate advantage (+7.4%)",
      "QB EPA/Play edge (+0.04)",
      "Home field advantage (+2.5 pts)",
      "Injury-adjusted depth chart rating",
    ],
  };
}

export const MOCK_BACKTEST_DATA: BacktestRecord[] = [
  { season: 2024, week: "Week 1", teamA: "KC", teamB: "BAL", predictedWinProbA: 58.3, predictedScoreA: 27, predictedScoreB: 24, actualScoreA: 27, actualScoreB: 20, correct: true },
  { season: 2024, week: "Week 1", teamA: "SF", teamB: "NYJ", predictedWinProbA: 64.1, predictedScoreA: 28, predictedScoreB: 21, actualScoreA: 32, actualScoreB: 19, correct: true },
  { season: 2024, week: "Week 2", teamA: "DAL", teamB: "NO", predictedWinProbA: 52.7, predictedScoreA: 24, predictedScoreB: 23, actualScoreA: 19, actualScoreB: 44, correct: false },
  { season: 2024, week: "Week 2", teamA: "DET", teamB: "TB", predictedWinProbA: 61.8, predictedScoreA: 30, predictedScoreB: 24, actualScoreA: 16, actualScoreB: 20, correct: false },
  { season: 2024, week: "Week 3", teamA: "BUF", teamB: "JAX", predictedWinProbA: 66.2, predictedScoreA: 31, predictedScoreB: 21, actualScoreA: 47, actualScoreB: 10, correct: true },
  { season: 2024, week: "Week 3", teamA: "PHI", teamB: "NO", predictedWinProbA: 55.4, predictedScoreA: 25, predictedScoreB: 23, actualScoreA: 15, actualScoreB: 12, correct: true },
  { season: 2024, week: "Week 4", teamA: "KC", teamB: "LAC", predictedWinProbA: 62.9, predictedScoreA: 27, predictedScoreB: 20, actualScoreA: 17, actualScoreB: 10, correct: true },
  { season: 2024, week: "Week 4", teamA: "MIN", teamB: "GB", predictedWinProbA: 48.1, predictedScoreA: 23, predictedScoreB: 24, actualScoreA: 31, actualScoreB: 29, correct: false },
  { season: 2024, week: "Week 5", teamA: "SF", teamB: "ARI", predictedWinProbA: 71.3, predictedScoreA: 30, predictedScoreB: 20, actualScoreA: 24, actualScoreB: 23, correct: true },
  { season: 2024, week: "Week 5", teamA: "BAL", teamB: "CIN", predictedWinProbA: 59.8, predictedScoreA: 28, predictedScoreB: 24, actualScoreA: 41, actualScoreB: 38, correct: true },
  { season: 2024, week: "Week 6", teamA: "DET", teamB: "DAL", predictedWinProbA: 63.4, predictedScoreA: 31, predictedScoreB: 24, actualScoreA: 47, actualScoreB: 9, correct: true },
  { season: 2024, week: "Week 6", teamA: "HOU", teamB: "NE", predictedWinProbA: 68.7, predictedScoreA: 27, predictedScoreB: 17, actualScoreA: 41, actualScoreB: 21, correct: true },
  { season: 2023, week: "Week 1", teamA: "DET", teamB: "KC", predictedWinProbA: 38.2, predictedScoreA: 20, predictedScoreB: 27, actualScoreA: 21, actualScoreB: 20, correct: false },
  { season: 2023, week: "Week 2", teamA: "MIA", teamB: "NE", predictedWinProbA: 62.5, predictedScoreA: 27, predictedScoreB: 20, actualScoreA: 24, actualScoreB: 17, correct: true },
  { season: 2023, week: "Week 3", teamA: "SF", teamB: "NYG", predictedWinProbA: 74.1, predictedScoreA: 31, predictedScoreB: 17, actualScoreA: 30, actualScoreB: 12, correct: true },
];

export const MOCK_SAVED_REPORTS: SavedReport[] = [
  { id: "1", season: 2024, week: "Week 12", teamA: "SF", teamB: "PHI", predictedWinner: "SF", actualWinner: "PHI", confidence: 62.4, generatedAt: "2024-11-24T14:30:00Z" },
  { id: "2", season: 2024, week: "Week 11", teamA: "KC", teamB: "BUF", predictedWinner: "KC", actualWinner: "KC", confidence: 57.8, generatedAt: "2024-11-17T18:00:00Z" },
  { id: "3", season: 2024, week: "Week 10", teamA: "DET", teamB: "HOU", predictedWinner: "DET", actualWinner: "DET", confidence: 65.2, generatedAt: "2024-11-10T13:00:00Z" },
  { id: "4", season: 2024, week: "Week 9", teamA: "BAL", teamB: "CIN", predictedWinner: "BAL", actualWinner: "BAL", confidence: 61.9, generatedAt: "2024-11-03T13:00:00Z" },
  { id: "5", season: 2024, week: "Week 8", teamA: "PHI", teamB: "DAL", predictedWinner: "PHI", actualWinner: "PHI", confidence: 70.1, generatedAt: "2024-10-27T16:25:00Z" },
  { id: "6", season: 2023, week: "Super Bowl", teamA: "SF", teamB: "KC", predictedWinner: "SF", actualWinner: "KC", confidence: 54.3, generatedAt: "2024-02-11T18:30:00Z" },
  { id: "7", season: 2023, week: "Week 15", teamA: "DAL", teamB: "BUF", predictedWinner: "BUF", actualWinner: "BUF", confidence: 55.8, generatedAt: "2023-12-17T13:00:00Z" },
  { id: "8", season: 2023, week: "Week 14", teamA: "MIA", teamB: "TEN", predictedWinner: "MIA", actualWinner: "MIA", confidence: 68.4, generatedAt: "2023-12-11T20:15:00Z" },
];
