import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import Navbar from "@/components/layout/Navbar";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import TeamBadge from "@/components/TeamBadge";
import { SEASONS } from "@/data/mockData";
import { getSchedule, type ApiScheduleGame } from "@/lib/api";

const PHASE_OPTIONS = [
  { value: "all", label: "All Games" },
  { value: "regular", label: "Regular Season" },
  { value: "postseason", label: "Postseason" },
];

export default function ScheduleExplorer() {
  const [season, setSeason] = useState("2024");
  const [phase, setPhase] = useState<"all" | "regular" | "postseason">("all");
  const navigate = useNavigate();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["schedule", season, phase],
    queryFn: () => getSchedule(Number(season), phase),
    staleTime: 60_000,
  });

  const games = useMemo(() => {
    const arr = data?.games ?? [];
    return [...arr].sort((a: ApiScheduleGame, b: ApiScheduleGame) => {
      const wa = typeof a.week === "number" ? a.week : 0;
      const wb = typeof b.week === "number" ? b.week : 0;
      return wa - wb;
    });
  }, [data]);

  const titlePhase = PHASE_OPTIONS.find((p) => p.value === phase)?.label ?? "All Games";

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="pt-20 pb-12 px-4">
        <div className="container max-w-6xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold tracking-tighter mb-1">Schedule &amp; Results Explorer</h1>
            <p className="text-sm text-muted-foreground">
              Browse real NFL matchups by season and phase, with GridironIQ&apos;s prediction versus the actual result.
            </p>
          </div>

          <div className="card-surface rim-light p-5 mb-6">
            <div className="flex flex-wrap items-center gap-3">
              <Select value={season} onValueChange={setSeason}>
                <SelectTrigger className="bg-secondary border-border rounded-sm w-32">
                  <SelectValue placeholder="Season" />
                </SelectTrigger>
                <SelectContent>
                  {SEASONS.map((s) => (
                    <SelectItem key={s} value={String(s)}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={phase} onValueChange={(v) => setPhase(v as "all" | "regular" | "postseason")}>
                <SelectTrigger className="bg-secondary border-border rounded-sm w-44">
                  <SelectValue placeholder="Phase" />
                </SelectTrigger>
                <SelectContent>
                  {PHASE_OPTIONS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button size="sm" variant="outline" onClick={() => refetch()}>
                Refresh
              </Button>
            </div>
          </div>

          {isLoading && (
            <div className="card-surface rim-light p-12 text-center text-sm text-muted-foreground">
              Loading schedule…
            </div>
          )}

          {isError && !isLoading && (
            <div className="card-surface rim-light p-12 text-center text-sm text-destructive">
              Failed to load schedule. Please check the backend and try again.
            </div>
          )}

          {!isLoading && !isError && games.length === 0 && (
            <div className="card-surface rim-light p-12 text-center text-sm text-muted-foreground">
              No games found for {season} ({titlePhase.toLowerCase()}).
            </div>
          )}

          {!isLoading && !isError && games.length > 0 && (
            <div className="grid gap-3 md:grid-cols-2">
              {games.map((g: ApiScheduleGame) => {
                const predicted = g.predicted_winner;
                const actual =
                  g.home_score > g.away_score ? g.home_team : g.away_score > g.home_score ? g.away_team : "TIE";
                let badgeLabel = "Pending";
                let badgeClass = "bg-muted text-muted-foreground border-border/60";
                if (predicted) {
                  if (predicted === actual) {
                    badgeLabel = "Correct Prediction";
                    badgeClass = "bg-emerald-500/10 text-emerald-300 border-emerald-500/60";
                  } else {
                    badgeLabel = "Incorrect Prediction";
                    badgeClass = "bg-red-500/10 text-red-300 border-red-500/60";
                  }
                }

                const winProb =
                  typeof g.win_probability === "number" ? `${Math.round(g.win_probability * 1000) / 10}%` : "—";

                return (
                  <button
                    key={g.game_id}
                    type="button"
                    onClick={() => navigate(`/schedule/${g.season}/${g.game_id}`)}
                    className="card-surface rim-light text-left p-4 md:p-5 hover:border-primary/60 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-3 mb-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                          {g.season_type === "REG" ? `Week ${g.week}` : g.season_type || "Game"}
                        </p>
                        <p className="text-sm font-medium text-foreground">
                          {g.season} • {phase === "all" ? "All games" : titlePhase}
                        </p>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-[0.18em] border ${badgeClass}`}
                      >
                        {badgeLabel}
                      </span>
                    </div>

                    <div className="flex items-center justify-between gap-4 mb-3">
                      <div className="flex-1 flex items-center gap-2">
                        <TeamBadge team={g.home_team} size="sm" showName />
                      </div>
                      <div className="flex flex-col items-center text-xs text-muted-foreground">
                        <span className="font-mono text-sm text-foreground">
                          {g.home_score} – {g.away_score}
                        </span>
                        <span>Final</span>
                      </div>
                      <div className="flex-1 flex items-center justify-end gap-2">
                        <TeamBadge team={g.away_team} size="sm" showName />
                      </div>
                    </div>

                    <div className="flex items-center justify-between gap-3 text-[11px] text-muted-foreground">
                      <div className="flex flex-col">
                        <span className="uppercase tracking-[0.18em] mb-0.5">Predicted</span>
                        {predicted ? (
                          <span>
                            {predicted} • {winProb}
                          </span>
                        ) : (
                          <span>Prediction pending</span>
                        )}
                      </div>
                      <div className="flex flex-col text-right">
                        <span className="uppercase tracking-[0.18em] mb-0.5">Projected Score</span>
                        <span className="font-mono">
                          {(g.predicted_score?.[g.home_team] ?? 0)} – {(g.predicted_score?.[g.away_team] ?? 0)}
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

