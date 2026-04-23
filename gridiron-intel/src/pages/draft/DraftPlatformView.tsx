import type { ReactNode } from "react";
import { Loader2, RefreshCw, Send } from "lucide-react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type {
  ApiDraftAnalystResponse,
  ApiDraftBoard,
  ApiDraftProspect,
  ApiDraftRecommendResponse,
} from "@/lib/api.ts";
import DraftSimulator from "../DraftSimulator.tsx";
import type { BoardViewTab, DraftModule, PosFilter } from "./draftBoardUtils.ts";
import { prospectPosPill } from "./draftBoardUtils.ts";
import type { TableSortKey } from "./draftBoardUtils.ts";

function radarDataFor(p: ApiDraftProspect) {
  const r = p.radar;
  return [
    { metric: "Athleticism", value: r.athleticism, full: 100 },
    { metric: "Production", value: r.production, full: 100 },
    { metric: "Efficiency", value: r.efficiency, full: 100 },
    { metric: "Scheme fit", value: r.scheme_fit, full: 100 },
    { metric: "Team need", value: r.team_need, full: 100 },
  ];
}

function needScoresFromBoard(board: ApiDraftBoard | undefined): Record<string, number> {
  const raw = board?.team_needs as { need_scores?: Record<string, number> } | undefined;
  return raw?.need_scores ?? {};
}

function NavBtn({
  icon,
  label,
  active,
  onClick,
  badge,
  badgeVariant,
}: {
  icon: ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
  badge?: string;
  badgeVariant?: "new" | "beta" | "count";
}) {
  return (
    <button type="button" onClick={onClick} className={`giq-nav-item ${active ? "giq-nav-item-active" : ""}`}>
      <span className="ni-icon w-3.5 shrink-0 text-center text-[12px]">{icon}</span>
      <span className="min-w-0 flex-1 tracking-wide">{label}</span>
      {badge != null && (
        <span
          className={`giq-nav-badge ${badgeVariant === "new" ? "giq-nav-badge-new" : ""} ${
            badgeVariant === "beta" ? "bg-[#29b8e0] text-[#050709]" : ""
          }`}
        >
          {badge}
        </span>
      )}
    </button>
  );
}

export interface DraftPlatformViewProps {
  draftModule: DraftModule;
  setDraftModule: (m: DraftModule) => void;
  posFilter: PosFilter;
  setPosFilter: (f: PosFilter) => void;
  boardViewTab: BoardViewTab;
  setBoardViewTab: (t: BoardViewTab) => void;
  board: ApiDraftBoard | undefined;
  boardLoading: boolean;
  boardError: Error | null;
  displayRows: ApiDraftProspect[];
  selected: ApiDraftProspect | null;
  selectedId: string | null;
  setSelectedId: (id: string | null) => void;
  toggleTableSort: (k: TableSortKey) => void;
  sortHeaderClass: (k: TableSortKey) => string;
  team: string;
  setTeam: (t: string) => void;
  displayTeams: string[];
  combineSeason: number;
  setCombineSeason: (n: number) => void;
  cfbSeason: number;
  setCfbSeason: (n: number) => void;
  evalSeason: number;
  setEvalSeason: (n: number) => void;
  pickNumber: number;
  setPickNumber: (n: number) => void;
  maxTradeTarget: number;
  setMaxTradeTarget: (n: number) => void;
  runIntel: () => void;
  intelBusy: boolean;
  recData: ApiDraftRecommendResponse | undefined;
  analystData: ApiDraftAnalystResponse | undefined;
  analystPending: boolean;
  tradePending: boolean;
  tradeError: Error | null;
  tradeScan:
    | { target_pick: number; ev_delta: number }[]
    | undefined;
  runTrade: () => void;
  compareIdB: string | null;
  setCompareIdB: (id: string | null) => void;
  chatQ: string;
  setChatQ: (s: string) => void;
  chatOut: string;
  sendChat: () => void;
  consensusConfigured: boolean | undefined;
  refetchBoard: () => void;
}

