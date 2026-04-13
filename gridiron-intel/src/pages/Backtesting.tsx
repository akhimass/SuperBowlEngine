import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { CheckCircle, XCircle, TrendingUp, Target, BarChart3 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import Navbar from "@/components/layout/Navbar";
import StatCard from "@/components/dashboard/StatCard";
import TeamLogo from "@/components/TeamLogo";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SEASONS, type BacktestRecord } from "@/data/mockData";
import { runBacktest } from "@/lib/api";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05, delayChildren: 0.2 } },
};
const item = {
  hidden: { y: 8, opacity: 0 },
  show: { y: 0, opacity: 1, transition: { ease: [0.16, 1, 0.3, 1] as [number, number, number, number], duration: 0.5 } },
};

export default function Backtesting() {
  const [season, setSeason] = useState("2024");
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["backtest", season],
    queryFn: () => runBacktest(Number(season)),
  });

  const records: BacktestRecord[] = useMemo(() => {
    if (!data) return [];
    return data.calibration_data.map((g) => ({
      season: g.season,
      week: String(g.week),
      teamA: g.home_team,
      teamB: g.away_team,
      predictedWinProbA: Math.round(g.predicted_win_prob * 1000) / 10,
      predictedScoreA: g.predicted_score_home,
      predictedScoreB: g.predicted_score_away,
      actualScoreA: g.actual_score_home,
      actualScoreB: g.actual_score_away,
      correct: g.correct,
    }));
  }, [data]);

  const accuracy = data ? Math.round(data.accuracy * 1000) / 10 : 0;
  const avgScoreError = data ? data.average_score_error.toFixed(1) : "0";

  const bestWeek = useMemo(() => {
    const weekMap: Record<string, { total: number; correct: number }> = {};
    records.forEach((r) => {
      if (!weekMap[r.week]) weekMap[r.week] = { total: 0, correct: 0 };
      weekMap[r.week].total++;
      if (r.correct) weekMap[r.week].correct++;
    });
    let best = "";
    let bestPct = 0;
    Object.entries(weekMap).forEach(([w, v]) => {
      const pct = v.correct / v.total;
      if (pct > bestPct) { bestPct = pct; best = w; }
    });
    return best || "—";
  }, [records]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="pt-20 pb-12 px-4">
        <div className="container max-w-6xl mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
            <div>
              <h1 className="text-3xl font-bold tracking-tighter mb-1">Data Accuracy</h1>
              <p className="text-sm text-muted-foreground">How well GridironIQ predictions align with real NFL results</p>
            </div>
            <Select value={season} onValueChange={setSeason}>
              <SelectTrigger className="w-32 bg-secondary border-border rounded-sm"><SelectValue /></SelectTrigger>
              <SelectContent>{SEASONS.map((s) => <SelectItem key={s} value={String(s)}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <StatCard label="Win Prediction Accuracy" value={`${accuracy}%`} icon={Target} delay={0.1} />
            <StatCard label="Avg Score Error" value={`${avgScoreError} pts`} icon={BarChart3} delay={0.15} />
            <StatCard label="Games Analyzed" value={records.length} icon={TrendingUp} delay={0.2} />
            <StatCard label="Top Performing Week" value={bestWeek} delay={0.25} />
          </div>

          {/* Loading / error */}
          {isLoading && (
            <div className="card-surface rim-light p-8 mb-6 text-sm text-muted-foreground">
              Running backtest for {season}…
            </div>
          )}
          {isError && (
            <div className="card-surface rim-light p-8 mb-6 text-sm text-destructive">
              Backtest unavailable: {(error as Error)?.message ?? "Unknown error"}
            </div>
          )}

          {/* Calibration visual */}
          <div className="card-surface rim-light p-5 mb-6">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">
              Predicted Win Probability vs Actual Result
            </h3>
            <div className="space-y-2">
              {records.map((r, i) => {
                const margin = r.actualScoreA - r.actualScoreB;
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="flex items-center gap-3"
                  >
                    <span className="text-xs text-muted-foreground w-16 shrink-0 font-mono">{r.week.replace("Week ", "W")}</span>
                    <span className="text-xs w-28 shrink-0 flex items-center gap-1">
                      <TeamLogo team={r.teamA} size={16} /> {r.teamA}
                      <span className="text-muted-foreground">vs</span>
                      <TeamLogo team={r.teamB} size={16} /> {r.teamB}
                    </span>
                    <div className="flex-1 h-3 bg-secondary rounded-sm relative overflow-hidden">
                      <motion.div
                        className={`h-full rounded-sm ${r.correct ? "bg-success" : "bg-primary"}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${r.predictedWinProbA}%` }}
                        transition={{ duration: 0.6, delay: 0.2 + i * 0.04 }}
                      />
                      <div
                        className="absolute top-0 bottom-0 w-0.5 bg-foreground"
                        style={{ left: "50%" }}
                      />
                    </div>
                    <span className="font-mono text-xs w-12 text-right">{r.predictedWinProbA}%</span>
                    {r.correct ? (
                      <CheckCircle className="h-4 w-4 text-success shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 text-primary shrink-0" />
                    )}
                    <span className="text-xs text-muted-foreground w-16 text-right font-mono">
                      {r.actualScoreA}–{r.actualScoreB}
                    </span>
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Game detail table */}
          <div className="card-surface rim-light overflow-hidden">
            <div className="grid grid-cols-8 px-5 py-3 border-b border-border text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <span>Week</span>
              <span>Matchup</span>
              <span className="text-center">Pred. Score</span>
              <span className="text-center">Act. Score</span>
              <span className="text-center">Win Prob</span>
              <span className="text-center">Score Err</span>
              <span className="text-center">Result</span>
              <span className="text-center">Correct</span>
            </div>
            <motion.div variants={container} initial="hidden" animate="show">
              {records.map((r, i) => (
                <motion.div
                  key={i}
                  variants={item}
                  className="grid grid-cols-8 px-5 py-3 border-b border-border last:border-b-0 text-sm items-center"
                >
                  <span className="text-muted-foreground text-xs">{r.week}</span>
                  <span className="font-medium flex items-center gap-1.5">
                    <TeamLogo team={r.teamA} size={20} /> {r.teamA}
                    <span className="text-muted-foreground">vs</span>
                    <TeamLogo team={r.teamB} size={20} /> {r.teamB}
                  </span>
                  <span className="text-center font-mono text-xs">{r.predictedScoreA}–{r.predictedScoreB}</span>
                  <span className="text-center font-mono text-xs">{r.actualScoreA}–{r.actualScoreB}</span>
                  <span className="text-center font-mono text-xs">{r.predictedWinProbA}%</span>
                  <span className="text-center font-mono text-xs">
                    {(Math.abs(r.predictedScoreA - r.actualScoreA) + Math.abs(r.predictedScoreB - r.actualScoreB)).toFixed(0)}
                  </span>
                  <span className="text-center text-xs">
                    {r.actualScoreA > r.actualScoreB ? r.teamA : r.teamB} W
                  </span>
                  <span className="text-center">
                    {r.correct ? (
                      <CheckCircle className="h-4 w-4 text-success inline" />
                    ) : (
                      <XCircle className="h-4 w-4 text-primary inline" />
                    )}
                  </span>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}
