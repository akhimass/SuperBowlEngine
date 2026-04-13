import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import { Loader2, RefreshCw, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import Navbar from "@/components/layout/Navbar.tsx";
import {
  getDraftBoard,
  postDraftRecommend,
  postDraftAnalyst,
  postDraftTrade,
  aiChat,
  getTeamLogos,
  type ApiDraftBoard,
  type ApiDraftProspect,
} from "@/lib/api.ts";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const NFL_TEAMS = [
  "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB", "HOU",
  "IND", "JAX", "KC", "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG", "NYJ", "PHI",
  "PIT", "SEA", "SF", "TB", "TEN", "WAS",
];

type TableSortKey =
  | "player_name"
  | "prospect_score"
  | "final_draft_score"
  | "model_rank"
  | "consensus_rank"
  | "reach_risk"
  | "market_value_score";

function sortProspects(rows: ApiDraftProspect[], key: TableSortKey, dir: "asc" | "desc"): ApiDraftProspect[] {
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
      key === "prospect_score" ? a.prospect_score : key === "final_draft_score" ? a.final_draft_score : a.market_value_score,
      dir === "desc" ? -1e6 : 1e6,
    );
    const vb = num(
      key === "prospect_score" ? b.prospect_score : key === "final_draft_score" ? b.final_draft_score : b.market_value_score,
      dir === "desc" ? -1e6 : 1e6,
    );
    return (va - vb) * mul;
  });
}

function radarDataFor(p: ApiDraftBoard["prospects"][0]) {
  const r = p.radar;
  return [
    { metric: "Athleticism", value: r.athleticism, full: 100 },
    { metric: "Production", value: r.production, full: 100 },
    { metric: "Efficiency", value: r.efficiency, full: 100 },
    { metric: "Scheme fit", value: r.scheme_fit, full: 100 },
    { metric: "Team need", value: r.team_need, full: 100 },
  ];
}

