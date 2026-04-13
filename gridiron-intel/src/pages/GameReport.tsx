import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import Navbar from "@/components/layout/Navbar";
import TeamBadge from "@/components/TeamBadge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { aiChat, getJson, type ApiAiExplanation } from "@/lib/api";
import DeveloperDebugAccordion from "@/components/dashboard/DeveloperDebugAccordion";

interface ApiGameReport {
  season: number;
  game_id: string;
  week: number | string | null;
  season_type: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  matchup: {
    team_a: string;
    team_b: string;
    win_probability: number;
    predicted_winner: string;
    projected_score: Record<string, number>;
    projected_margin?: number | null;
    projected_total?: number | null;
    team_efficiency_edges?: Record<string, unknown> | null;
  };
  scouting_report: {
    summary?: string;
    prediction_explanation?: string;
    team_a_strengths?: string[];
    team_b_strengths?: string[];
    [key: string]: unknown;
  };
  situational: {
    situational_edges?: Record<string, unknown>;
    offense_vs_defense?: Record<string, unknown>;
    [key: string]: unknown;
  };
  broadcast: {
    headline?: string;
    summary?: string;
    talking_points?: string[];
    top_3_storylines?: string[];
    confidence_notes?: string[];
    [key: string]: unknown;
  };
  ai_statistician?: ApiAiExplanation;
}

