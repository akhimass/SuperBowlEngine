import { useState, useMemo, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Crosshair, Loader2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import Navbar from "@/components/layout/Navbar";
import WinProbRing from "@/components/dashboard/WinProbRing";
import StatCard from "@/components/dashboard/StatCard";
import EdgePanel from "@/components/dashboard/EdgePanel";
import ComparisonTable from "@/components/dashboard/ComparisonTable";
import ChartPanel from "@/components/dashboard/ChartPanel";
import DeveloperDebugAccordion from "@/components/dashboard/DeveloperDebugAccordion";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { NFL_TEAMS, SEASONS, type MatchupResult } from "@/data/mockData";
import {
  runMatchup,
  getMatchupReport,
  getReportSituational,
  getReportBroadcast,
  getFullMatchupReport,
  type ApiMatchupReportResponse,
  type ApiScoutingReport,
  type ApiSituationalResponse,
  type ApiBroadcastReportResponse,
  type ApiMatchupResponse,
} from "@/lib/api";
import StructuredReportView from "@/components/dashboard/StructuredReportView";
import TeamLogo from "@/components/TeamLogo";
import TeamBadge from "@/components/TeamBadge";
import ExamplePredictionCard from "@/components/ExamplePredictionCard";
import { useTeamLogos } from "@/hooks/useTeamLogos";
import { aiChat } from "@/lib/api";

function SituationalTab({
  season,
  teamA,
  teamB,
  data,
  loading,
  onLoad,
}: {
  season: number;
  teamA: string;
  teamB: string;
  data: ApiSituationalResponse | null;
  loading: boolean;
  onLoad: () => void;
}) {
  useEffect(() => {
    onLoad();
  }, []);
  if (loading) {
    return (
      <div className="card-surface rim-light p-12 text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-3" />
        <p className="text-sm text-muted-foreground">Loading situational tendencies…</p>
      </div>
    );
  }
  if (!data) return <div className="card-surface rim-light p-6 text-sm text-muted-foreground">Run a matchup first, then open this tab to load situational data.</div>;
  const edges = data.situational_edges as ApiSituationalResponse["situational_edges"];
  const hasNote = edges && "note" in edges;
  return (
    <div className="space-y-4">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground mb-1">
            Situational Tendencies
          </h3>
          <p className="text-sm text-muted-foreground">
            Run / pass mix, success rates, and matchup edges by down, distance, and field position.
          </p>
        </div>
      </div>

      {hasNote && <div className="card-surface rim-light p-4 text-sm leading-relaxed">{String(edges.note)}</div>}

      {!hasNote && (
        <>
          <ChartPanel
            title="Situational Visuals"
            subtitle="Heatmaps and matchup overlays generated from play-by-play."
          >
            <SituationalVisuals season={season} teamA={teamA} teamB={teamB} mode="opp_weighted" />
          </ChartPanel>

          <ChartPanel
            title="Offense vs Defense Situational Edges"
            subtitle="Where the matchup tilts in key situations (early downs, third down, red zone)."
          >
            <div className="grid md:grid-cols-2 gap-4 text-sm">
              <div className="bg-secondary/40 border border-border rounded-sm p-4">
                <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                  {teamA} offense vs {teamB} defense
                </p>
                <p className="text-xs text-muted-foreground">
                  Structured situational comparison is available below.
                </p>
              </div>
              <div className="bg-secondary/40 border border-border rounded-sm p-4">
                <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                  {teamB} offense vs {teamA} defense
                </p>
                <p className="text-xs text-muted-foreground">
                  Structured situational comparison is available below.
                </p>
              </div>
            </div>

            <DeveloperDebugAccordion>
              <pre className="bg-secondary/50 rounded p-2 max-h-64 overflow-auto">
                {JSON.stringify({ situational_edges: edges, offense_vs_defense: data.offense_vs_defense ?? {} }, null, 2)}
              </pre>
            </DeveloperDebugAccordion>
          </ChartPanel>
        </>
      )}
    </div>
  );
}

function SituationalVisuals({
  season,
  teamA,
  teamB,
  mode,
}: {
  season: number;
  teamA: string;
  teamB: string;
  mode: string;
}) {
  const [report, setReport] = useState<ApiMatchupReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);
    getFullMatchupReport(season, teamA, teamB, mode, true)
      .then((r) => {
        if (!cancelled) setReport(r);
      })
      .catch((e) => {
        if (!cancelled) setErr((e as Error)?.message ?? "Failed to load matchup visuals");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [season, teamA, teamB, mode]);

  if (loading) return <div className="text-sm text-muted-foreground">Rendering visuals…</div>;
  if (err) return <div className="text-sm text-destructive">Visuals unavailable: {err}</div>;
  if (!report || !report.report_assets?.length) return <div className="text-sm text-muted-foreground">No visuals available.</div>;

  return (
    <div className="grid md:grid-cols-2 gap-4">
      {report.report_assets
        .filter((a) => a.url)
        .slice(0, 6)
        .map((a, idx) => (
          <figure key={`${a.type}-${idx}`} className="bg-secondary/30 border border-border rounded-sm overflow-hidden">
            <img src={a.url ?? ""} alt={a.caption ?? a.type} className="w-full h-auto" />
            <figcaption className="p-3 text-xs text-muted-foreground">
              <div className="uppercase tracking-[0.18em] text-[10px]">{String(a.type).replaceAll("_", " ")}</div>
              {a.caption ? <div className="mt-1">{String(a.caption)}</div> : null}
            </figcaption>
          </figure>
        ))}
    </div>
  );
}

function BroadcastTab({
  season,
  teamA,
  teamB,
  data,
  loading,
  onLoad,
}: {
  season: number;
  teamA: string;
  teamB: string;
  data: ApiBroadcastReportResponse | null;
  loading: boolean;
  onLoad: () => void;
}) {
  useEffect(() => {
    onLoad();
  }, []);
  if (loading) {
    return (
      <div className="card-surface rim-light p-12 text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-3" />
        <p className="text-sm text-muted-foreground">Loading broadcast report…</p>
      </div>
    );
  }
  if (!data) return <div className="card-surface rim-light p-6 text-sm text-muted-foreground">Run a matchup first, then open this tab to load the broadcast view.</div>;
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">{data.headline}</h3>
      <p className="text-sm text-muted-foreground">{data.summary}</p>
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
        {data.headline_stats?.map((s, i) => (
          <div key={i} className="card-surface rim-light p-3">
            <p className="text-xs text-muted-foreground">{s.label}</p>
            <p className="font-semibold">{s.value}</p>
          </div>
        ))}
      </div>
      {data.talking_points?.length > 0 && (
        <div className="card-surface rim-light p-4">
          <h4 className="text-sm font-semibold mb-2">Talking points</h4>
          <ul className="list-disc list-inside text-sm space-y-1">
            {data.talking_points.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}
      {data.top_3_storylines?.length > 0 && (
        <div className="card-surface rim-light p-4">
          <h4 className="text-sm font-semibold mb-2">Top storylines</h4>
          <ol className="list-decimal list-inside text-sm space-y-1">
            {data.top_3_storylines.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </div>
      )}
      {data.confidence_notes?.length > 0 && (
        <p className="text-xs text-muted-foreground">{data.confidence_notes.join(" ")}</p>
      )}
    </div>
  );
}

export default function MatchupAnalysis() {
  const [season, setSeason] = useState("2024");
  const [mode, setMode] = useState<"regular" | "postseason" | "opp_weighted">("opp_weighted");
  const [teamA, setTeamA] = useState("SF");
  const [teamB, setTeamB] = useState("PHI");
  const [result, setResult] = useState<MatchupResult | null>(null);
  const [scoutingReport, setScoutingReport] = useState<ApiScoutingReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [situationalData, setSituationalData] = useState<ApiSituationalResponse | null>(null);
  const [situationalLoading, setSituationalLoading] = useState(false);
  const [broadcastData, setBroadcastData] = useState<ApiBroadcastReportResponse | null>(null);
  const [broadcastLoading, setBroadcastLoading] = useState(false);
  const [lastApiMatchup, setLastApiMatchup] = useState<ApiMatchupResponse | null>(null);
  const [lastApiReport, setLastApiReport] = useState<ApiScoutingReport | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState<{ q: string; a: string; provider: string }[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  const { getLogoPath } = useTeamLogos();

  const matchupMutation = useMutation({
    mutationFn: async (vars: { season: number; teamA: string; teamB: string; mode: string }) => {
      const result = await runMatchup(vars.season, vars.teamA, vars.teamB, vars.mode);
      return { ui: result, vars };
    },
    onSuccess: async ({ ui, vars }) => {
      const { season: s, teamA, teamB, mode } = vars;

      setResult(ui);
      setLastApiMatchup({
        team_a: teamA,
        team_b: teamB,
        season: s,
        mode,
        win_probability: ui.winProbA / 100,
        predicted_winner: ui.teamA === teamA ? (ui.winProbA >= 50 ? teamA : teamB) : ui.teamB,
        projected_score: {
          [teamA]: ui.projectedScoreA,
          [teamB]: ui.projectedScoreB,
        },
        key_edges: {},
        keys_won: {},
        top_drivers: [],
      });
      setScoutingReport(null);
      setSituationalData(null);
      setBroadcastData(null);
      setReportError(null);
      setReportLoading(true);
      try {
        const report = await getMatchupReport(s, teamA, teamB);
        setScoutingReport(report);
        setLastApiReport(report);
      } catch (e) {
        console.error("Failed to load matchup report", e);
        setReportError((e as Error)?.message ?? "Failed to load report");
      } finally {
        setReportLoading(false);
      }
    },
    onError: (error) => {
      console.error("[Matchup] runMatchup failed", error);
      setResult(null);
      setReportError((error as Error)?.message ?? "Failed to run matchup");
    },
  });

  const loading = matchupMutation.isPending;

  const handleRunMatchup = () => {
    if (!teamA || !teamB) {
      setFormError("Please select two teams.");
      return;
    }
    if (teamA === teamB) {
      setFormError("Team A and Team B must be different.");
      return;
    }
    setFormError(null);
    setResult(null);
    setLastApiMatchup(null);
    setLastApiReport(null);
    matchupMutation.mutate({ season: Number(season), teamA, teamB, mode });
  };

  const teamAName = useMemo(() => NFL_TEAMS.find((t) => t.abbr === teamA)?.name ?? teamA, [teamA]);
  const teamBName = useMemo(() => NFL_TEAMS.find((t) => t.abbr === teamB)?.name ?? teamB, [teamB]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="pt-20 pb-12 px-4">
        <div className="container max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold tracking-tighter mb-1">Matchup Predictor</h1>
            <p className="text-sm text-muted-foreground">
              Run custom matchup predictions for any two teams using opponent-adjusted efficiency and situational context.
            </p>
          </div>

          {/* Featured past example */}
          <div className="mb-8">
            <ExamplePredictionCard />
          </div>

          {/* Controls */}
          <div className="card-surface rim-light p-5 mb-6">
            <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
              <Select value={season} onValueChange={setSeason}>
                <SelectTrigger className="bg-secondary border-border rounded-sm"><SelectValue /></SelectTrigger>
                <SelectContent>{SEASONS.map((s) => <SelectItem key={s} value={String(s)}>{s}</SelectItem>)}</SelectContent>
              </Select>
              <Select value={mode} onValueChange={(v) => setMode(v as "regular" | "postseason" | "opp_weighted")}>
                <SelectTrigger className="bg-secondary border-border rounded-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="opp_weighted">Opponent-Adjusted (Full Season)</SelectItem>
                  <SelectItem value="regular">Regular Season Only</SelectItem>
                  <SelectItem value="postseason">Postseason Only</SelectItem>
                </SelectContent>
              </Select>
              <Select value={teamA} onValueChange={setTeamA}>
                <SelectTrigger className="bg-secondary border-border rounded-sm flex items-center gap-2">
                  <TeamLogo team={teamA} size={22} showFallback />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>{NFL_TEAMS.map((t) => <SelectItem key={t.abbr} value={t.abbr}>{t.abbr} — {t.name}</SelectItem>)}</SelectContent>
              </Select>
              <Select value={teamB} onValueChange={setTeamB}>
                <SelectTrigger className="bg-secondary border-border rounded-sm flex items-center gap-2">
                  <TeamLogo team={teamB} size={22} showFallback />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>{NFL_TEAMS.map((t) => <SelectItem key={t.abbr} value={t.abbr}>{t.abbr} — {t.name}</SelectItem>)}</SelectContent>
              </Select>
              <Button onClick={handleRunMatchup} disabled={loading || teamA === teamB} className="rounded-sm bg-primary text-primary-foreground">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Crosshair className="h-4 w-4 mr-1.5" />Analyze</>}
              </Button>
            </div>
            {formError && (
              <p className="mt-3 text-xs text-destructive">
                {formError}
              </p>
            )}
          </div>

          {/* Loading state */}
          {loading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card-surface rim-light p-12 text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-3" />
              <p className="text-sm text-muted-foreground">Analyzing play-by-play data…</p>
              {matchupMutation.isError && (
                <p className="text-xs text-destructive mt-3">
                  {(matchupMutation.error as Error).message ?? "Unable to run matchup."}
                </p>
              )}
            </motion.div>
          )}

          {/* Results */}
          <AnimatePresence>
            {result && !loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.5 }}
              >
                {/* War Room Header */}
                <div className="card-surface rim-light p-6 mb-4">
                  <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex flex-col items-center md:items-start gap-2">
                      <TeamLogo team={teamA} size={48} className="rounded-full" />
                      <h2 className="text-2xl font-bold tracking-tighter">{teamAName}</h2>
                      <span className="text-xs text-muted-foreground uppercase tracking-wider">{teamA}</span>
                    </div>
                    <WinProbRing probability={result.winProbA} label={`${teamA} Win Prob`} />
                    <div className="flex flex-col items-center md:items-end gap-2">
                      <TeamLogo team={teamB} size={48} className="rounded-full" />
                      <h2 className="text-2xl font-bold tracking-tighter">{teamBName}</h2>
                      <span className="text-xs text-muted-foreground uppercase tracking-wider">{teamB}</span>
                    </div>
                  </div>
                </div>

                {/* Tabs: Model Prediction | Efficiency Edges | 5 Keys | Scouting | AI | Situational | Broadcast */}
                <Tabs defaultValue="prediction" className="space-y-4">
                  <TabsList className="bg-secondary rounded-sm border border-border p-1 flex flex-wrap">
                    <TabsTrigger value="prediction" className="rounded-sm text-xs data-[state=active]:bg-card">Model Prediction</TabsTrigger>
                    <TabsTrigger value="efficiency" className="rounded-sm text-xs data-[state=active]:bg-card">Efficiency Edges</TabsTrigger>
                    <TabsTrigger value="keys" className="rounded-sm text-xs data-[state=active]:bg-card">5 Keys Breakdown</TabsTrigger>
                    <TabsTrigger value="scout" className="rounded-sm text-xs data-[state=active]:bg-card">Scouting Report</TabsTrigger>
                    <TabsTrigger value="ai" className="rounded-sm text-xs data-[state=active]:bg-card">AI Statistician</TabsTrigger>
                    <TabsTrigger value="situational" className="rounded-sm text-xs data-[state=active]:bg-card">Situational Tendencies</TabsTrigger>
                    <TabsTrigger value="broadcast" className="rounded-sm text-xs data-[state=active]:bg-card">Broadcast View</TabsTrigger>
                  </TabsList>

                  <TabsContent value="prediction">
                    <div className="card-surface rim-light p-5 mb-4">
                      <div className="flex flex-col md:flex-row md:items-end justify-between gap-3 mb-4">
                        <div>
                          <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground mb-1">
                            Model Prediction
                          </h3>
                          <p className="text-sm text-muted-foreground">
                            Primary v2 prediction driven by stable team efficiency and matchup differentials.
                          </p>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Winner: <span className="text-foreground font-semibold">{result.winProbA >= 50 ? teamA : teamB}</span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                      <div className="card-surface rim-light p-4 flex flex-col gap-2">
                        <p className="text-xs text-muted-foreground uppercase tracking-wider">Projected Score</p>
                        <div className="flex items-center justify-center gap-4">
                          <TeamBadge team={teamA} size="sm" />
                          <span className="font-mono text-lg font-semibold">{result.projectedScoreA}–{result.projectedScoreB}</span>
                          <TeamBadge team={teamB} size="sm" />
                        </div>
                      </div>
                      <StatCard
                        label="Win Probability"
                        value={`${result.winProbA}% / ${result.winProbB}%`}
                        subtitle={`${teamA} / ${teamB}`}
                        trend="up"
                        delay={0.15}
                      />
                      <StatCard label="Projected Margin" value={`${(result.projectedMargin ?? (result.projectedScoreA - result.projectedScoreB)).toFixed ? (result.projectedMargin ?? (result.projectedScoreA - result.projectedScoreB)).toFixed(1) : (result.projectedMargin ?? (result.projectedScoreA - result.projectedScoreB))} pts`} subtitle={`${teamA} − ${teamB}`} delay={0.2} />
                      <StatCard label="Projected Total" value={`${(result.projectedTotal ?? (result.projectedScoreA + result.projectedScoreB)).toFixed ? (result.projectedTotal ?? (result.projectedScoreA + result.projectedScoreB)).toFixed(1) : (result.projectedTotal ?? (result.projectedScoreA + result.projectedScoreB))} pts`} subtitle="Points (combined)" delay={0.25} />
                      <StatCard label="Confidence Band" value="Balanced" subtitle="Avoids 0%/100% outputs" delay={0.3} />
                      </div>
                    </div>
                    <div className="flex items-center justify-center gap-2 py-2 text-sm text-muted-foreground">
                      <TeamLogo team={teamA} size={20} /> <span>{teamA}</span>
                      <span>vs</span>
                      <TeamLogo team={teamB} size={20} /> <span>{teamB}</span>
                    </div>
                    <div className="card-surface rim-light p-6">
                      <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">Top Prediction Drivers</h3>
                      <ol className="space-y-3">
                        {result.topDrivers.map((d, i) => (
                          <motion.li
                            key={i}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.08 }}
                            className="flex items-start gap-3"
                          >
                            <span className="font-mono text-xs text-muted-foreground shrink-0 w-5">{String(i + 1).padStart(2, "0")}</span>
                            <span className="text-sm">{d}</span>
                          </motion.li>
                        ))}
                      </ol>
                    </div>
                  </TabsContent>

                  <TabsContent value="efficiency">
                    <div className="card-surface rim-light p-6 space-y-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground mb-1">
                            Efficiency Edges
                          </h3>
                          <p className="text-sm text-muted-foreground">
                            Stable matchup differentials (offense vs defense) that drive the v2 win, margin, and total models.
                          </p>
                        </div>
                      </div>

                      <div className="grid md:grid-cols-2 gap-4 text-sm">
                        {[
                          ["EPA Edge", "epa_edge"],
                          ["Success Rate Edge", "success_edge"],
                          ["Explosive Play Edge", "explosive_edge"],
                          ["Early-Down Edge", "early_down_success_edge"],
                          ["Third-Down Edge", "third_down_edge"],
                          ["Red Zone Edge", "redzone_edge"],
                          ["Sack / Pressure Edge", "sack_edge"],
                          ["Recent Form (EPA) Edge", "recent_epa_edge"],
                          ["Strength of Schedule Edge", "sos_edge"],
                        ].map(([label, key]) => {
                          const v = (result.efficiencyEdges as any)?.[key] as number | undefined;
                          const dir = typeof v === "number" ? (v > 0 ? teamA : v < 0 ? teamB : "Even") : "—";
                          const val = typeof v === "number" ? v.toFixed(3) : "—";
                          return (
                            <div key={key} className="card-surface rim-light p-4">
                              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-1">{label}</p>
                              <div className="flex items-end justify-between gap-3">
                                <div className="font-mono text-lg text-foreground">{val}</div>
                                <div className="text-xs text-muted-foreground">
                                  Edge: <span className="text-foreground font-semibold">{dir}</span>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      <details className="text-[11px] text-muted-foreground">
                        <summary className="cursor-pointer underline-offset-2 underline">Developer view (raw payload)</summary>
                        <pre className="mt-2 bg-secondary/50 rounded p-2 max-h-64 overflow-auto">
                          {JSON.stringify(result.efficiencyEdges ?? {}, null, 2)}
                        </pre>
                      </details>
                    </div>
                  </TabsContent>

                  <TabsContent value="keys">
                    <div className="card-surface rim-light p-6 space-y-4">
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground mb-1">
                          5 Keys Breakdown
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          Explainability layer. These keys summarize matchup pressure points, but they are not the v2 model backbone.
                        </p>
                      </div>
                      <EdgePanel edges={result.edges} teamA={teamA} teamB={teamB} />
                      <div className="card-surface rim-light p-5">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Key drivers</h4>
                        <ul className="list-disc list-inside text-sm space-y-1">
                          {result.topDrivers.map((d, i) => (
                            <li key={i}>{d}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="scout">
                    {reportLoading && (
                      <div className="card-surface rim-light p-12 text-center">
                        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-3" />
                        <p className="text-sm text-muted-foreground">Generating scouting report…</p>
                      </div>
                    )}
                    {reportError && !reportLoading && (
                      <div className="card-surface rim-light p-4 text-sm text-destructive">
                        Report unavailable: {reportError}
                      </div>
                    )}
                    {scoutingReport && !reportLoading && (
                      <StructuredReportView
                        report={scoutingReport}
                        teamA={teamA}
                        teamB={teamB}
                      />
                    )}
                  </TabsContent>

                  <TabsContent value="ai">
                    {reportLoading && (
                      <div className="card-surface rim-light p-12 text-center">
                        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-3" />
                        <p className="text-sm text-muted-foreground">Generating AI explanation…</p>
                      </div>
                    )}
                    {!reportLoading && scoutingReport?.ai_statistician && (
                      <div className="card-surface rim-light p-6 space-y-4">
                        <div className="flex items-center justify-between gap-2">
                          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                            AI Statistician
                          </h3>
                          <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground border border-border rounded-full px-2 py-0.5">
                            Provider: {import.meta.env.VITE_AI_MODE ?? "template"}
                          </span>
                        </div>
                        <p className="text-sm text-secondary-foreground">
                          {scoutingReport.ai_statistician.summary}
                        </p>
                        <div>
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                            Top reasons
                          </h4>
                          <ul className="list-disc list-inside text-sm space-y-1">
                            {scoutingReport.ai_statistician.top_3_reasons.map((r, i) => (
                              <li key={i}>{r}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="grid md:grid-cols-2 gap-4 text-sm">
                          <div>
                            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                              What matters most
                            </h4>
                            <p className="text-secondary-foreground">
                              {scoutingReport.ai_statistician.what_matters_most}
                            </p>
                          </div>
                          <div>
                            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                              What could flip it
                            </h4>
                            <p className="text-secondary-foreground">
                              {scoutingReport.ai_statistician.what_could_flip_it}
                            </p>
                          </div>
                        </div>
                        {scoutingReport.ai_statistician.confidence_note && (
                          <p className="text-xs text-muted-foreground">
                            {scoutingReport.ai_statistician.confidence_note}
                          </p>
                        )}

                        <div className="border-t border-border pt-4">
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                            Ask about this matchup
                          </h4>
                          <div className="flex flex-col md:flex-row gap-2">
                            <input
                              value={question}
                              onChange={(e) => setQuestion(e.target.value)}
                              placeholder="Ask a grounded question (e.g., 'What matters most on third down?')"
                              className="flex-1 bg-secondary border border-border rounded-sm px-3 py-2 text-sm text-foreground"
                            />
                            <Button
                              size="sm"
                              disabled={chatLoading || !question.trim()}
                              onClick={async () => {
                                const q = question.trim();
                                if (!q) return;
                                setChatLoading(true);
                                setQuestion("");
                                try {
                                  const res = await aiChat({
                                    question: q,
                                    context_type: "matchup",
                                    season: Number(season),
                                    team_a: teamA,
                                    team_b: teamB,
                                    mode,
                                  });
                                  setChat((prev) => [{ q, a: res.answer, provider: res.provider }, ...prev].slice(0, 6));
                                } finally {
                                  setChatLoading(false);
                                }
                              }}
                            >
                              {chatLoading ? "Thinking…" : "Ask"}
                            </Button>
                          </div>
                          <div className="mt-3 space-y-3">
                            {chat.map((m, idx) => (
                              <div key={idx} className="bg-secondary/40 border border-border rounded-sm p-3">
                                <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                                  Question • Provider: {m.provider}
                                </div>
                                <div className="text-sm text-foreground mb-2">{m.q}</div>
                                <div className="text-sm text-muted-foreground whitespace-pre-wrap">{m.a}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                    {!reportLoading && !scoutingReport?.ai_statistician && (
                      <div className="card-surface rim-light p-6 text-sm text-muted-foreground">
                        AI explanation is not available for this matchup.
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="situational">
                    <SituationalTab
                      season={Number(season)}
                      teamA={teamA}
                      teamB={teamB}
                      data={situationalData}
                      loading={situationalLoading}
                      onLoad={() => {
                        if (!situationalData && !situationalLoading) {
                          setSituationalLoading(true);
                          getReportSituational(Number(season), teamA, teamB)
                            .then(setSituationalData)
                            .finally(() => setSituationalLoading(false));
                        }
                      }}
                    />
                  </TabsContent>

                  <TabsContent value="broadcast">
                    <BroadcastTab
                      season={Number(season)}
                      teamA={teamA}
                      teamB={teamB}
                      data={broadcastData}
                      loading={broadcastLoading}
                      onLoad={() => {
                        if (!broadcastData && !broadcastLoading) {
                          setBroadcastLoading(true);
                          getReportBroadcast(Number(season), teamA, teamB)
                            .then(setBroadcastData)
                            .finally(() => setBroadcastLoading(false));
                        }
                      }}
                    />
                  </TabsContent>
                </Tabs>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Scouting report errors (without debug JSON) */}
          {reportError && result && (
            <div className="card-surface rim-light mt-4 p-4 text-xs text-destructive">
              Failed to generate matchup report: {reportError}
            </div>
          )}

          {/* Empty state */}
          {!result && !loading && (
            <div className="card-surface rim-light p-16 text-center">
              <Crosshair className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground text-sm">Select two teams and click Analyze to generate a matchup report.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