export default function DraftRoom() {
  const [team, setTeam] = useState("CAR");
  const [combineSeason, setCombineSeason] = useState(2025);
  const [cfbSeason, setCfbSeason] = useState(2024);
  const [evalSeason, setEvalSeason] = useState(2024);
  const [pickNumber, setPickNumber] = useState(19);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [chatQ, setChatQ] = useState("What happens if we pass on the top levered player?");
  const [chatOut, setChatOut] = useState("");
  const [tableSortKey, setTableSortKey] = useState<TableSortKey>("final_draft_score");
  const [tableSortDir, setTableSortDir] = useState<"asc" | "desc">("desc");
  const [maxTradeTarget, setMaxTradeTarget] = useState(47);

  const logosQ = useQuery({ queryKey: ["team-logos"], queryFn: getTeamLogos });

  useEffect(() => {
    setCfbSeason(combineSeason - 1);
  }, [combineSeason]);

  useEffect(() => {
    setMaxTradeTarget(pickNumber + 28);
  }, [pickNumber]);

  const boardQ = useQuery({
    queryKey: ["draft-board", team, combineSeason, evalSeason, cfbSeason],
    queryFn: () => getDraftBoard(team, combineSeason, evalSeason, cfbSeason),
    staleTime: 60_000,
  });

  const selected = useMemo(() => {
    if (!boardQ.data?.prospects || !selectedId) return null;
    return boardQ.data.prospects.find((x) => x.player_id === selectedId) ?? null;
  }, [boardQ.data, selectedId]);

  const recMut = useMutation({
    mutationFn: () =>
      postDraftRecommend({
        team,
        combine_season: combineSeason,
        eval_season: evalSeason,
        pick_number: pickNumber,
        n_simulations: 600,
        temperature: 2.0,
        cfb_season: cfbSeason,
      }),
  });

  const analystMut = useMutation({
    mutationFn: () =>
      postDraftAnalyst({
        team,
        combine_season: combineSeason,
        eval_season: evalSeason,
        pick_number: pickNumber,
        n_simulations: 600,
        temperature: 2.0,
        ai_mode: "template",
        cfb_season: cfbSeason,
      }),
  });

  const tradeMut = useMutation({
    mutationFn: () =>
      postDraftTrade({
        team,
        combine_season: combineSeason,
        eval_season: evalSeason,
        current_pick: pickNumber,
        max_target_pick: maxTradeTarget,
        n_simulations: 500,
        temperature: 2.0,
        cfb_season: cfbSeason,
      }),
  });

  const runIntel = () => {
    recMut.mutate();
    analystMut.mutate();
  };

  const topRec = recMut.data?.recommendations?.[0];
  const topAvail = topRec?.availability_at_pick;

  const sendChat = async () => {
    if (!chatQ.trim()) return;
    setChatOut("…");
    try {
      const res = await aiChat({
        question: chatQ,
        context_type: "draft",
        draft_team: team,
        combine_season: combineSeason,
        eval_season: evalSeason,
        pick_number: pickNumber,
        ai_mode: "template",
        cfb_season: cfbSeason,
      });
      setChatOut(res.answer);
    } catch (e) {
      setChatOut(e instanceof Error ? e.message : "Chat failed");
    }
  };

  const displayTeams = useMemo(() => {
    const m = logosQ.data?.teams;
    if (m && Object.keys(m).length) return Object.keys(m).sort();
    return NFL_TEAMS;
  }, [logosQ.data]);

  const sortedBoardRows = useMemo(() => {
    const rows = boardQ.data?.prospects ?? [];
    return sortProspects(rows, tableSortKey, tableSortDir);
  }, [boardQ.data?.prospects, tableSortKey, tableSortDir]);

  const toggleTableSort = (k: TableSortKey) => {
    if (k === tableSortKey) {
      setTableSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setTableSortKey(k);
      setTableSortDir(
        k === "player_name" || k === "model_rank" || k === "consensus_rank" ? "asc" : "desc",
      );
    }
  };

  const sortHeaderClass = (k: TableSortKey) =>
    `cursor-pointer select-none hover:text-lime-300 ${tableSortKey === k ? "text-lime-400" : ""}`;

  const fourModes = recMut.data?.four_ranking_modes;
  const consensusMeta = boardQ.data?.meta?.consensus as { consensus_configured?: boolean } | undefined;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <Navbar />
      <main className="container pt-20 pb-16">
        <header className="mb-8 border-b border-zinc-800 pb-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-lime-400/90">
            GridironIQ · Draft Intelligence
          </p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-white md:text-4xl">
            Draft Decision Room
            {team === "CAR" && (
              <span className="ml-3 align-middle text-base font-semibold text-lime-400/90">
                · Panthers front-office preset
              </span>
            )}
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-zinc-400">
            Prospect grades from nflverse combine + career tables, optional CollegeFootballData.com
            (CFBD) season stats for college production, team needs from EPA/snap/injury signals,
            Monte Carlo availability, and levered recommendations.
          </p>
          <p className="mt-4">
            <Link
              to="/draft/simulator"
              className="text-sm font-semibold text-lime-400 underline-offset-4 hover:underline"
            >
              2026 Round 1 mock draft simulator →
            </Link>
          </p>
        </header>

        {boardQ.data?.meta?.cfb != null && (
          <div
            className={`mb-4 rounded-md border px-4 py-3 text-sm ${
              (boardQ.data.meta.cfb as { cfb_error?: string }).cfb_error
                ? "border-amber-700/60 bg-amber-950/40 text-amber-100"
                : (boardQ.data.meta.cfb as { cfb_enabled?: boolean }).cfb_enabled
                  ? "border-lime-700/50 bg-lime-950/30 text-lime-100"
                  : "border-zinc-700 bg-zinc-900/60 text-zinc-400"
            }`}
          >
            {(boardQ.data.meta.cfb as { cfb_enabled?: boolean }).cfb_enabled &&
            !(boardQ.data.meta.cfb as { cfb_error?: string }).cfb_error ? (
              <>
                <span className="font-semibold text-lime-300">CFBD integrated</span> — college season{" "}
                {(boardQ.data.meta.cfb as { cfb_season?: number }).cfb_season}: matched{" "}
                {(boardQ.data.meta.cfb as { cfb_match_count?: number }).cfb_match_count} prospects (
                {(
                  ((boardQ.data.meta.cfb as { cfb_match_rate?: number }).cfb_match_rate ?? 0) * 100
                ).toFixed(1)}
                %).
              </>
            ) : (boardQ.data.meta.cfb as { cfb_error?: string }).cfb_error ? (
              <>
                <span className="font-semibold">CFBD request failed:</span>{" "}
                {String((boardQ.data.meta.cfb as { cfb_error?: string }).cfb_error)}
              </>
            ) : (
              <>
                <span className="font-semibold text-zinc-300">CFBD not configured.</span> Set environment
                variable <code className="rounded bg-zinc-800 px-1">CFBD_API_KEY</code> (get a key at{" "}
                <a
                  className="text-lime-400 underline"
                  href="https://collegefootballdata.com/key"
                  target="_blank"
                  rel="noreferrer"
                >
                  collegefootballdata.com
                </a>
                ).
              </>
            )}
          </div>
        )}

        <div className="mb-6 grid gap-4 rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 md:grid-cols-2 lg:grid-cols-7">
          <div className="space-y-2">
            <Label className="text-zinc-400">Team</Label>
            <Select value={team} onValueChange={setTeam}>
              <SelectTrigger className="border-zinc-700 bg-zinc-950">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {displayTeams.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="text-zinc-400">Combine season</Label>
            <Input
              type="number"
              className="border-zinc-700 bg-zinc-950"
              value={combineSeason}
              onChange={(e) => setCombineSeason(Number(e.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label className="text-zinc-400">CFB stats season (CFBD)</Label>
            <Input
              type="number"
              className="border-zinc-700 bg-zinc-950"
              value={cfbSeason}
              onChange={(e) => setCfbSeason(Number(e.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label className="text-zinc-400">Eval season (NFL)</Label>
            <Input
              type="number"
              className="border-zinc-700 bg-zinc-950"
              value={evalSeason}
              onChange={(e) => setEvalSeason(Number(e.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label className="text-zinc-400">Pick #</Label>
            <Input
              type="number"
              className="border-zinc-700 bg-zinc-950"
              value={pickNumber}
              onChange={(e) => setPickNumber(Number(e.target.value))}
            />
          </div>
          <div className="flex items-end gap-2 lg:col-span-2">
            <Button
              className="w-full bg-lime-500 font-bold text-zinc-950 hover:bg-lime-400"
              onClick={runIntel}
              disabled={recMut.isPending || analystMut.isPending || boardQ.isLoading}
            >
              {(recMut.isPending || analystMut.isPending) && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Run simulation + AI brief
            </Button>
            <Button
              variant="outline"
              className="border-zinc-600 bg-zinc-950"
              onClick={() => boardQ.refetch()}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-12">
          {/* Left: table */}
          <Card className="border-zinc-800 bg-zinc-900/40 lg:col-span-4">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg text-white">Available class (combine board)</CardTitle>
              <CardDescription className="text-zinc-500">
                Click column headers to sort. Consensus columns populate when{" "}
                <code className="rounded bg-zinc-800 px-1">GRIDIRONIQ_DRAFT_CONSENSUS_DIR</code> has real
                board files.
                {consensusMeta?.consensus_configured === false && (
                  <span className="mt-1 block text-amber-200/90">
                    No external consensus boards matched — ranks show model-only until you add CSV/JSON
                    boards.
                  </span>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {boardQ.isLoading && (
                <div className="flex items-center gap-2 p-6 text-zinc-500">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading nflverse…
                </div>
              )}
              {boardQ.error && (
                <p className="p-6 text-sm text-red-400">
                  {(boardQ.error as Error).message || "Failed to load board"}
                </p>
              )}
              {boardQ.data && (
                <ScrollArea className="h-[560px]">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-zinc-800 hover:bg-transparent">
                        <TableHead
                          className={`text-zinc-400 ${sortHeaderClass("player_name")}`}
                          onClick={() => toggleTableSort("player_name")}
                        >
                          Player{tableSortKey === "player_name" ? (tableSortDir === "asc" ? " ↑" : " ↓") : ""}
                        </TableHead>
                        <TableHead className="text-zinc-400">Pos</TableHead>
                        <TableHead
                          className={`text-right text-zinc-400 ${sortHeaderClass("prospect_score")}`}
                          onClick={() => toggleTableSort("prospect_score")}
                        >
                          Prospect
                          {tableSortKey === "prospect_score"
                            ? tableSortDir === "asc"
                              ? " ↑"
                              : " ↓"
                            : ""}
                        </TableHead>
                        <TableHead
                          className={`text-right text-zinc-400 ${sortHeaderClass("final_draft_score")}`}
                          onClick={() => toggleTableSort("final_draft_score")}
                        >
                          Final
                          {tableSortKey === "final_draft_score"
                            ? tableSortDir === "asc"
                              ? " ↑"
                              : " ↓"
                            : ""}
                        </TableHead>
                        <TableHead
                          className={`text-right text-zinc-400 ${sortHeaderClass("model_rank")}`}
                          onClick={() => toggleTableSort("model_rank")}
                        >
                          Mdl#
                          {tableSortKey === "model_rank" ? (tableSortDir === "asc" ? " ↑" : " ↓") : ""}
                        </TableHead>
                        <TableHead
                          className={`text-right text-zinc-400 ${sortHeaderClass("consensus_rank")}`}
                          onClick={() => toggleTableSort("consensus_rank")}
                        >
                          Cons
                          {tableSortKey === "consensus_rank"
                            ? tableSortDir === "asc"
                              ? " ↑"
                              : " ↓"
                            : ""}
                        </TableHead>
                        <TableHead
                          className={`text-right text-zinc-400 ${sortHeaderClass("reach_risk")}`}
                          onClick={() => toggleTableSort("reach_risk")}
                        >
                          Reach
                          {tableSortKey === "reach_risk"
                            ? tableSortDir === "asc"
                              ? " ↑"
                              : " ↓"
                            : ""}
                        </TableHead>
                        <TableHead
                          className={`text-right text-zinc-400 ${sortHeaderClass("market_value_score")}`}
                          onClick={() => toggleTableSort("market_value_score")}
                        >
                          Mkt
                          {tableSortKey === "market_value_score"
                            ? tableSortDir === "asc"
                              ? " ↑"
                              : " ↓"
                            : ""}
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sortedBoardRows.map((p) => (
                        <TableRow
                          key={p.player_id}
                          className={`cursor-pointer border-zinc-800 ${
                            selectedId === p.player_id ? "bg-lime-500/10" : "hover:bg-zinc-800/50"
                          }`}
                          onClick={() => setSelectedId(p.player_id)}
                        >
                          <TableCell className="font-medium text-zinc-100">{p.player_name}</TableCell>
                          <TableCell className="text-zinc-400">{p.pos}</TableCell>
                          <TableCell className="text-right tabular-nums text-zinc-300">
                            {p.prospect_score.toFixed(1)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-lime-400">
                            {p.final_draft_score.toFixed(1)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-zinc-400">
                            {p.model_rank != null ? String(p.model_rank) : "—"}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-zinc-400">
                            {p.consensus_rank != null ? Number(p.consensus_rank).toFixed(1) : "—"}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-zinc-400">
                            {p.reach_risk != null ? Number(p.reach_risk).toFixed(1) : "—"}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-zinc-400">
                            {p.market_value_score != null ? Number(p.market_value_score).toFixed(1) : "—"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              )}
            </CardContent>
          </Card>

          {/* Center: detail */}
          <Card className="border-zinc-800 bg-zinc-900/40 lg:col-span-5">
            <CardHeader>
              <CardTitle className="text-lg text-white">Player profile</CardTitle>
              <CardDescription className="text-zinc-500">
                Radar uses the same five axes shown to the model (0–100 scales).
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!selected && (
                <p className="text-sm text-zinc-500">Select a prospect from the board.</p>
              )}
              {selected && (
                <div className="grid gap-6 md:grid-cols-2">
                  <div>
                    <h3 className="text-xl font-bold text-white">{selected.player_name}</h3>
                    <p className="text-sm text-zinc-400">
                      {selected.pos} · {selected.school}
                    </p>
                    <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
                      <div className="rounded-md border border-zinc-800 bg-zinc-950/80 p-3">
                        <dt className="text-xs uppercase text-zinc-500">Prospect</dt>
                        <dd className="text-lg font-semibold text-lime-400">{selected.prospect_score}</dd>
                      </div>
                      <div className="rounded-md border border-zinc-800 bg-zinc-950/80 p-3">
                        <dt className="text-xs uppercase text-zinc-500">Final (team)</dt>
                        <dd className="text-lg font-semibold text-white">{selected.final_draft_score}</dd>
                      </div>
                      <div className="rounded-md border border-zinc-800 bg-zinc-950/80 p-3">
                        <dt className="text-xs uppercase text-zinc-500">Need</dt>
                        <dd className="text-lg font-semibold text-zinc-200">{selected.team_need_score}</dd>
                      </div>
                      <div className="rounded-md border border-zinc-800 bg-zinc-950/80 p-3">
                        <dt className="text-xs uppercase text-zinc-500">Scheme fit</dt>
                        <dd className="text-lg font-semibold text-zinc-200">{selected.scheme_fit_score}</dd>
                      </div>
                      <div className="rounded-md border border-zinc-800 bg-zinc-950/80 p-3">
                        <dt className="text-xs uppercase text-zinc-500">Model rank</dt>
                        <dd className="text-lg font-semibold text-zinc-200">
                          {selected.model_rank != null ? selected.model_rank : "—"}
                        </dd>
                      </div>
                      <div className="rounded-md border border-zinc-800 bg-zinc-950/80 p-3">
                        <dt className="text-xs uppercase text-zinc-500">Consensus</dt>
                        <dd className="text-lg font-semibold text-zinc-200">
                          {selected.consensus_rank != null ? Number(selected.consensus_rank).toFixed(1) : "—"}
                        </dd>
                      </div>
                      <div className="rounded-md border border-zinc-800 bg-zinc-950/80 p-3">
                        <dt className="text-xs uppercase text-zinc-500">Reach risk</dt>
                        <dd className="text-lg font-semibold text-zinc-200">
                          {selected.reach_risk != null ? Number(selected.reach_risk).toFixed(2) : "—"}
                        </dd>
                      </div>
                      <div className="rounded-md border border-zinc-800 bg-zinc-950/80 p-3">
                        <dt className="text-xs uppercase text-zinc-500">Market value</dt>
                        <dd className="text-lg font-semibold text-zinc-200">
                          {selected.market_value_score != null
                            ? Number(selected.market_value_score).toFixed(1)
                            : "—"}
                        </dd>
                      </div>
                    </dl>
                    <div className="mt-4 text-xs text-zinc-500">
                      Production source:{" "}
                      <span className="text-zinc-300">
                        {selected.score_breakdown.prospect.production_source}
                      </span>
                    </div>
                    {selected.score_breakdown.cfb && (
                      <div className="mt-2 rounded-md border border-zinc-800 bg-zinc-950/60 p-2 text-xs text-zinc-400">
                        <span className="font-semibold text-lime-400/90">CFBD match</span> — season{" "}
                        {String(
                          (selected.score_breakdown.cfb as Record<string, unknown>).cfb_season ?? "",
                        )}
                        , production pct{" "}
                        {String((selected.score_breakdown.cfb as Record<string, unknown>).cfb_production_score)}
                        , efficiency pct{" "}
                        {String((selected.score_breakdown.cfb as Record<string, unknown>).cfb_efficiency_score)}
                      </div>
                    )}
                  </div>
                  <div className="h-[280px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={radarDataFor(selected)} cx="50%" cy="50%" outerRadius="75%">
                        <PolarGrid stroke="#3f3f46" />
                        <PolarAngleAxis dataKey="metric" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
                        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#71717a" }} />
                        <Radar
                          name={selected.player_name}
                          dataKey="value"
                          stroke="#a3e635"
                          fill="#a3e635"
                          fillOpacity={0.35}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="md:col-span-2">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                      Combine metrics (nflverse)
                    </p>
                    <Table>
                      <TableBody>
                        {[
                          ["40 yd", selected.forty],
                          ["Vertical", selected.vertical],
                          ["Bench", selected.bench],
                          ["Broad", selected.broad_jump],
                          ["3-cone", selected.cone],
                          ["Shuttle", selected.shuttle],
                        ].map(([k, v]) => (
                          <TableRow key={k} className="border-zinc-800">
                            <TableCell className="text-zinc-400">{k}</TableCell>
                            <TableCell className="text-right text-zinc-200">
                              {v != null ? String(v) : "—"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Right: recommendation + AI */}
          <div className="space-y-6 lg:col-span-3">
            <Card className="border-zinc-800 bg-zinc-900/40">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg text-white">Draft recommendation</CardTitle>
                <CardDescription className="text-zinc-500">
                  Levered score weights availability at your pick (simulation-driven).
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {!topRec && (
                  <p className="text-sm text-zinc-500">Run simulation to populate this card.</p>
                )}
                {topRec && (
                  <>
                    <div className="rounded-lg border border-lime-500/30 bg-lime-500/5 p-4">
                      <p className="text-xs uppercase text-lime-400/90">Top levered</p>
                      <p className="text-lg font-bold text-white">
                        {topRec.player_name}{" "}
                        <span className="text-zinc-400">({topRec.pos})</span>
                      </p>
                      <p className="mt-1 text-sm text-zinc-400">
                        Final {Number(topRec.final_draft_score).toFixed(1)} · Leverage{" "}
                        {Number(topRec.leverage_score).toFixed(1)}
                      </p>
                      <p className="mt-2 text-sm text-zinc-300">
                        Simulated availability at pick {pickNumber}:{" "}
                        <span className="font-mono text-lime-300">
                          {topAvail != null ? `${(Number(topAvail) * 100).toFixed(1)}%` : "—"}
                        </span>
                      </p>
                    </div>
                    <div className="text-xs text-zinc-500">
                      {recMut.data?.simulation?.n_simulations} draws · temp{" "}
                      {recMut.data?.simulation?.temperature}
                    </div>
                  </>
                )}
                {fourModes && (
                  <Tabs defaultValue="best_player_available" className="mt-4 w-full">
                    <TabsList className="flex h-auto w-full flex-wrap gap-1 bg-zinc-800/80 p-1">
                      <TabsTrigger
                        value="best_player_available"
                        className="text-xs data-[state=active]:bg-zinc-950 data-[state=active]:text-lime-300"
                      >
                        BPA
                      </TabsTrigger>
                      <TabsTrigger
                        value="best_fit"
                        className="text-xs data-[state=active]:bg-zinc-950 data-[state=active]:text-lime-300"
                      >
                        Best fit
                      </TabsTrigger>
                      <TabsTrigger
                        value="highest_upside"
                        className="text-xs data-[state=active]:bg-zinc-950 data-[state=active]:text-lime-300"
                      >
                        Upside
                      </TabsTrigger>
                      <TabsTrigger
                        value="safest_pick"
                        className="text-xs data-[state=active]:bg-zinc-950 data-[state=active]:text-lime-300"
                      >
                        Safest
                      </TabsTrigger>
                    </TabsList>
                    {(
                      [
                        ["best_player_available", "Best player available"],
                        ["best_fit", "Best fit (team)"],
                        ["highest_upside", "Highest upside"],
                        ["safest_pick", "Safest pick"],
                      ] as const
                    ).map(([key, label]) => (
                      <TabsContent key={key} value={key} className="mt-3 rounded-md border border-zinc-800 p-3">
                        <p className="mb-2 text-xs font-semibold uppercase text-zinc-500">{label}</p>
                        <ul className="space-y-1 text-sm text-zinc-300">
                          {(fourModes[key] ?? []).slice(0, 8).map((row) => (
                            <li key={String(row.player_id)} className="flex justify-between gap-2">
                              <span className="truncate text-zinc-100">
                                <span className="font-mono text-zinc-500">#{row.mode_rank}</span>{" "}
                                {String(row.player_name)}{" "}
                                <span className="text-zinc-500">({String(row.pos)})</span>
                              </span>
                              <span className="shrink-0 tabular-nums text-lime-400/90">
                                {Number(row.prospect_score ?? row.final_draft_score ?? 0).toFixed(1)}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </TabsContent>
                    ))}
                  </Tabs>
                )}
              </CardContent>
            </Card>

            <Card className="border-zinc-800 bg-zinc-900/40">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg text-white">AI Draft Analyst</CardTitle>
                <CardDescription className="text-zinc-500">
                  Structured brief grounded in the live board JSON (template provider default).
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {analystMut.data && (
                  <>
                    <div>
                      <p className="text-xs font-semibold uppercase text-zinc-500">Best pick</p>
                      <p className="text-zinc-200">{analystMut.data.best_pick_explanation}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase text-zinc-500">Risk</p>
                      <p className="text-zinc-200">{analystMut.data.risk_analysis}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase text-zinc-500">Alternatives</p>
                      <ul className="list-disc pl-4 text-zinc-300">
                        {(analystMut.data.alternative_picks ?? []).map((x) => (
                          <li key={x}>{x}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase text-zinc-500">If we pass</p>
                      <p className="text-zinc-200">{analystMut.data.if_we_pass}</p>
                    </div>
                    {(analystMut.data.why_not_other_targets?.length ?? 0) > 0 && (
                      <div>
                        <p className="text-xs font-semibold uppercase text-zinc-500">Why not others</p>
                        <ul className="list-disc pl-4 text-zinc-300">
                          {(analystMut.data.why_not_other_targets ?? []).map((x) => (
                            <li key={x}>{x}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {analystMut.data.alternate_outcomes && (
                      <div>
                        <p className="text-xs font-semibold uppercase text-zinc-500">Alternate outcomes</p>
                        <p className="text-zinc-200 whitespace-pre-wrap">
                          {analystMut.data.alternate_outcomes}
                        </p>
                      </div>
                    )}
                  </>
                )}
                {!analystMut.data && !analystMut.isPending && (
                  <p className="text-zinc-500">Run simulation + AI brief to generate analyst copy.</p>
                )}
                {analystMut.isPending && (
                  <div className="flex items-center gap-2 text-zinc-500">
                    <Loader2 className="h-4 w-4 animate-spin" /> Generating…
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-zinc-800 bg-zinc-900/40">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg text-white">Ask the analyst</CardTitle>
                <CardDescription className="text-zinc-500">
                  Draft-mode chat uses the same nflverse-backed context (no matchup required).
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <Textarea
                  value={chatQ}
                  onChange={(e) => setChatQ(e.target.value)}
                  className="min-h-[72px] border-zinc-700 bg-zinc-950"
                />
                <Button
                  className="w-full bg-zinc-100 font-semibold text-zinc-950 hover:bg-white"
                  onClick={sendChat}
                >
                  <Send className="mr-2 h-4 w-4" />
                  Send
                </Button>
                {chatOut && (
                  <div className="rounded-md border border-zinc-800 bg-zinc-950/80 p-3 text-sm text-zinc-200 whitespace-pre-wrap">
                    {chatOut}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        <Card className="mt-8 border-zinc-800 bg-zinc-900/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg text-white">Trade-down scan</CardTitle>
            <CardDescription className="text-zinc-500">
              Monte Carlo screening: expected value proxy vs trading from pick {pickNumber} to later slots
              (independent-availability approximation — use for relative ranking only).
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 md:flex-row md:items-end">
            <div className="space-y-2">
              <Label className="text-zinc-400">Max target pick #</Label>
              <Input
                type="number"
                className="max-w-[140px] border-zinc-700 bg-zinc-950"
                value={maxTradeTarget}
                min={pickNumber + 1}
                onChange={(e) => setMaxTradeTarget(Number(e.target.value))}
              />
            </div>
            <Button
              className="bg-zinc-100 font-semibold text-zinc-950 hover:bg-white md:mb-0.5"
              disabled={tradeMut.isPending || boardQ.isLoading || maxTradeTarget <= pickNumber}
              onClick={() => tradeMut.mutate()}
            >
              {tradeMut.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Run trade scan
            </Button>
            {tradeMut.error && (
              <p className="text-sm text-red-400">
                {(tradeMut.error as Error).message || "Trade scan failed"}
              </p>
            )}
          </CardContent>
          {tradeMut.data?.trade_down_scan && tradeMut.data.trade_down_scan.length > 0 && (
            <CardContent className="border-t border-zinc-800 pt-4">
              <p className="mb-2 text-xs font-semibold uppercase text-zinc-500">Best slots by EV delta</p>
              <Table>
                <TableHeader>
                  <TableRow className="border-zinc-800">
                    <TableHead className="text-zinc-400">Target pick</TableHead>
                    <TableHead className="text-right text-zinc-400">EV Δ</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tradeMut.data.trade_down_scan.map((r) => (
                    <TableRow key={r.target_pick} className="border-zinc-800">
                      <TableCell className="font-mono text-zinc-200">{r.target_pick}</TableCell>
                      <TableCell className="text-right tabular-nums text-lime-400">
                        {Number(r.ev_delta).toFixed(3)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          )}
        </Card>
      </main>
    </div>
  );
}