export default function GameReport() {
  const { season, gameId } = useParams<{ season: string; gameId: string }>();
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["game-report", season, gameId],
    queryFn: () =>
      getJson<ApiGameReport>(`/api/game-report?season=${encodeURIComponent(season ?? "")}&game_id=${encodeURIComponent(gameId ?? "")}`),
    enabled: Boolean(season && gameId),
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="pt-20 pb-12 px-4">
          <div className="container max-w-6xl mx-auto">
            <div className="card-surface rim-light p-12 text-center text-sm text-muted-foreground">Loading game report…</div>
          </div>
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="pt-20 pb-12 px-4">
          <div className="container max-w-6xl mx-auto">
            <div className="card-surface rim-light p-12 text-center text-sm text-destructive">
              Failed to load game report.
              <div className="mt-4">
                <Button size="sm" variant="outline" onClick={() => navigate(-1)}>
                  Back to schedule
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const projHome = data.matchup.projected_score?.[data.home_team] ?? 0;
  const projAway = data.matchup.projected_score?.[data.away_team] ?? 0;
  const winProb = Math.round((data.matchup.win_probability ?? 0.5) * 1000) / 10;
  const projMargin = typeof data.matchup.projected_margin === "number" ? data.matchup.projected_margin : projHome - projAway;
  const projTotal = typeof data.matchup.projected_total === "number" ? data.matchup.projected_total : projHome + projAway;

  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState<{ q: string; a: string; provider: string }[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="pt-20 pb-12 px-4">
        <div className="container max-w-6xl mx-auto space-y-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                {data.season_type === "REG" ? `Week ${data.week}` : data.season_type} • {data.season}
              </p>
              <h1 className="text-2xl font-bold tracking-tight">
                {data.home_team} vs {data.away_team}
              </h1>
            </div>
            <Button size="sm" variant="outline" onClick={() => navigate(-1)}>
              Back to schedule
            </Button>
          </div>

          <div className="card-surface rim-light p-6 flex flex-col gap-4">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <TeamBadge team={data.home_team} size="lg" showName />
              <div className="text-center text-sm text-muted-foreground">
                <div className="font-mono text-lg text-foreground mb-1">
                  {data.home_score} – {data.away_score}
                </div>
                <div>Final score</div>
                <div className="mt-2 text-xs">
                  Predicted: {data.matchup.predicted_winner} • {winProb}% • {projHome} – {projAway}
                </div>
              </div>
              <TeamBadge team={data.away_team} size="lg" showName />
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            <div className="card-surface rim-light p-5">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-1">Model Prediction</p>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Win probability</span>
                  <span className="font-mono text-foreground">{winProb}%</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Projected score</span>
                  <span className="font-mono text-foreground">{projHome}–{projAway}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Projected margin</span>
                  <span className="font-mono text-foreground">{projMargin.toFixed(1)} pts</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Projected total</span>
                  <span className="font-mono text-foreground">{projTotal.toFixed(1)} pts</span>
                </div>
              </div>
            </div>

            <div className="card-surface rim-light p-5 md:col-span-2">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-1">Efficiency Edges</p>
              <p className="text-xs text-muted-foreground mb-3">
                Stable matchup differentials that drive the v2 model outputs.
              </p>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
                {[
                  ["EPA Edge", "epa_edge"],
                  ["Success Rate Edge", "success_edge"],
                  ["Explosive Edge", "explosive_edge"],
                  ["Early-Down Edge", "early_down_success_edge"],
                  ["Third-Down Edge", "third_down_edge"],
                  ["Red Zone Edge", "redzone_edge"],
                  ["Sack/Pressure Edge", "sack_edge"],
                  ["Recent Form Edge", "recent_epa_edge"],
                  ["SOS Edge", "sos_edge"],
                ].map(([label, key]) => {
                  const v = (data.matchup.team_efficiency_edges as any)?.[key] as number | undefined;
                  const val = typeof v === "number" ? v.toFixed(3) : "—";
                  return (
                    <div key={key} className="bg-secondary/40 border border-border rounded-sm p-3">
                      <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
                      <div className="font-mono text-foreground">{val}</div>
                    </div>
                  );
                })}
              </div>
              <details className="mt-3 text-[11px] text-muted-foreground">
                <summary className="cursor-pointer underline-offset-2 underline">Developer view (raw payload)</summary>
                <pre className="mt-2 bg-secondary/50 rounded p-2 max-h-48 overflow-auto">
                  {JSON.stringify(data.matchup.team_efficiency_edges ?? {}, null, 2)}
                </pre>
              </details>
            </div>
          </div>

          <Tabs defaultValue="scout" className="space-y-4">
            <TabsList className="bg-secondary rounded-sm border border-border p-1 flex flex-wrap">
              <TabsTrigger value="scout" className="rounded-sm text-xs data-[state=active]:bg-card">
                Scouting Report
              </TabsTrigger>
              <TabsTrigger value="keys" className="rounded-sm text-xs data-[state=active]:bg-card">
                5 Keys Breakdown
              </TabsTrigger>
              <TabsTrigger value="ai" className="rounded-sm text-xs data-[state=active]:bg-card">
                AI Statistician
              </TabsTrigger>
              <TabsTrigger value="situational" className="rounded-sm text-xs data-[state=active]:bg-card">
                Situational Tendencies
              </TabsTrigger>
              <TabsTrigger value="broadcast" className="rounded-sm text-xs data-[state=active]:bg-card">
                Broadcast View
              </TabsTrigger>
            </TabsList>

            <TabsContent value="scout">
              <div className="card-surface rim-light p-6 space-y-4 text-sm">
                {data.scouting_report.summary && (
                  <p className="text-muted-foreground leading-relaxed">{data.scouting_report.summary}</p>
                )}
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground mb-2">
                      {data.home_team} Strengths
                    </h3>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {(data.scouting_report.team_a_strengths ?? []).map((s) => (
                        <li key={s}>{s}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground mb-2">
                      {data.away_team} Strengths
                    </h3>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {(data.scouting_report.team_b_strengths ?? []).map((s) => (
                        <li key={s}>{s}</li>
                      ))}
                    </ul>
                  </div>
                </div>
                {data.scouting_report.prediction_explanation && (
                  <div className="border-t border-border pt-3 text-xs text-muted-foreground">
                    {data.scouting_report.prediction_explanation}
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="ai">
              {data.ai_statistician ? (
                <div className="card-surface rim-light p-6 space-y-4 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                      AI Statistician
                    </h3>
                    <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground border border-border rounded-full px-2 py-0.5">
                      Provider: {import.meta.env.VITE_AI_MODE ?? "template"}
                    </span>
                  </div>
                  <p className="text-secondary-foreground mb-2">
                    {data.ai_statistician.summary}
                  </p>
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                      Top reasons
                    </h4>
                    <ul className="list-disc list-inside space-y-1">
                      {data.ai_statistician.top_3_reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                  {data.ai_statistician.why_prediction_was_right_or_wrong && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                        Why the model was right/wrong
                      </h4>
                      <p className="text-secondary-foreground">
                        {data.ai_statistician.why_prediction_was_right_or_wrong}
                      </p>
                    </div>
                  )}
                  {data.ai_statistician.confidence_note && (
                    <p className="text-xs text-muted-foreground">
                      {data.ai_statistician.confidence_note}
                    </p>
                  )}

                  <div className="border-t border-border pt-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                      Ask about this game
                    </h4>
                    <div className="flex flex-col md:flex-row gap-2">
                      <input
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder="Ask a question grounded in this report (e.g., 'What matters most in the red zone?')"
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
                              context_type: "historical_game",
                              season: data.season,
                              team_a: data.home_team,
                              team_b: data.away_team,
                              mode: data.season_type === "REG" ? "regular" : "opp_weighted",
                              game_id: data.game_id,
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
              ) : (
                <div className="card-surface rim-light p-6 text-sm text-muted-foreground">
                  AI explanation is not available for this game.
                </div>
              )}
            </TabsContent>

            <TabsContent value="keys">
              <div className="card-surface rim-light p-6 space-y-3 text-sm">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground mb-1">
                    5 Keys Breakdown
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Explainability layer summarizing pressure points (not the v2 model backbone).
                  </p>
                </div>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="bg-secondary/40 border border-border rounded-sm p-4">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-1">Why the model leaned</div>
                    <div className="text-sm text-foreground">{data.scouting_report.prediction_explanation ?? "—"}</div>
                  </div>
                  <div className="bg-secondary/40 border border-border rounded-sm p-4">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-1">Key strengths summary</div>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-1">{data.home_team}</div>
                        <ul className="list-disc list-inside space-y-1">
                          {(data.scouting_report.team_a_strengths ?? []).slice(0, 4).map((s) => <li key={s}>{s}</li>)}
                        </ul>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-1">{data.away_team}</div>
                        <ul className="list-disc list-inside space-y-1">
                          {(data.scouting_report.team_b_strengths ?? []).slice(0, 4).map((s) => <li key={s}>{s}</li>)}
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
                <details className="text-[11px] text-muted-foreground">
                  <summary className="cursor-pointer underline-offset-2 underline">Developer view (scouting JSON)</summary>
                  <pre className="mt-2 bg-secondary/50 rounded p-2 max-h-64 overflow-auto">
                    {JSON.stringify(data.scouting_report, null, 2)}
                  </pre>
                </details>
              </div>
            </TabsContent>

            <TabsContent value="situational">
              <div className="card-surface rim-light p-6 space-y-3 text-sm">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground mb-1">
                    Situational Tendencies
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    How each team performed by down, distance, and field position, and where the matchup tilted
                    situationally.
                  </p>
                </div>
                <details className="text-[11px] text-muted-foreground">
                  <summary className="cursor-pointer underline-offset-2 underline">Developer view (JSON)</summary>
                  <pre className="mt-2 bg-secondary/50 rounded p-2 max-h-64 overflow-auto">
                    {JSON.stringify(data.situational, null, 2)}
                  </pre>
                </details>
              </div>
            </TabsContent>

            <TabsContent value="broadcast">
              <div className="card-surface rim-light p-6 space-y-3 text-sm">
                {data.broadcast.headline && <h2 className="text-lg font-semibold">{data.broadcast.headline}</h2>}
                {data.broadcast.summary && <p className="text-muted-foreground">{data.broadcast.summary}</p>}
                {Array.isArray(data.broadcast.top_3_storylines) && data.broadcast.top_3_storylines.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground mb-1">
                      Top Storylines
                    </h3>
                    <ol className="list-decimal list-inside space-y-1">
                      {data.broadcast.top_3_storylines.map((s) => (
                        <li key={s}>{s}</li>
                      ))}
                    </ol>
                  </div>
                )}
                {Array.isArray(data.broadcast.talking_points) && data.broadcast.talking_points.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground mb-1">
                      Talking Points
                    </h3>
                    <ul className="list-disc list-inside space-y-1">
                      {data.broadcast.talking_points.map((t) => (
                        <li key={t}>{t}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </TabsContent>

            <div className="pt-2">
              <DeveloperDebugAccordion>
                <div className="grid md:grid-cols-2 gap-3">
                  <pre className="bg-secondary/50 rounded p-2 max-h-64 overflow-auto">{JSON.stringify(data.matchup, null, 2)}</pre>
                  <pre className="bg-secondary/50 rounded p-2 max-h-64 overflow-auto">{JSON.stringify({ scouting: data.scouting_report, situational: data.situational, broadcast: data.broadcast }, null, 2)}</pre>
                </div>
              </DeveloperDebugAccordion>
            </div>
          </Tabs>
        </div>
      </div>
    </div>
  );
}