const BOARD_TABS: { id: BoardViewTab; label: string }[] = [
  { id: "consensus_board", label: "CONSENSUS_BOARD" },
  { id: "model_board", label: "MODEL_BOARD" },
  { id: "r1_projections_tab", label: "R1_PROJECTIONS" },
  { id: "rmu_predictions", label: "RMU_PREDICTIONS" },
  { id: "by_team_fit", label: "BY_TEAM_FIT" },
];

export default function DraftPlatformView(p: DraftPlatformViewProps) {
  const topRec = p.recData?.recommendations?.[0] as
    | {
        player_name?: string;
        pos?: string;
        final_draft_score?: number;
        leverage_score?: number;
        availability_at_pick?: number;
      }
    | undefined;
  const topAvail = topRec?.availability_at_pick;
  const fourModes = p.recData?.four_ranking_modes;
  const needScores = needScoresFromBoard(p.board);
  const needEntries = Object.entries(needScores).sort((a, b) => b[1] - a[1]);
  const compareB =
    p.board?.prospects?.find((x) => x.player_id === p.compareIdB) ??
    (p.compareIdB ? null : p.board?.prospects?.[1] ?? null);

  const boardTitle =
    p.draftModule === "prospect_db"
      ? "// PROSPECT_DB — LIVE nflverse BOARD"
      : "// 2026 NFL DRAFT — BIG_BOARD";

  const showBoardChrome = p.draftModule === "big_board" || p.draftModule === "prospect_db";

  const topScore = p.displayRows[0]?.final_draft_score ?? p.board?.prospects?.[0]?.final_draft_score;

  return (
    <main className="giq-draft-layout">
      {/* LEFT */}
      <aside className="giq-draft-left max-h-[calc(100vh-3.5rem)] overflow-y-auto lg:max-h-none">
        <div className="giq-panel-section">
          <div className="giq-panel-title">BOARD_MODULES</div>
          <NavBtn
            icon="◈"
            label="BIG_BOARD"
            badge="32"
            badgeVariant="count"
            active={p.draftModule === "big_board"}
            onClick={() => p.setDraftModule("big_board")}
          />
          <NavBtn
            icon="◎"
            label="R1_PROJECTIONS"
            active={p.draftModule === "r1_projections"}
            onClick={() => p.setDraftModule("r1_projections")}
          />
          <NavBtn
            icon="⊞"
            label="PROSPECT_DB"
            active={p.draftModule === "prospect_db"}
            onClick={() => p.setDraftModule("prospect_db")}
          />
          <NavBtn
            icon="▶"
            label="SIMULATOR"
            active={p.draftModule === "simulator"}
            onClick={() => p.setDraftModule("simulator")}
          />
          <NavBtn
            icon="⇄"
            label="COMPARE"
            active={p.draftModule === "compare"}
            onClick={() => p.setDraftModule("compare")}
          />
        </div>
        <div className="giq-panel-section">
          <div className="giq-panel-title">ANALYTICS</div>
          <NavBtn
            icon="⚙"
            label="MODEL_INTEL"
            badge="NEW"
            badgeVariant="new"
            active={p.draftModule === "model_intel"}
            onClick={() => p.setDraftModule("model_intel")}
          />
          <NavBtn
            icon="◉"
            label="TEAM_NEEDS"
            active={p.draftModule === "team_needs"}
            onClick={() => p.setDraftModule("team_needs")}
          />
          <NavBtn
            icon="≋"
            label="SCHEME_FIT"
            active={p.draftModule === "scheme_fit"}
            onClick={() => p.setDraftModule("scheme_fit")}
          />
          <NavBtn
            icon="⬡"
            label="COMBINE_LAB"
            active={p.draftModule === "combine_lab"}
            onClick={() => p.setDraftModule("combine_lab")}
          />
          <NavBtn
            icon="∿"
            label="TREND_SIGNALS"
            active={p.draftModule === "trend_signals"}
            onClick={() => p.setDraftModule("trend_signals")}
          />
        </div>
        <div className="giq-panel-section">
          <div className="giq-panel-title">POSITION_FILTER</div>
          {(
            [
              ["ALL", "—", "ALL_POSITIONS"] as const,
              ["QB", "QB", "QUARTERBACKS"] as const,
              ["WR", "WR", "WIDE_RECEIVERS"] as const,
              ["RB", "RB", "RUNNING_BACKS"] as const,
              ["EDGE_DL", "—", "EDGE / DL"] as const,
              ["OT_IOL", "—", "OT / IOL"] as const,
              ["DB_LB", "—", "DB / LB"] as const,
            ] as const
          ).map(([id, mark, lab]) => (
            <NavBtn
              key={id}
              icon={<span className="text-[9px]">{mark}</span>}
              label={lab}
              active={p.posFilter === id}
              onClick={() => p.setPosFilter(id)}
            />
          ))}
        </div>
      </aside>

      {/* CENTER */}
      <div className="giq-draft-center min-w-0">
        {p.draftModule === "simulator" && (
          <div className="border-b border-white/[0.06] p-3">
            <DraftSimulator />
          </div>
        )}

        {showBoardChrome && (
          <>
            <div className="giq-kpi-bar">
              <div className="giq-kpi-item">
                <div className="giq-kpi-label">PICK_SLOT</div>
                <div className="giq-kpi-value text-[22px]">{p.pickNumber}</div>
                <div className="giq-kpi-delta">{p.team} · BOARD_ROWS</div>
              </div>
              <div className="giq-kpi-item">
                <div className="giq-kpi-label">PROSPECTS</div>
                <div className="giq-kpi-value text-[22px]">{p.board?.prospects?.length ?? "—"}</div>
                <div className="giq-kpi-delta">nflverse combine</div>
              </div>
              <div className="giq-kpi-item">
                <div className="giq-kpi-label">FILTERED</div>
                <div className="giq-kpi-value text-[22px]">{p.displayRows.length}</div>
                <div className="giq-kpi-delta">POS + TAB</div>
              </div>
              <div className="giq-kpi-item">
                <div className="giq-kpi-label">TOP_FINAL</div>
                <div className="giq-kpi-value text-[22px]">{topScore != null ? topScore.toFixed(1) : "—"}</div>
                <div className="giq-kpi-delta">MODEL_LAYER</div>
              </div>
              <div className="giq-kpi-item">
                <div className="giq-kpi-label">CONSENSUS</div>
                <div className="giq-kpi-value text-[18px]" style={{ color: p.consensusConfigured ? "#3ecf7a" : "#e05252" }}>
                  {p.consensusConfigured ? "LIVE" : "MODEL"}
                </div>
                <div className="giq-kpi-delta">DIR_CHECK</div>
              </div>
            </div>

            <div className="giq-module-header">
              <div className="giq-mh-title">
                <span>//</span> {boardTitle}
              </div>
              <div className="giq-mh-sub">LIVE · {p.team}</div>
            </div>

            <div className="flex flex-wrap items-end gap-3 border-b border-white/[0.06] bg-[#0a0d14] px-4 py-3">
              <div className="space-y-1">
                <Label className="text-[10px] uppercase tracking-wider text-[#7d8fa8]">Team</Label>
                <Select value={p.team} onValueChange={p.setTeam}>
                  <SelectTrigger className="h-8 w-[120px] border-white/10 bg-[#050709] text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {p.displayTeams.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-[10px] uppercase tracking-wider text-[#7d8fa8]">Combine</Label>
                <Input
                  type="number"
                  className="h-8 w-[88px] border-white/10 bg-[#050709] text-xs"
                  value={p.combineSeason}
                  onChange={(e) => p.setCombineSeason(Number(e.target.value))}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[10px] uppercase tracking-wider text-[#7d8fa8]">CFB</Label>
                <Input
                  type="number"
                  className="h-8 w-[88px] border-white/10 bg-[#050709] text-xs"
                  value={p.cfbSeason}
                  onChange={(e) => p.setCfbSeason(Number(e.target.value))}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[10px] uppercase tracking-wider text-[#7d8fa8]">Eval</Label>
                <Input
                  type="number"
                  className="h-8 w-[88px] border-white/10 bg-[#050709] text-xs"
                  value={p.evalSeason}
                  onChange={(e) => p.setEvalSeason(Number(e.target.value))}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[10px] uppercase tracking-wider text-[#7d8fa8]">Pick #</Label>
                <Input
                  type="number"
                  className="h-8 w-[72px] border-white/10 bg-[#050709] text-xs"
                  value={p.pickNumber}
                  onChange={(e) => p.setPickNumber(Number(e.target.value))}
                />
              </div>
              <Button
                className="h-8 bg-[#d4a843] font-mono text-[10px] font-bold uppercase tracking-wider text-[#050709] hover:bg-[#f0c060]"
                disabled={p.intelBusy || p.boardLoading}
                onClick={p.runIntel}
              >
                {p.intelBusy && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
                Run pipeline
              </Button>
              <Button variant="outline" size="sm" className="h-8 border-white/15 bg-transparent" onClick={p.refetchBoard}>
                <RefreshCw className="h-3.5 w-3.5" />
              </Button>
            </div>

            <div className="giq-filter-row">
              {(
                [
                  ["ALL", "ALL"],
                  ["QB", "QB"],
                  ["WR", "WR"],
                  ["RB", "RB"],
                  ["EDGE", "EDGE_DL"],
                  ["OT", "OT_IOL"],
                  ["TE", "TE"],
                  ["CB", "CB"],
                  ["S", "S"],
                  ["LB", "LB"],
                ] as const
              ).map(([label, key]) => (
                <button
                  key={label}
                  type="button"
                  className={`giq-filter-pill ${p.posFilter === key ? "giq-filter-pill-active" : ""}`}
                  onClick={() => p.setPosFilter(key)}
                >
                  {label}
                </button>
              ))}
              <button
                type="button"
                className={`giq-filter-pill ${p.boardViewTab === "r1_projections_tab" ? "giq-filter-pill-active" : ""}`}
                onClick={() => p.setBoardViewTab("r1_projections_tab")}
              >
                R1_ONLY
              </button>
            </div>

            <div className="giq-tabs-row">
              {BOARD_TABS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={`giq-tab ${p.boardViewTab === t.id ? "giq-tab-active" : ""}`}
                  onClick={() => p.setBoardViewTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </>
        )}

        {p.draftModule === "r1_projections" && (
          <div className="space-y-4 p-5">
            <div className="giq-module-header border-t-0">
              <div className="giq-mh-title">
                <span>//</span> R1_PROJECTIONS · LEVERED_INTEL
              </div>
            </div>
            {!topRec && (
              <p className="font-mono text-xs text-[#7d8fa8]">Run pipeline to populate Monte Carlo availability + modes.</p>
            )}
            {topRec && (
              <div className="rounded border border-[#d4a843]/30 bg-[#131928] p-4">
                <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-[#d4a843]">TOP_LEVERED</p>
                <p className="mt-1 text-lg font-semibold text-[#dde4ef]">
                  {topRec.player_name}{" "}
                  <span className="text-[#7d8fa8]">({topRec.pos})</span>
                </p>
                <p className="mt-1 font-mono text-xs text-[#7d8fa8]">
                  Final {Number(topRec.final_draft_score ?? 0).toFixed(1)} · Leverage{" "}
                  {Number(topRec.leverage_score ?? 0).toFixed(1)} · Avail @ pick {p.pickNumber}:{" "}
                  <span className="text-[#d4a843]">
                    {topAvail != null ? `${(Number(topAvail) * 100).toFixed(1)}%` : "—"}
                  </span>
                </p>
              </div>
            )}
            {fourModes && (
              <Tabs defaultValue="best_player_available" className="w-full">
                <TabsList className="flex h-auto w-full flex-wrap gap-1 bg-[#0a0d14] p-1">
                  {(
                    [
                      ["best_player_available", "BPA"],
                      ["best_fit", "FIT"],
                      ["highest_upside", "UPSIDE"],
                      ["safest_pick", "SAFE"],
                    ] as const
                  ).map(([k, lab]) => (
                    <TabsTrigger
                      key={k}
                      value={k}
                      className="font-mono text-[10px] uppercase tracking-wider data-[state=active]:bg-[#050709] data-[state=active]:text-[#d4a843]"
                    >
                      {lab}
                    </TabsTrigger>
                  ))}
                </TabsList>
                {(["best_player_available", "best_fit", "highest_upside", "safest_pick"] as const).map((key) => (
                  <TabsContent key={key} value={key} className="mt-3 rounded border border-white/[0.06] p-3">
                    <ul className="space-y-1 font-mono text-xs text-[#dde4ef]">
                      {(fourModes[key] ?? []).slice(0, 10).map((row) => (
                        <li key={String((row as { player_id?: string }).player_id)} className="flex justify-between gap-2">
                          <span className="truncate">
                            #{(row as { mode_rank?: number }).mode_rank} {String((row as { player_name?: string }).player_name)}
                          </span>
                          <span className="shrink-0 text-[#d4a843]">
                            {Number((row as { prospect_score?: number }).prospect_score ?? 0).toFixed(1)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </TabsContent>
                ))}
              </Tabs>
            )}
          </div>
        )}

        {(p.draftModule === "big_board" || p.draftModule === "prospect_db") && (
          <div className="giq-board-wrap">
            {p.boardLoading && (
              <div className="flex items-center gap-2 p-6 font-mono text-sm text-[#7d8fa8]">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading board…
              </div>
            )}
            {p.boardError && (
              <p className="p-6 font-mono text-sm text-red-400">{p.boardError.message || "Board error"}</p>
            )}
            {p.board && !p.boardLoading && (
              <table className="giq-board-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th className={p.sortHeaderClass("player_name")} onClick={() => p.toggleTableSort("player_name")}>
                      PLAYER
                    </th>
                    <th>POS</th>
                    <th>SCHOOL</th>
                    <th className={p.sortHeaderClass("final_draft_score")} onClick={() => p.toggleTableSort("final_draft_score")}>
                      FINAL
                    </th>
                    <th className={p.sortHeaderClass("prospect_score")} onClick={() => p.toggleTableSort("prospect_score")}>
                      PROSPECT
                    </th>
                    <th className={p.sortHeaderClass("model_rank")} onClick={() => p.toggleTableSort("model_rank")}>
                      MDL#
                    </th>
                    <th className={p.sortHeaderClass("consensus_rank")} onClick={() => p.toggleTableSort("consensus_rank")}>
                      CONS
                    </th>
                    <th className={p.sortHeaderClass("reach_risk")} onClick={() => p.toggleTableSort("reach_risk")}>
                      REACH
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {p.displayRows.map((row, idx) => {
                    const rank = row.model_rank ?? idx + 1;
                    const active = p.selectedId === row.player_id;
                    return (
                      <tr
                        key={row.player_id}
                        onClick={() => p.setSelectedId(row.player_id)}
                        style={{ background: active ? "rgba(212,168,67,0.08)" : undefined }}
                      >
                        <td>
                          <div className={`giq-rank-num ${rank <= 3 ? "border-[rgba(212,168,67,0.35)] text-[#d4a843]" : ""}`}>
                            {rank}
                          </div>
                        </td>
                        <td>
                          <div className="text-[13px] font-semibold text-[#dde4ef]">{row.player_name}</div>
                          <div className="text-[9px] uppercase tracking-wider text-[#3d4f66]">
                            {row.pos_bucket} · score breakdown
                          </div>
                        </td>
                        <td>
                          <span className={prospectPosPill(row.pos)}>{row.pos}</span>
                        </td>
                        <td className="text-[10px] text-[#7d8fa8]">{row.school}</td>
                        <td className="text-[#f0c060]">{row.final_draft_score.toFixed(1)}</td>
                        <td>{row.prospect_score.toFixed(1)}</td>
                        <td>{row.model_rank ?? "—"}</td>
                        <td>{row.consensus_rank != null ? Number(row.consensus_rank).toFixed(1) : "—"}</td>
                        <td>{row.reach_risk != null ? Number(row.reach_risk).toFixed(2) : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {p.draftModule === "model_intel" && (
          <div className="space-y-4 p-5">
            <div className="giq-module-header border-t-0">
              <div className="giq-mh-title">
                <span>//</span> MODEL_INTEL · ANALYST_CONSOLE
              </div>
            </div>
            {p.analystPending && (
              <div className="flex items-center gap-2 font-mono text-sm text-[#7d8fa8]">
                <Loader2 className="h-4 w-4 animate-spin" /> Generating…
              </div>
            )}
            {p.analystData && (
              <div className="space-y-3 rounded border border-white/[0.06] bg-[#131928] p-4 font-mono text-xs text-[#dde4ef]">
                <div>
                  <p className="text-[9px] uppercase tracking-wider text-[#d4a843]">Best pick</p>
                  <p className="mt-1">{p.analystData.best_pick_explanation}</p>
                </div>
                <div>
                  <p className="text-[9px] uppercase tracking-wider text-[#d4a843]">Risk</p>
                  <p className="mt-1">{p.analystData.risk_analysis}</p>
                </div>
              </div>
            )}
            <div className="rounded border border-white/[0.06] bg-[#131928] p-4">
              <p className="mb-2 font-mono text-[9px] uppercase tracking-wider text-[#7d8fa8]">Ask the analyst</p>
              <Textarea
                value={p.chatQ}
                onChange={(e) => p.setChatQ(e.target.value)}
                className="min-h-[72px] border-white/10 bg-[#050709] font-mono text-xs"
              />
              <Button
                className="mt-2 w-full bg-[#dde4ef] font-mono text-xs font-semibold text-[#050709] hover:bg-white"
                onClick={p.sendChat}
              >
                <Send className="mr-2 h-3.5 w-3.5" /> Send
              </Button>
              {p.chatOut && (
                <div className="mt-3 whitespace-pre-wrap rounded border border-white/[0.06] bg-[#050709] p-3 font-mono text-xs text-[#dde4ef]">
                  {p.chatOut}
                </div>
              )}
            </div>
          </div>
        )}

        {p.draftModule === "team_needs" && (
          <div className="p-5">
            <div className="giq-module-header border-t-0">
              <div className="giq-mh-title">
                <span>//</span> {p.team} — POSITIONAL_NEED_SCORES
              </div>
              <div className="giq-mh-sub">SIGNAL_LAYERS · nflverse</div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
              {needEntries.length === 0 && (
                <p className="font-mono text-xs text-[#7d8fa8]">No need_scores on payload — load board.</p>
              )}
              {needEntries.map(([pos, score]) => (
                <div key={pos} className="rounded border border-white/[0.06] bg-[#131928] p-3">
                  <div className="font-mono text-[10px] text-[#7d8fa8]">{pos}</div>
                  <div className="text-2xl font-bold text-[#d4a843]">{score.toFixed(0)}</div>
                  <div className="giq-signal-track mt-2">
                    <div className="giq-signal-fill-gold" style={{ width: `${Math.min(100, score)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {p.draftModule === "compare" && p.board && (
          <div className="space-y-4 p-5">
            <div className="giq-module-header border-t-0">
              <div className="giq-mh-title">
                <span>//</span> PROSPECT_COMPARE
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label className="text-[10px] uppercase text-[#7d8fa8]">Player A</Label>
                <Select value={p.selectedId ?? ""} onValueChange={(v) => p.setSelectedId(v || null)}>
                  <SelectTrigger className="border-white/10 bg-[#050709] font-mono text-xs">
                    <SelectValue placeholder="Select A" />
                  </SelectTrigger>
                  <SelectContent>
                    {p.board.prospects.map((r) => (
                      <SelectItem key={r.player_id} value={r.player_id}>
                        {r.player_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-[10px] uppercase text-[#7d8fa8]">Player B</Label>
                <Select value={p.compareIdB ?? ""} onValueChange={(v) => p.setCompareIdB(v || null)}>
                  <SelectTrigger className="border-white/10 bg-[#050709] font-mono text-xs">
                    <SelectValue placeholder="Select B" />
                  </SelectTrigger>
                  <SelectContent>
                    {p.board.prospects.map((r) => (
                      <SelectItem key={r.player_id} value={r.player_id}>
                        {r.player_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            {p.selected && compareB && (
              <div className="grid gap-4 border-t border-white/[0.06] pt-4 md:grid-cols-[1fr_auto_1fr] md:items-stretch">
                <div className="rounded border border-white/[0.06] bg-[#131928] p-4">
                  <div className="text-2xl font-bold tracking-tight text-[#dde4ef]">{p.selected.player_name}</div>
                  <div className="mt-1 flex items-center gap-2">
                    <span className={prospectPosPill(p.selected.pos)}>{p.selected.pos}</span>
                    <span className="font-mono text-[10px] text-[#3d4f66]">{p.selected.school}</span>
                  </div>
                  <dl className="mt-4 space-y-2 font-mono text-xs">
                    {[
                      ["FINAL", p.selected.final_draft_score.toFixed(1)],
                      ["PROSPECT", p.selected.prospect_score.toFixed(1)],
                      ["NEED", p.selected.team_need_score.toFixed(1)],
                      ["SCHEME", p.selected.scheme_fit_score.toFixed(1)],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between border-b border-white/[0.04] py-1 text-[#7d8fa8]">
                        <dt>{k}</dt>
                        <dd className="text-[#d4a843]">{v}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <div className="flex items-center justify-center font-mono text-sm font-bold text-[#d4a843]">VS</div>
                <div className="rounded border border-white/[0.06] bg-[#131928] p-4">
                  <div className="text-2xl font-bold tracking-tight text-[#dde4ef]">{compareB.player_name}</div>
                  <div className="mt-1 flex items-center gap-2">
                    <span className={prospectPosPill(compareB.pos)}>{compareB.pos}</span>
                    <span className="font-mono text-[10px] text-[#3d4f66]">{compareB.school}</span>
                  </div>
                  <dl className="mt-4 space-y-2 font-mono text-xs">
                    {[
                      ["FINAL", compareB.final_draft_score.toFixed(1)],
                      ["PROSPECT", compareB.prospect_score.toFixed(1)],
                      ["NEED", compareB.team_need_score.toFixed(1)],
                      ["SCHEME", compareB.scheme_fit_score.toFixed(1)],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between border-b border-white/[0.04] py-1 text-[#7d8fa8]">
                        <dt>{k}</dt>
                        <dd className="text-[#dde4ef]">{v}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>
            )}
          </div>
        )}

        {(p.draftModule === "scheme_fit" || p.draftModule === "combine_lab" || p.draftModule === "trend_signals") && (
          <div className="p-8">
            <div className="giq-module-header border-t-0">
              <div className="giq-mh-title">
                <span>//</span>{" "}
                {p.draftModule === "scheme_fit" ? "SCHEME_FIT" : p.draftModule === "combine_lab" ? "COMBINE_LAB" : "TREND_SIGNALS"}
              </div>
            </div>
            <p className="mt-4 max-w-lg font-mono text-xs leading-relaxed text-[#7d8fa8]">
              Wire-up pending: this rail mirrors the static platform module. Use BIG_BOARD + selected prospect for scheme
              and combine context today; full trend layer will attach to team_context signals.
            </p>
          </div>
        )}

        {(p.draftModule === "big_board" || p.draftModule === "prospect_db") && (
          <div className="border-t border-white/[0.06] p-4">
            <div className="giq-module-header !border-t-0 !px-0 !pt-0">
              <div className="giq-mh-title">
                <span>//</span> TRADE_DOWN_SCAN
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-end gap-3">
              <div className="space-y-1">
                <Label className="text-[10px] uppercase text-[#7d8fa8]">Max target pick</Label>
                <Input
                  type="number"
                  className="h-8 w-[120px] border-white/10 bg-[#050709] font-mono text-xs"
                  value={p.maxTradeTarget}
                  min={p.pickNumber + 1}
                  onChange={(e) => p.setMaxTradeTarget(Number(e.target.value))}
                />
              </div>
              <Button
                className="h-8 bg-[#dde4ef] font-mono text-xs font-semibold text-[#050709] hover:bg-white"
                disabled={p.tradePending || p.boardLoading || p.maxTradeTarget <= p.pickNumber}
                onClick={p.runTrade}
              >
                {p.tradePending && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
                Run trade scan
              </Button>
            </div>
            {p.tradeError && <p className="mt-2 font-mono text-xs text-red-400">{p.tradeError.message}</p>}
            {p.tradeScan && p.tradeScan.length > 0 && (
              <Table className="mt-4 font-mono text-xs">
                <TableHeader>
                  <TableRow className="border-white/[0.06] hover:bg-transparent">
                    <TableHead className="text-[#7d8fa8]">Target</TableHead>
                    <TableHead className="text-right text-[#7d8fa8]">EV Δ</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {p.tradeScan.map((r) => (
                    <TableRow key={r.target_pick} className="border-white/[0.06]">
                      <TableCell className="text-[#dde4ef]">{r.target_pick}</TableCell>
                      <TableCell className="text-right text-[#d4a843]">{Number(r.ev_delta).toFixed(3)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        )}
      </div>

      {/* RIGHT */}
      <aside className="giq-draft-right max-h-[calc(100vh-3.5rem)] overflow-y-auto lg:max-h-none">
        <div>
          <div className="giq-rp-header">SELECTED_PROSPECT</div>
          <div className="px-4 py-3">
            {!p.selected && <p className="font-mono text-xs text-[#7d8fa8]">Select a row on the big board.</p>}
            {p.selected && (
              <>
                <div className="text-[22px] font-bold leading-none tracking-tight text-[#dde4ef]">{p.selected.player_name}</div>
                <div className="mt-1 font-mono text-[10px] text-[#7d8fa8]">
                  {p.selected.pos} · {p.selected.school}
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <div className="text-3xl font-bold text-[#d4a843]">{p.selected.final_draft_score.toFixed(1)}</div>
                  <div className="font-mono text-[9px] uppercase tracking-wider text-[#3d4f66]">FINAL_SCORE</div>
                </div>
              </>
            )}
          </div>
        </div>
        <div>
          <div className="giq-rp-header">PROSPECT_RADAR</div>
          <div className="px-2 py-2">
            {p.selected ? (
              <div className="h-[200px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarDataFor(p.selected)} cx="50%" cy="50%" outerRadius="72%">
                    <PolarGrid stroke="rgba(255,255,255,0.08)" />
                    <PolarAngleAxis dataKey="metric" tick={{ fill: "#7d8fa8", fontSize: 9 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#3d4f66", fontSize: 8 }} />
                    <Radar
                      name={p.selected.player_name}
                      dataKey="value"
                      stroke="#d4a843"
                      fill="#d4a843"
                      fillOpacity={0.2}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="px-2 pb-4 font-mono text-xs text-[#7d8fa8]">No selection</p>
            )}
          </div>
        </div>
        <div>
          <div className="giq-rp-header">SIGNAL_BREAKDOWN</div>
          <div className="space-y-3 px-4 py-3">
            {p.selected ? (
              <>
                {(
                  [
                    ["Athleticism", p.selected.radar.athleticism, "gold"],
                    ["Production", p.selected.radar.production, "cyan"],
                    ["Efficiency", p.selected.radar.efficiency, "cyan"],
                    ["Scheme fit", p.selected.radar.scheme_fit, "green"],
                    ["Team need", p.selected.radar.team_need, "gold"],
                  ] as const
                ).map(([label, val, tone]) => (
                  <div key={label}>
                    <div className="flex justify-between font-mono text-[9px] uppercase tracking-wider text-[#7d8fa8]">
                      <span>{label}</span>
                      <span className="text-[#f0c060]">{val.toFixed(1)}</span>
                    </div>
                    <div className="giq-signal-track mt-1">
                      <div
                        className={tone === "gold" ? "giq-signal-fill-gold" : tone === "green" ? "giq-signal-fill-green" : "giq-signal-fill-cyan"}
                        style={{ width: `${val}%` }}
                      />
                    </div>
                  </div>
                ))}
              </>
            ) : (
              <p className="font-mono text-xs text-[#7d8fa8]">—</p>
            )}
          </div>
        </div>
        <div>
          <div className="giq-rp-header">MODEL_STATUS</div>
          <div className="px-4 py-2 font-mono text-[10px]">
            <div className="flex justify-between border-b border-white/[0.04] py-2 text-[#7d8fa8]">
              <span>CONSENSUS</span>
              <span className={p.consensusConfigured ? "text-[#3ecf7a]" : "text-[#e05252]"}>
                {p.consensusConfigured ? "CONFIGURED" : "MODEL_ONLY"}
              </span>
            </div>
            <div className="flex justify-between py-2 text-[#7d8fa8]">
              <span>BOARD_ROWS</span>
              <span className="text-[#dde4ef]">{p.board?.prospects?.length ?? 0}</span>
            </div>
          </div>
        </div>
      </aside>
    </main>
  );
}
