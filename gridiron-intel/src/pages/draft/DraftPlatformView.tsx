import type { ReactNode } from "react";
import { useMemo } from "react";
import { Loader2, RefreshCw, Search, Send } from "lucide-react";
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
import type { RmuConfidence, RmuData, RmuPosition, RmuProspect } from "@/lib/rmu.ts";
import { confidenceColor, matchRmu } from "@/lib/rmu.ts";
import type { EngineData, R1BoardRow } from "@/lib/engine.ts";
import { pct, topFeatures } from "@/lib/engine.ts";
import {
  buildMockDraftFullPoolRows,
  buildMockDraftSkillOnlyRows,
  buildRmuMockLandings,
  findR1Overlay,
  MOCK_DRAFT_3R_PICKS,
} from "@/lib/mockDraftComposite.ts";
import DraftSimulator from "../DraftSimulator.tsx";
import type { AnalyticsSubTab, BoardViewTab, DraftRoomTab, PosFilter } from "./draftBoardUtils.ts";
import {
  BIG_BOARD_TOP_N,
  DRAFT_CFB_SEASON,
  DRAFT_COMBINE_SEASON,
  DRAFT_EVAL_SEASON,
  prospectPosPill,
} from "./draftBoardUtils.ts";
import type { RmuHighlightFilter } from "./draftBoardUtils.ts";
import type { TableSortKey } from "./draftBoardUtils.ts";

/** Training window for the RMU / SAC first-round model (historical draft classes). */
const RMU_TRAINING_YEARS = 14;

function r1ChipClass(conf: RmuConfidence | null | undefined): string {
  if (!conf) return "giq-r1-chip giq-r1-na";
  switch (conf) {
    case "LOCK":
      return "giq-r1-chip giq-r1-lock";
    case "HIGH":
      return "giq-r1-chip giq-r1-high";
    case "MEDIUM":
      return "giq-r1-chip giq-r1-med";
    case "LOW":
      return "giq-r1-chip giq-r1-low";
    default:
      return "giq-r1-chip giq-r1-na";
  }
}

function R1ProbCell({ rmu }: { rmu: RmuProspect | null }) {
  if (!rmu) {
    return <span className="giq-r1-chip giq-r1-na">—</span>;
  }
  const pct = Math.round(rmu.r1_probability * 100);
  return (
    <span className={r1ChipClass(rmu.confidence)} title={`${rmu.confidence} · ${pct}% P(R1)`}>
      {pct}%
    </span>
  );
}

function Headshot({
  rmu,
  name,
  size = "sm",
}: {
  rmu: RmuProspect | null;
  name: string;
  size?: "sm" | "lg";
}) {
  const cls = size === "lg" ? "giq-headshot-lg" : "giq-headshot";
  const dim = size === "lg" ? 96 : 48;
  if (rmu?.headshot_url) {
    return (
      <img
        src={rmu.headshot_url}
        alt={name}
        className={cls}
        loading="lazy"
        onError={(e) => {
          (e.currentTarget as HTMLImageElement).style.display = "none";
          const holder = e.currentTarget.nextElementSibling as HTMLElement | null;
          if (holder) holder.style.display = "inline-flex";
        }}
      />
    );
  }
  const initials = name
    .split(/\s+/)
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return (
    <span
      className={`giq-headshot-placeholder ${cls}`}
      style={{ width: dim, height: dim, display: "inline-flex" }}
    >
      {initials || "?"}
    </span>
  );
}

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

function RoomTabBtn({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`giq-room-tab ${active ? "giq-room-tab-active" : ""}`}
    >
      {label}
    </button>
  );
}

export interface DraftPlatformViewProps {
  roomTab: DraftRoomTab;
  setRoomTab: (t: DraftRoomTab) => void;
  analyticsSub: AnalyticsSubTab;
  setAnalyticsSub: (s: AnalyticsSubTab) => void;
  posFilter: PosFilter;
  setPosFilter: (f: PosFilter) => void;
  rmuHighlightFilter: RmuHighlightFilter;
  setRmuHighlightFilter: (f: RmuHighlightFilter) => void;
  boardViewTab: BoardViewTab;
  setBoardViewTab: (t: BoardViewTab) => void;
  board: ApiDraftBoard | undefined;
  boardLoading: boolean;
  boardError: Error | null;
  displayRows: ApiDraftProspect[];
  prospectDbRows: ApiDraftProspect[];
  prospectSearch: string;
  setProspectSearch: (s: string) => void;
  selected: ApiDraftProspect | null;
  selectedId: string | null;
  setSelectedId: (id: string | null) => void;
  toggleTableSort: (k: TableSortKey) => void;
  sortHeaderClass: (k: TableSortKey) => string;
  team: string;
  setTeam: (t: string) => void;
  displayTeams: string[];
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
  tradeScan: { target_pick: number; ev_delta: number }[] | undefined;
  runTrade: () => void;
  compareIdB: string | null;
  setCompareIdB: (id: string | null) => void;
  chatQ: string;
  setChatQ: (s: string) => void;
  chatOut: string;
  sendChat: () => void;
  consensusConfigured: boolean | undefined;
  refetchBoard: () => void;
  /** RMU / SAC hackathon first-round model outputs (loaded from /rmu/*.json). */
  rmuData: RmuData | undefined;
  rmuLoading: boolean;
  rmuError: Error | null;
  /** GridironIQ game-prediction engine outputs (loaded from /engine/*). */
  engineData: EngineData | undefined;
  engineLoading: boolean;
  engineError: Error | null;
}

const BOARD_TABS: { id: BoardViewTab; label: string }[] = [
  { id: "consensus_board", label: "CONSENSUS_BOARD" },
  { id: "model_board", label: "MODEL_BOARD" },
  { id: "r1_projections_tab", label: "R1_PROJECTIONS" },
  { id: "rmu_predictions", label: "RMU_PREDICTIONS" },
  { id: "by_team_fit", label: "BY_TEAM_FIT" },
];

const ANALYTICS_PRIMARY: { id: AnalyticsSubTab; label: string }[] = [
  { id: "model_intel", label: "MODEL_INTEL" },
  { id: "engine_intel", label: "ENGINE_INTEL" },
  { id: "backtest_lab", label: "BACKTEST_LAB" },
  { id: "team_needs", label: "TEAM_NEEDS" },
  { id: "scheme_fit", label: "SCHEME_FIT" },
  { id: "combine_lab", label: "COMBINE_LAB" },
  { id: "trend_signals", label: "TREND_SIGNALS" },
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

  const tableRows = p.roomTab === "prospect_db" ? p.prospectDbRows : p.displayRows;
  const topScore = tableRows[0]?.final_draft_score ?? p.board?.prospects?.[0]?.final_draft_score;

  const selectedRmu = p.selected ? matchRmu(p.rmuData, p.selected.player_name) : null;
  const modelAccuracyPct = p.rmuData
    ? Math.round(p.rmuData.ensembleAucMean * 100)
    : null;

  const canonicalRoom = p.roomTab === "board" ? "big_board" : p.roomTab;
  /** Views that render the prospect table + filter chips + board sub-tabs. */
  const showBoardLayers =
    canonicalRoom === "big_board" ||
    canonicalRoom === "prospect_db" ||
    canonicalRoom === "team_view";
  const layoutMainClass = p.selected ? "giq-draft-layout giq-draft-layout-with-side" : "giq-draft-layout";

  return (
    <main className={layoutMainClass}>
      {/* LEFT */}
      <aside className="giq-draft-left max-h-[calc(100vh-3.5rem)] overflow-y-auto lg:max-h-none">
        <div className="giq-panel-section">
          <div className="giq-panel-title">BOARD_MODULES</div>
          <NavBtn
            icon="▦"
            label="BIG_BOARD"
            badge={p.rmuData ? String(p.rmuData.r1Projected) : undefined}
            active={canonicalRoom === "big_board"}
            onClick={() => p.setRoomTab("big_board")}
          />
          <NavBtn
            icon="▣"
            label="MOCK_DRAFT_3R"
            badge={String(MOCK_DRAFT_3R_PICKS)}
            active={canonicalRoom === "mock_draft"}
            onClick={() => p.setRoomTab("mock_draft")}
          />
          <NavBtn
            icon="▶"
            label="SIMULATOR"
            active={canonicalRoom === "simulator"}
            onClick={() => p.setRoomTab("simulator")}
          />
          <NavBtn
            icon="◎"
            label="TEAM_VIEW"
            badge={canonicalRoom === "team_view" ? p.team : undefined}
            active={canonicalRoom === "team_view"}
            onClick={() => p.setRoomTab("team_view")}
          />
          <NavBtn
            icon="≡"
            label="PROSPECT_DB"
            active={canonicalRoom === "prospect_db"}
            onClick={() => p.setRoomTab("prospect_db")}
          />
          <NavBtn
            icon="⇄"
            label="COMPARE"
            active={canonicalRoom === "compare"}
            onClick={() => p.setRoomTab("compare")}
          />
          <p className="px-4 pb-3 pt-1 font-mono text-[9px] leading-relaxed text-[#3d4f66]">
            2026 cycle · combine {DRAFT_COMBINE_SEASON} · CFB {DRAFT_CFB_SEASON} · eval {DRAFT_EVAL_SEASON}
          </p>
        </div>

        {canonicalRoom === "team_view" && (
          <div className="giq-panel-section">
            <div className="giq-panel-title">TEAM_CONTEXT</div>
            <div className="space-y-2 px-4 py-3">
              <Label className="text-[10px] uppercase tracking-wider text-[#7d8fa8]">Team</Label>
              <Select value={p.team} onValueChange={p.setTeam}>
                <SelectTrigger className="h-8 w-full border-white/10 bg-[#050709] text-xs">
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
              <div className="space-y-1 pt-1">
                <Label className="text-[10px] uppercase tracking-wider text-[#7d8fa8]">Pick #</Label>
                <Input
                  type="number"
                  className="h-8 border-white/10 bg-[#050709] text-xs"
                  value={p.pickNumber}
                  min={1}
                  max={259}
                  onChange={(e) => p.setPickNumber(Number(e.target.value))}
                />
              </div>
            </div>
          </div>
        )}

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

        <div className="giq-panel-section">
          <div className="giq-panel-title">GAME_ENGINE</div>
          <div className="flex flex-wrap items-center gap-2 px-4 py-2">
            <span className="text-[#29b8e0]">◆</span>
            <span className="font-mono text-[10px] font-bold tracking-wider text-[#dde4ef]">PREDICTION_STACK</span>
            <span className="giq-nav-badge">LIVE</span>
          </div>
          <NavBtn
            icon="◇"
            label="ENGINE_INTEL"
            active={p.roomTab === "analytics" && p.analyticsSub === "engine_intel"}
            onClick={() => {
              p.setRoomTab("analytics");
              p.setAnalyticsSub("engine_intel");
            }}
          />
          <NavBtn
            icon="◈"
            label="BACKTEST_LAB"
            active={p.roomTab === "analytics" && p.analyticsSub === "backtest_lab"}
            onClick={() => {
              p.setRoomTab("analytics");
              p.setAnalyticsSub("backtest_lab");
            }}
          />
        </div>

        <div className="giq-panel-section">
          <div className="giq-panel-title">RMU_SAC_MODULE</div>
          <div className="flex flex-wrap items-center gap-2 px-4 py-2">
            <span className="text-[#d4a843]">★</span>
            <span className="font-mono text-[10px] font-bold tracking-wider text-[#dde4ef]">HACKATHON</span>
            <span className="giq-nav-badge bg-[#29b8e0] text-[#050709]">BETA</span>
          </div>
          <NavBtn
            icon="⊕"
            label="TRAINING_DATA"
            active={p.roomTab === "analytics" && p.analyticsSub === "rmu_training"}
            onClick={() => {
              p.setRoomTab("analytics");
              p.setAnalyticsSub("rmu_training");
            }}
          />
          <NavBtn
            icon="⊗"
            label="MODEL_RESULTS"
            active={p.roomTab === "analytics" && p.analyticsSub === "rmu_results"}
            onClick={() => {
              p.setRoomTab("analytics");
              p.setAnalyticsSub("rmu_results");
            }}
          />
          <NavBtn
            icon="⊘"
            label="PREDICTIONS"
            active={p.roomTab === "analytics" && p.analyticsSub === "rmu_predictions"}
            onClick={() => {
              p.setRoomTab("analytics");
              p.setAnalyticsSub("rmu_predictions");
            }}
          />
        </div>
      </aside>

      {/* CENTER */}
      <div className="giq-draft-center min-w-0">
        <div className="giq-room-tab-strip sticky top-0 z-20 border-b border-white/[0.06] bg-[#0a0d14] px-2 py-2">
          <div className="flex flex-wrap items-center gap-1">
            <RoomTabBtn
              label="BIG_BOARD"
              active={canonicalRoom === "big_board"}
              onClick={() => p.setRoomTab("big_board")}
            />
            <RoomTabBtn
              label="MOCK_DRAFT_3R"
              active={canonicalRoom === "mock_draft"}
              onClick={() => p.setRoomTab("mock_draft")}
            />
            <RoomTabBtn
              label="SIMULATOR"
              active={canonicalRoom === "simulator"}
              onClick={() => p.setRoomTab("simulator")}
            />
            <RoomTabBtn
              label={canonicalRoom === "team_view" ? `TEAM · ${p.team}` : "TEAM_VIEW"}
              active={canonicalRoom === "team_view"}
              onClick={() => p.setRoomTab("team_view")}
            />
            <span className="mx-1 h-5 w-px bg-white/10" aria-hidden />
            <RoomTabBtn
              label="PROSPECT_DB"
              active={canonicalRoom === "prospect_db"}
              onClick={() => p.setRoomTab("prospect_db")}
            />
            <RoomTabBtn
              label="COMPARE"
              active={canonicalRoom === "compare"}
              onClick={() => p.setRoomTab("compare")}
            />
            <RoomTabBtn
              label="ANALYTICS"
              active={canonicalRoom === "analytics"}
              onClick={() => p.setRoomTab("analytics")}
            />
            {canonicalRoom === "analytics" && (
              <button
                type="button"
                onClick={() => p.setRoomTab("big_board")}
                className="ml-auto rounded border border-white/10 bg-[#050709] px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-[#7d8fa8] hover:text-[#dde4ef]"
                title="Back to Big Board"
              >
                ← BIG_BOARD
              </button>
            )}
          </div>
        </div>

        {canonicalRoom === "simulator" && (
          <div className="border-b border-white/[0.06] p-3">
            <DraftSimulator />
          </div>
        )}

        {canonicalRoom === "mock_draft" && (
          <MockDraftPane
            rmuData={p.rmuData}
            engineData={p.engineData}
            board={p.board}
            boardLoading={p.boardLoading}
            boardError={p.boardError}
          />
        )}

        {showBoardLayers && (
          <>
            <div className="giq-kpi-bar">
              <div className="giq-kpi-item">
                <div className="giq-kpi-label">R1_PROJECTED</div>
                <div className="giq-kpi-value text-[22px] text-[#d4a843]">
                  {p.rmuData ? p.rmuData.r1Projected : "—"}
                </div>
                <div className="giq-kpi-delta">QB · WR · RB · SKILL</div>
              </div>
              <div className="giq-kpi-item">
                <div className="giq-kpi-label">MODEL_ACCURACY</div>
                <div className="giq-kpi-value text-[22px] text-[#d4a843]">
                  {modelAccuracyPct != null ? `${modelAccuracyPct}%` : "—"}
                </div>
                <div className="giq-kpi-delta">HOLDOUT_SET_AUC</div>
              </div>
              <div className="giq-kpi-item">
                <div className="giq-kpi-label">PROSPECTS_SCORED</div>
                <div className="giq-kpi-value text-[22px] text-[#d4a843]">
                  {p.rmuData ? p.rmuData.manifest.length : (p.board?.prospects?.length ?? "—")}
                </div>
                <div className="giq-kpi-delta">QB+WR+RB · RMU_SAC</div>
              </div>
              <div className="giq-kpi-item">
                <div className="giq-kpi-label">TOP_SCORE</div>
                <div className="giq-kpi-value text-[22px] text-[#d4a843]">
                  {p.rmuData ? p.rmuData.topScore.toFixed(1) : topScore != null ? topScore.toFixed(1) : "—"}
                </div>
                <div className="giq-kpi-delta">P(R1) · MENDOZA</div>
              </div>
              <div className="giq-kpi-item">
                <div className="giq-kpi-label">ENGINE_ACC</div>
                <div className="giq-kpi-value text-[22px] text-[#d4a843]">
                  {p.engineData ? pct(p.engineData.overall.accuracy, 1) : "—"}
                </div>
                <div className="giq-kpi-delta">
                  {p.engineData
                    ? `${p.engineData.overall.correct}/${p.engineData.overall.total} games · 2020-2025`
                    : `${RMU_TRAINING_YEARS} train years`}
                </div>
              </div>
            </div>

            <div className="giq-module-header">
              <div className="giq-mh-title">
                <span>//</span>{" "}
                {canonicalRoom === "prospect_db"
                  ? "PROSPECT_DB — LIVE nflverse BOARD (2026)"
                  : canonicalRoom === "team_view"
                    ? `TEAM_VIEW · ${p.team} · PICK ${p.pickNumber}`
                    : `2026 BIG_BOARD — TOP ${BIG_BOARD_TOP_N} PROSPECTS (MODEL)`}
              </div>
              <div className="giq-mh-sub">
                {canonicalRoom === "team_view"
                  ? `TEAM · ${p.team}`
                  : canonicalRoom === "big_board"
                    ? `GLOBAL · prospect_score · max ${BIG_BOARD_TOP_N} rows · RMU filter: ${p.rmuHighlightFilter}`
                    : "LIVE · GLOBAL"}
              </div>
            </div>

            {canonicalRoom === "team_view" && p.engineData?.nflDraft && (
              <TeamNeedsStrip
                team={p.team}
                nflDraft={p.engineData.nflDraft}
              />
            )}

            <div className="flex flex-wrap items-center gap-2 border-b border-white/[0.06] bg-[#0a0d14] px-4 py-3">
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

            <div className="flex flex-wrap items-center gap-2 border-b border-white/[0.06] px-4 py-2">
              <button
                type="button"
                className={`giq-filter-pill ${p.boardViewTab === "r1_projections_tab" ? "giq-filter-pill-active" : ""}`}
                onClick={() => p.setBoardViewTab("r1_projections_tab")}
              >
                R1_ONLY
              </button>
              <button
                type="button"
                className={`giq-filter-pill ${p.rmuHighlightFilter === "RMU_ONLY" ? "giq-filter-pill-active" : ""}`}
                onClick={() =>
                  p.setRmuHighlightFilter(p.rmuHighlightFilter === "RMU_ONLY" ? "ALL" : "RMU_ONLY")
                }
                title="Show only prospects on the RMU/SAC first-round board (QB · WR · RB)"
              >
                RMU_BOARD
              </button>
            </div>

            {p.roomTab === "prospect_db" && (
              <div className="flex items-center gap-2 border-b border-white/[0.06] bg-[#0f131e] px-4 py-3">
                <Search className="h-4 w-4 shrink-0 text-[#7d8fa8]" />
                <Input
                  placeholder="Search name, school, position…"
                  value={p.prospectSearch}
                  onChange={(e) => p.setProspectSearch(e.target.value)}
                  className="h-9 border-white/10 bg-[#050709] font-mono text-xs"
                />
              </div>
            )}
          </>
        )}

        {showBoardLayers && (
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
                    <th>R1_PROB</th>
                    <th>TREND</th>
                  </tr>
                </thead>
                <tbody>
                  {tableRows.map((row, idx) => {
                    const rank = row.model_rank ?? idx + 1;
                    const active = p.selectedId === row.player_id;
                    const rmu = matchRmu(p.rmuData, row.player_name);
                    const rmuBoardHit = Boolean(rmu);
                    const reach = row.reach_risk;
                    const trend =
                      reach == null
                        ? "—"
                        : reach <= -3
                          ? "LOCK"
                          : reach < 0
                            ? "HIGH"
                            : reach > 3
                              ? "LOW"
                              : "MED";
                    const trendColor =
                      trend === "LOCK"
                        ? "#d4a843"
                        : trend === "HIGH"
                          ? "#3ecf7a"
                          : trend === "MED"
                            ? "#29b8e0"
                            : trend === "LOW"
                              ? "#7d8fa8"
                              : "#3d4f66";
                    return (
                      <tr
                        key={row.player_id}
                        className={rmuBoardHit ? "giq-board-row-rmu" : undefined}
                        onClick={() => p.setSelectedId(active ? null : row.player_id)}
                        style={{ background: active ? "rgba(212,168,67,0.08)" : undefined }}
                      >
                        <td>
                          <div className={`giq-rank-num ${rank <= 3 ? "border-[rgba(212,168,67,0.35)] text-[#d4a843]" : ""}`}>
                            {rank}
                          </div>
                        </td>
                        <td>
                          <div className="flex items-center gap-2">
                            <Headshot rmu={rmu} name={row.player_name} size="sm" />
                            <div>
                              <div className="text-[13px] font-semibold text-[#dde4ef]">{row.player_name}</div>
                              <div className="text-[9px] uppercase tracking-wider text-[#3d4f66]">
                                {row.pos_bucket} · score breakdown
                              </div>
                            </div>
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
                        <td>
                          <R1ProbCell rmu={rmu} />
                        </td>
                        <td className="font-mono text-[10px]" style={{ color: trendColor }}>
                          {trend}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {canonicalRoom === "team_view" && (
          <div className="space-y-4 border-t border-white/[0.06] p-5">
            <div className="giq-module-header border-t-0">
              <div className="giq-mh-title">
                <span>//</span> {p.team} · R1_PROJECTIONS · LEVERED_INTEL
              </div>
            </div>
            {!topRec && (
              <p className="font-mono text-xs text-[#7d8fa8]">
                Run pipeline to populate Monte Carlo availability + modes.
              </p>
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
                            #{(row as { mode_rank?: number }).mode_rank}{" "}
                            {String((row as { player_name?: string }).player_name)}
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

        {canonicalRoom === "team_view" && (
          <div className="border-t border-white/[0.06] p-4">
            <div className="giq-module-header !border-t-0 !px-0 !pt-0">
              <div className="giq-mh-title">
                <span>//</span> {p.team} · TRADE_DOWN_SCAN
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

        {p.roomTab === "analytics" && (
          <div className="min-h-[420px] border-t border-white/[0.06] p-4">
            <div className="giq-analytics-subrow mb-2 flex flex-wrap gap-1">
              {ANALYTICS_PRIMARY.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={`giq-tab ${p.analyticsSub === t.id ? "giq-tab-active" : ""}`}
                  onClick={() => p.setAnalyticsSub(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="mb-4 flex flex-wrap items-center gap-2 border-b border-white/[0.06] pb-4">
              <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-[#3d4f66]">RMU_SAC</span>
              {(
                [
                  ["rmu_training", "⊕", "TRAINING_DATA"],
                  ["rmu_results", "⊗", "MODEL_RESULTS"],
                  ["rmu_predictions", "⊘", "PREDICTIONS"],
                ] as const
              ).map(([id, sym, lab]) => (
                <button
                  key={id}
                  type="button"
                  className={`giq-tab text-[9px] ${p.analyticsSub === id ? "giq-tab-active" : ""}`}
                  onClick={() => p.setAnalyticsSub(id)}
                >
                  <span className="mr-1 opacity-80">{sym}</span>
                  {lab}
                </button>
              ))}
            </div>

            {p.analyticsSub === "model_intel" && (
              <div className="space-y-6">
                <EnginePane
                  data={p.engineData}
                  loading={p.engineLoading}
                  error={p.engineError}
                  rmuData={p.rmuData}
                />

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

            {p.analyticsSub === "team_needs" && (
              <div>
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

            {(p.analyticsSub === "scheme_fit" ||
              p.analyticsSub === "combine_lab" ||
              p.analyticsSub === "trend_signals") && (
              <div>
                <div className="giq-module-header border-t-0">
                  <div className="giq-mh-title">
                    <span>//</span>{" "}
                    {p.analyticsSub === "scheme_fit"
                      ? "SCHEME_FIT"
                      : p.analyticsSub === "combine_lab"
                        ? "COMBINE_LAB"
                        : "TREND_SIGNALS"}
                  </div>
                </div>
                <p className="mt-4 max-w-lg font-mono text-xs leading-relaxed text-[#7d8fa8]">
                  Wire-up pending: this rail mirrors the static platform module. Use BIG_BOARD + selected prospect for
                  scheme and combine context today; full trend layer will attach to team_context signals.
                </p>
              </div>
            )}

            {p.analyticsSub === "rmu_training" && (
              <RmuTrainingPane data={p.rmuData} loading={p.rmuLoading} error={p.rmuError} />
            )}

            {p.analyticsSub === "rmu_results" && (
              <RmuResultsPane data={p.rmuData} loading={p.rmuLoading} error={p.rmuError} />
            )}

            {p.analyticsSub === "rmu_predictions" && (
              <RmuPredictionsPane
                data={p.rmuData}
                loading={p.rmuLoading}
                error={p.rmuError}
                onOpenBoard={() => {
                  p.setRoomTab("big_board");
                  p.setBoardViewTab("rmu_predictions");
                }}
              />
            )}

            {p.analyticsSub === "engine_intel" && (
              <EnginePane
                data={p.engineData}
                loading={p.engineLoading}
                error={p.engineError}
                rmuData={p.rmuData}
              />
            )}

            {p.analyticsSub === "backtest_lab" && (
              <BacktestPane
                data={p.engineData}
                loading={p.engineLoading}
                error={p.engineError}
              />
            )}
          </div>
        )}

        {p.roomTab === "compare" && p.board && (
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
      </div>

      {/* RIGHT — prospect radar map (only when a row is selected; frees center width otherwise) */}
      {p.selected && (
        <aside className="giq-draft-right max-h-[calc(100vh-3.5rem)] overflow-y-auto lg:max-h-none">
          <div>
            <div className="giq-rp-header">SELECTED_PROSPECT</div>
            <div className="px-4 py-3">
              <div className="flex items-start gap-3">
                <div className="shrink-0">
                  <Headshot rmu={selectedRmu} name={p.selected.player_name} size="lg" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[20px] font-bold leading-tight tracking-tight text-[#dde4ef]">
                    {p.selected.player_name}
                  </div>
                  <div className="mt-1 font-mono text-[10px] text-[#7d8fa8]">
                    {p.selected.pos} · {p.selected.school}
                  </div>
                  {selectedRmu && (
                    <div className="mt-2">
                      <span className={r1ChipClass(selectedRmu.confidence)}>
                        P(R1) {Math.round(selectedRmu.r1_probability * 100)}% · {selectedRmu.confidence}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <div className="text-3xl font-bold text-[#d4a843]">{p.selected.final_draft_score.toFixed(1)}</div>
                <div className="font-mono text-[9px] uppercase tracking-wider text-[#3d4f66]">FINAL_SCORE</div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {(
                  [
                    ["40 YD", p.selected.forty != null ? p.selected.forty.toFixed(2) : null],
                    ["VERT", p.selected.vertical != null ? p.selected.vertical.toFixed(1) : null],
                    ["BENCH", p.selected.bench != null ? String(p.selected.bench) : null],
                    ["R1_PROB", selectedRmu ? `${Math.round(selectedRmu.r1_probability * 100)}%` : null],
                  ] as const
                ).map(([label, value]) => (
                  <div key={label} className="giq-combine-chip">
                    <span className="giq-combine-chip-label">{label}</span>
                    <span
                      className="giq-combine-chip-value"
                      style={label === "R1_PROB" && selectedRmu ? { color: confidenceColor(selectedRmu.confidence) } : undefined}
                    >
                      {value ?? "DNP"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div>
            <div className="giq-rp-header">PROSPECT_RADAR</div>
            <div className="px-2 py-2">
              <div className="h-[220px] w-full">
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
            </div>
          </div>
          <div>
            <div className="giq-rp-header">SIGNAL_BREAKDOWN</div>
            <div className="space-y-3 px-4 py-3">
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
                      className={
                        tone === "gold" ? "giq-signal-fill-gold" : tone === "green" ? "giq-signal-fill-green" : "giq-signal-fill-cyan"
                      }
                      style={{ width: `${val}%` }}
                    />
                  </div>
                </div>
              ))}
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
              <div className="flex justify-between border-b border-white/[0.04] py-2 text-[#7d8fa8]">
                <span>BOARD_ROWS</span>
                <span className="text-[#dde4ef]">{p.board?.prospects?.length ?? 0}</span>
              </div>
              <div className="flex justify-between border-b border-white/[0.04] py-2 text-[#7d8fa8]">
                <span>RMU_AUC</span>
                <span className="text-[#d4a843]">
                  {p.rmuData ? p.rmuData.ensembleAucMean.toFixed(3) : "—"}
                </span>
              </div>
              <div className="flex justify-between py-2 text-[#7d8fa8]">
                <span>CFBD_ID</span>
                <span className="text-[#dde4ef]">{selectedRmu?.cfbd_id ?? "—"}</span>
              </div>
            </div>
          </div>
        </aside>
      )}
    </main>
  );
}

function RmuPaneShell({
  title,
  loading,
  error,
  children,
}: {
  title: string;
  loading: boolean;
  error: Error | null;
  children: ReactNode;
}) {
  return (
    <div className="space-y-4">
      <div className="giq-module-header border-t-0">
        <div className="giq-mh-title">
          <span>//</span> {title}
        </div>
        <div className="giq-mh-sub">RMU_SAC · HACKATHON</div>
      </div>
      {loading && (
        <div className="flex items-center gap-2 font-mono text-xs text-[#7d8fa8]">
          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading model outputs…
        </div>
      )}
      {error && <p className="font-mono text-xs text-red-400">{error.message}</p>}
      {!loading && !error && children}
    </div>
  );
}

function RmuTrainingPane({
  data,
  loading,
  error,
}: {
  data: RmuData | undefined;
  loading: boolean;
  error: Error | null;
}) {
  return (
    <RmuPaneShell title="TRAINING_DATA · FEATURES + WALK_FORWARD" loading={loading} error={error}>
      <div className="grid gap-3 md:grid-cols-3">
        {(["QB", "WR", "RB"] as RmuPosition[]).map((pos) => {
          const rows = data?.featureImportance[pos] ?? [];
          const m = data?.metrics[pos];
          return (
            <div key={pos} className="rounded border border-white/[0.06] bg-[#131928] p-3">
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-[10px] uppercase tracking-wider text-[#d4a843]">{pos}</span>
                <span className="font-mono text-[9px] text-[#7d8fa8]">
                  LR {m ? m.lr_auc.toFixed(2) : "—"} · XGB {m ? m.xgb_auc.toFixed(2) : "—"}
                </span>
              </div>
              <table className="mt-3 w-full font-mono text-[10px]">
                <thead>
                  <tr className="text-[#7d8fa8]">
                    <th className="py-1 text-left font-normal">FEATURE</th>
                    <th className="py-1 text-right font-normal">LR</th>
                    <th className="py-1 text-right font-normal">XGB</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 8).map((r) => (
                    <tr key={r.feature} className="border-t border-white/[0.04] text-[#dde4ef]">
                      <td className="py-1">{r.feature}</td>
                      <td className="py-1 text-right text-[#f0c060]">{Number(r.lr_coef).toFixed(2)}</td>
                      <td className="py-1 text-right text-[#29b8e0]">{Number(r.xgb_gain).toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>
      <p className="font-mono text-[10px] leading-relaxed text-[#7d8fa8]">
        Training frames: 14 historical classes (2010 → 2024) · stratified K-fold CV · ensemble 0.4·LR + 0.6·XGBoost.
        Combine metrics are median-imputed with an <code className="text-[#f0c060]">_attended</code> flag; conference
        weighting rides on CFBD team strength.
      </p>
    </RmuPaneShell>
  );
}

function RmuResultsPane({
  data,
  loading,
  error,
}: {
  data: RmuData | undefined;
  loading: boolean;
  error: Error | null;
}) {
  const positions: RmuPosition[] = ["QB", "WR", "RB"];
  return (
    <RmuPaneShell title="MODEL_RESULTS · HOLDOUT_AUC" loading={loading} error={error}>
      <div className="grid gap-3 md:grid-cols-3">
        {positions.map((pos) => {
          const m = data?.metrics[pos];
          const ens = m ? 0.4 * m.lr_auc + 0.6 * m.xgb_auc : null;
          return (
            <div key={pos} className="rounded border border-white/[0.06] bg-[#131928] p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-[#d4a843]">{pos}</div>
              <div className="mt-2 text-3xl font-bold text-[#f0c060]">
                {ens != null ? ens.toFixed(3) : "—"}
              </div>
              <div className="font-mono text-[9px] text-[#7d8fa8]">ENSEMBLE_AUC</div>
              <div className="mt-3 space-y-2 font-mono text-[10px] text-[#dde4ef]">
                <div className="flex justify-between">
                  <span className="text-[#7d8fa8]">LR</span>
                  <span>{m ? m.lr_auc.toFixed(3) : "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#7d8fa8]">XGBoost</span>
                  <span>{m ? m.xgb_auc.toFixed(3) : "—"}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <p className="font-mono text-[10px] leading-relaxed text-[#7d8fa8]">
        Intuition for the judges: an ensemble AUC of{" "}
        {data ? data.ensembleAucMean.toFixed(2) : "—"} means that if you pick a random Round-1 player and a random
        non-first-rounder from the same position, the model ranks the first-rounder higher{" "}
        {data ? Math.round(data.ensembleAucMean * 100) : "—"}% of the time.
      </p>
    </RmuPaneShell>
  );
}

function RmuPredictionsPane({
  data,
  loading,
  error,
  onOpenBoard,
}: {
  data: RmuData | undefined;
  loading: boolean;
  error: Error | null;
  onOpenBoard: () => void;
}) {
  const positions: RmuPosition[] = ["QB", "WR", "RB"];
  return (
    <RmuPaneShell title="PREDICTIONS · 2026 CLASS P(R1)" loading={loading} error={error}>
      <div className="grid gap-3 md:grid-cols-3">
        {positions.map((pos) => {
          const rows = (data?.manifest ?? [])
            .filter((r) => r.position === pos)
            .sort((a, b) => b.r1_probability - a.r1_probability)
            .slice(0, 6);
          return (
            <div key={pos} className="rounded border border-white/[0.06] bg-[#131928] p-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-wider text-[#d4a843]">{pos}</span>
                <span className="font-mono text-[9px] text-[#7d8fa8]">TOP · P(R1)</span>
              </div>
              <ul className="mt-2 space-y-2">
                {rows.map((r, i) => (
                  <li key={r.name} className="flex items-center gap-2 font-mono text-[10px] text-[#dde4ef]">
                    <span className="w-5 text-right text-[#7d8fa8]">{i + 1}.</span>
                    {r.headshot_url ? (
                      <img src={r.headshot_url} alt={r.name} className="h-7 w-7 rounded-full border border-white/[0.08] object-cover" />
                    ) : (
                      <span className="giq-headshot-placeholder h-7 w-7 text-[9px]">
                        {r.name
                          .split(/\s+/)
                          .map((p) => p[0] ?? "")
                          .join("")
                          .slice(0, 2)
                          .toUpperCase()}
                      </span>
                    )}
                    <span className="min-w-0 flex-1 truncate">{r.name}</span>
                    <span className="text-[#7d8fa8]">{r.college_team}</span>
                    <span className={r1ChipClass(r.confidence)}>{Math.round(r.r1_probability * 100)}%</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-3">
        <Button
          className="h-8 bg-[#d4a843] font-mono text-[10px] font-bold uppercase tracking-wider text-[#050709] hover:bg-[#f0c060]"
          onClick={onOpenBoard}
        >
          Open RMU board tab
        </Button>
        <span className="font-mono text-[9px] uppercase tracking-wider text-[#7d8fa8]">
          {data?.r1Projected ?? 0} prospects projected in R1 · weighted by 0.4·LR + 0.6·XGB
        </span>
      </div>
    </RmuPaneShell>
  );
}

function MetricTile({
  label,
  value,
  delta,
  tone = "gold",
}: {
  label: string;
  value: string;
  delta?: string;
  tone?: "gold" | "cyan" | "green" | "ink";
}) {
  const color =
    tone === "cyan"
      ? "#29b8e0"
      : tone === "green"
        ? "#3ecf7a"
        : tone === "ink"
          ? "#dde4ef"
          : "#d4a843";
  return (
    <div className="rounded border border-white/[0.06] bg-[#131928] p-4">
      <div className="font-mono text-[9px] uppercase tracking-wider text-[#7d8fa8]">{label}</div>
      <div className="mt-1 text-2xl font-bold" style={{ color }}>
        {value}
      </div>
      {delta && (
        <div className="mt-1 font-mono text-[9px] uppercase tracking-wider text-[#3d4f66]">{delta}</div>
      )}
    </div>
  );
}

function CoefTable({
  rows,
  unit,
}: {
  rows: Array<{ feature: string; coef: number; abs: number }>;
  unit?: string;
}) {
  return (
    <table className="w-full font-mono text-[10px]">
      <thead>
        <tr className="text-[#7d8fa8]">
          <th className="py-1 text-left font-normal">FEATURE</th>
          <th className="py-1 text-right font-normal">COEF{unit ? ` (${unit})` : ""}</th>
          <th className="py-1 text-right font-normal">|x|</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.feature} className="border-t border-white/[0.04] text-[#dde4ef]">
            <td className="py-1">{r.feature}</td>
            <td className="py-1 text-right text-[#f0c060]">{r.coef.toFixed(3)}</td>
            <td className="py-1 text-right text-[#7d8fa8]">{r.abs.toFixed(3)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function EnginePane({
  data,
  loading,
  error,
  rmuData,
}: {
  data: EngineData | undefined;
  loading: boolean;
  error: Error | null;
  rmuData: RmuData | undefined;
}) {
  return (
    <div className="space-y-4">
      <div className="giq-module-header border-t-0">
        <div className="giq-mh-title">
          <span>//</span> ENGINE_INTEL · MODEL_CARD
        </div>
        <div className="giq-mh-sub">GAME_PRED + DRAFT_PRED · STATIC_BUNDLE</div>
      </div>

      {loading && (
        <div className="flex items-center gap-2 font-mono text-xs text-[#7d8fa8]">
          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading engine artifacts…
        </div>
      )}
      {error && <p className="font-mono text-xs text-red-400">{error.message}</p>}

      {data && (
        <>
          <div className="grid gap-3 md:grid-cols-4">
            <MetricTile
              label="GAME_ACC"
              value={pct(data.overall.accuracy)}
              delta={`${data.overall.correct}/${data.overall.total} · 2020-2025`}
            />
            <MetricTile
              label="WIN_PROB_LL"
              value={data.winProb.metrics.log_loss.toFixed(3)}
              delta={`brier ${data.winProb.metrics.brier.toFixed(3)} · ${data.winProb.metrics.calibrated ? "calibrated" : "raw"}`}
              tone="cyan"
            />
            <MetricTile
              label="MARGIN_MAE"
              value={data.margin.metrics.mae.toFixed(2)}
              delta={`rmse ${data.margin.metrics.rmse.toFixed(2)} · n=${data.margin.metrics.n_rows}`}
              tone="green"
            />
            <MetricTile
              label="TOTAL_MAE"
              value={data.total.metrics.mae.toFixed(2)}
              delta={`rmse ${data.total.metrics.rmse.toFixed(2)} · σ=${data.score.total_std.toFixed(1)}`}
              tone="green"
            />
          </div>

          {rmuData && (
            <div className="grid gap-3 md:grid-cols-3">
              {(["QB", "WR", "RB"] as RmuPosition[]).map((pos) => {
                const m = rmuData.metrics[pos];
                const ens = 0.4 * m.lr_auc + 0.6 * m.xgb_auc;
                return (
                  <MetricTile
                    key={pos}
                    label={`DRAFT_AUC · ${pos}`}
                    value={ens.toFixed(3)}
                    delta={`LR ${m.lr_auc.toFixed(2)} · XGB ${m.xgb_auc.toFixed(2)}`}
                    tone="cyan"
                  />
                );
              })}
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded border border-white/[0.06] bg-[#131928] p-3">
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-[10px] uppercase tracking-wider text-[#d4a843]">
                  WIN_PROB · LOGISTIC
                </span>
                <span className="font-mono text-[9px] text-[#7d8fa8]">
                  acc {pct(data.winProb.metrics.accuracy)}
                </span>
              </div>
              <div className="mt-2">
                <CoefTable rows={topFeatures(data.winProb, 6)} unit="logit" />
              </div>
              <p className="mt-3 font-mono text-[9px] leading-relaxed text-[#7d8fa8]">
                Intercept {data.winProb.intercept.toFixed(3)} · n={data.winProb.metrics.n_rows} · isotonic
                calibrated.
              </p>
            </div>
            <div className="rounded border border-white/[0.06] bg-[#131928] p-3">
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-[10px] uppercase tracking-wider text-[#d4a843]">
                  MARGIN · LINEAR
                </span>
                <span className="font-mono text-[9px] text-[#7d8fa8]">
                  σ {data.score.margin_std.toFixed(2)}
                </span>
              </div>
              <div className="mt-2">
                <CoefTable rows={topFeatures(data.margin, 6)} unit="pts" />
              </div>
              <p className="mt-3 font-mono text-[9px] leading-relaxed text-[#7d8fa8]">
                Intercept {data.margin.intercept.toFixed(2)} · MAE {data.margin.metrics.mae.toFixed(2)} pts.
              </p>
            </div>
            <div className="rounded border border-white/[0.06] bg-[#131928] p-3">
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-[10px] uppercase tracking-wider text-[#d4a843]">
                  TOTAL · LINEAR
                </span>
                <span className="font-mono text-[9px] text-[#7d8fa8]">
                  σ {data.score.total_std.toFixed(2)}
                </span>
              </div>
              <div className="mt-2">
                <CoefTable rows={topFeatures(data.total, 6)} unit="pts" />
              </div>
              <p className="mt-3 font-mono text-[9px] leading-relaxed text-[#7d8fa8]">
                Intercept {data.total.intercept.toFixed(2)} · MAE {data.total.metrics.mae.toFixed(2)} pts.
              </p>
            </div>
          </div>

          <div className="rounded border border-white/[0.06] bg-[#131928] p-4">
            <div className="font-mono text-[10px] uppercase tracking-wider text-[#d4a843]">
              SAMPLE_PREDICTION · {data.sample.predicted_winner} ↑
            </div>
            <div className="mt-2 grid gap-3 md:grid-cols-3">
              <div>
                <div className="font-mono text-[9px] text-[#7d8fa8]">WIN_PROB</div>
                <div className="text-2xl font-bold text-[#f0c060]">
                  {pct(data.sample.p_team_a_win)}
                </div>
              </div>
              <div>
                <div className="font-mono text-[9px] text-[#7d8fa8]">MARGIN</div>
                <div className="text-2xl font-bold text-[#dde4ef]">
                  {data.sample.predicted_margin.toFixed(1)} pts
                </div>
                <div className="font-mono text-[9px] text-[#3d4f66]">
                  ±{data.sample.score_ci.margin_sd.toFixed(2)}
                </div>
              </div>
              <div>
                <div className="font-mono text-[9px] text-[#7d8fa8]">TOTAL</div>
                <div className="text-2xl font-bold text-[#dde4ef]">
                  {data.sample.predicted_total.toFixed(1)}
                </div>
                <div className="font-mono text-[9px] text-[#3d4f66]">
                  ±{data.sample.score_ci.total_sd.toFixed(2)}
                </div>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-1 font-mono text-[9px] uppercase tracking-wider text-[#7d8fa8]">
              {data.sample.top_3_drivers.map(([key, val]) => (
                <span
                  key={key}
                  className="rounded border border-white/[0.06] bg-[#0a0d14] px-2 py-1 text-[#dde4ef]"
                >
                  {key} · {Number(val).toFixed(2)}
                </span>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function BacktestPane({
  data,
  loading,
  error,
}: {
  data: EngineData | undefined;
  loading: boolean;
  error: Error | null;
}) {
  return (
    <div className="space-y-4">
      <div className="giq-module-header border-t-0">
        <div className="giq-mh-title">
          <span>//</span> BACKTEST_LAB · 2020 → 2025
        </div>
        <div className="giq-mh-sub">PER_SEASON_ACCURACY · DEFENSIVE_RANKINGS</div>
      </div>

      {loading && (
        <div className="flex items-center gap-2 font-mono text-xs text-[#7d8fa8]">
          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading backtest…
        </div>
      )}
      {error && <p className="font-mono text-xs text-red-400">{error.message}</p>}

      {data && (
        <>
          <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
            {data.perSeason.map((s) => (
              <div key={s.season} className="rounded border border-white/[0.06] bg-[#131928] p-3">
                <div className="font-mono text-[10px] uppercase tracking-wider text-[#7d8fa8]">
                  {s.season}
                </div>
                <div className="mt-1 text-xl font-bold text-[#f0c060]">{pct(s.accuracy)}</div>
                <div className="font-mono text-[9px] text-[#3d4f66]">
                  {s.correct} / {s.total} games
                </div>
                <div className="giq-signal-track mt-2">
                  <div
                    className="giq-signal-fill-gold"
                    style={{ width: `${s.accuracy * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded border border-white/[0.06] bg-[#131928] p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-[#d4a843]">
                DEFENSIVE_STRENGTH · 2025 (top 10)
              </div>
              <table className="mt-3 w-full font-mono text-[10px]">
                <thead>
                  <tr className="text-[#7d8fa8]">
                    <th className="py-1 text-left font-normal">#</th>
                    <th className="py-1 text-left font-normal">TEAM</th>
                    <th className="py-1 text-right font-normal">DEF_Z</th>
                  </tr>
                </thead>
                <tbody>
                  {[...data.defStrength]
                    .sort((a, b) => b.def_z - a.def_z)
                    .slice(0, 10)
                    .map((row, i) => (
                      <tr key={row.defteam} className="border-t border-white/[0.04] text-[#dde4ef]">
                        <td className="py-1 text-[#7d8fa8]">{i + 1}</td>
                        <td className="py-1">{row.defteam}</td>
                        <td className="py-1 text-right text-[#f0c060]">{Number(row.def_z).toFixed(3)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>

            <div className="rounded border border-white/[0.06] bg-[#131928] p-4">
              <div className="font-mono text-[10px] uppercase tracking-wider text-[#d4a843]">
                R1_BOARD · COMBINED (top 10)
              </div>
              <table className="mt-3 w-full font-mono text-[10px]">
                <thead>
                  <tr className="text-[#7d8fa8]">
                    <th className="py-1 text-left font-normal">#</th>
                    <th className="py-1 text-left font-normal">PLAYER</th>
                    <th className="py-1 text-left font-normal">POS</th>
                    <th className="py-1 text-right font-normal">P(R1)</th>
                  </tr>
                </thead>
                <tbody>
                  {data.r1Board.slice(0, 10).map((row) => (
                    <tr key={row.name} className="border-t border-white/[0.04] text-[#dde4ef]">
                      <td className="py-1 text-[#7d8fa8]">{row.overall_rank}</td>
                      <td className="py-1">{row.name}</td>
                      <td className="py-1 text-[#7d8fa8]">{row.position}</td>
                      <td className="py-1 text-right text-[#f0c060]">{pct(row.r1_probability, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <p className="font-mono text-[10px] leading-relaxed text-[#7d8fa8]">
            Game-prediction backtest covers {data.overall.total.toLocaleString()} regular + postseason
            games across six seasons. Overall accuracy of {pct(data.overall.accuracy)} comfortably beats
            the home-team-always baseline (~57%). Margin model MAE is{" "}
            {data.margin.metrics.mae.toFixed(2)} pts; total points MAE is{" "}
            {data.total.metrics.mae.toFixed(2)} pts.
          </p>
        </>
      )}
    </div>
  );
}

/** Top banner rendered inside TEAM_VIEW that surfaces the team's ESPN-declared
 *  top-5 positional needs plus all of its 2026 picks (round, overall number,
 *  via-trade annotation, comp flag). */
function TeamNeedsStrip({
  team,
  nflDraft,
}: {
  team: string;
  nflDraft: NonNullable<EngineData["nflDraft"]>;
}) {
  const needs = nflDraft.team_needs[team] ?? [];
  const teamPicks = nflDraft.picks
    .filter((p) => p.team === team)
    .sort((a, b) => a.overall - b.overall);

  return (
    <div className="space-y-2 border-b border-white/[0.06] bg-[#0a0d14] px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-[#7d8fa8]">
          TEAM_NEEDS
        </span>
        {needs.length > 0 ? (
          needs.map((n, i) => (
            <span
              key={n}
              className={`rounded px-1.5 py-[2px] font-mono text-[10px] font-semibold uppercase tracking-wider ${
                i === 0
                  ? "border border-[#d4a843]/50 bg-[#d4a843]/15 text-[#d4a843]"
                  : "border border-white/15 bg-white/[0.04] text-[#dde4ef]"
              }`}
              title={`Need #${i + 1}`}
            >
              #{i + 1} {n}
            </span>
          ))
        ) : (
          <span className="font-mono text-[10px] text-[#7d8fa8]">—</span>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-[#7d8fa8]">
          2026_CAPITAL
        </span>
        {teamPicks.length === 0 ? (
          <span className="font-mono text-[10px] text-[#7d8fa8]">—</span>
        ) : (
          teamPicks.map((pick) => {
            const label = pick.via.length
              ? `R${pick.round}·#${pick.overall} (via ${pick.via.join("→")})`
              : `R${pick.round}·#${pick.overall}`;
            return (
              <span
                key={pick.overall}
                className={`rounded px-1.5 py-[2px] font-mono text-[10px] uppercase tracking-wider ${
                  pick.is_compensatory
                    ? "border border-[#3fd15b]/40 bg-[#3fd15b]/10 text-[#3fd15b]"
                    : pick.via.length
                      ? "border border-[#d4a843]/40 bg-[#d4a843]/10 text-[#d4a843]"
                      : "border border-white/15 bg-white/[0.04] text-[#dde4ef]"
                }`}
                title={
                  pick.is_compensatory
                    ? "Compensatory pick"
                    : pick.via.length
                      ? `Acquired via trade (${pick.original_team} → ${pick.team})`
                      : "Native pick"
                }
              >
                {label}
                {pick.is_compensatory ? " · COMP" : ""}
              </span>
            );
          })
        )}
        <span className="ml-auto font-mono text-[10px] text-[#7d8fa8]">
          {teamPicks.length} picks · {teamPicks.filter((p) => p.is_compensatory).length} comp ·{" "}
          {teamPicks.filter((p) => p.via.length).length} via trade
        </span>
      </div>
    </div>
  );
}

type MockDraftSimState =
  | { kind: "skip" }
  | { kind: "board_loading" }
  | {
      kind: "ready";
      fullPoolMode: boolean;
      rowsFull: ReturnType<typeof buildMockDraftFullPoolRows> | null;
      rowsSkill: ReturnType<typeof buildMockDraftSkillOnlyRows> | null;
      rmuLandings: ReturnType<typeof buildRmuMockLandings>;
      team_long_names: Record<string, string>;
      tradeCount: number;
      slotCount: number;
      fullPool: ApiDraftProspect[] | null;
    };

/**
 * Three-round mock (100 picks) with real ESPN order + full combine board when
 * the API is available; RMU-only fallback stays at round 1 only. Includes an
 * RMU landing table so every hackathon prospect shows mock slot vs R1 band.
 */
function MockDraftPane({
  rmuData,
  engineData,
  board,
  boardLoading,
  boardError,
}: {
  rmuData: RmuData | null | undefined;
  engineData: EngineData | null | undefined;
  board: ApiDraftBoard | undefined;
  boardLoading: boolean;
  boardError: Error | null;
}) {
  const draftSim = useMemo((): MockDraftSimState => {
    if (!engineData?.nflDraft || !rmuData) return { kind: "skip" };
    const { picks: allPicks, team_needs, team_long_names } = engineData.nflDraft;
    const slots3r = allPicks.filter((p) => p.round <= 3);
    const round1Only = allPicks.filter((p) => p.round === 1);
    const trade3r = slots3r.filter((p) => p.via.length > 0).length;
    const trade1r = round1Only.filter((p) => p.via.length > 0).length;
    const r1Sorted = [...engineData.r1Board].sort(
      (a, b) => (b.r1_probability ?? 0) - (a.r1_probability ?? 0),
    );
    const fullPool = board?.prospects && board.prospects.length > 0 ? board.prospects : null;
    const fullPoolMode = Boolean(fullPool);
    if (boardLoading && !fullPool) return { kind: "board_loading" };

    if (fullPoolMode && fullPool) {
      const rowsFull = buildMockDraftFullPoolRows(slots3r, team_needs, fullPool, engineData.r1Board);
      const rmuLandings = buildRmuMockLandings(
        engineData.r1Board,
        rowsFull.map((r) => ({ slot: r.slot, selectedName: r.selected?.player_name ?? null })),
      );
      return {
        kind: "ready",
        fullPoolMode: true,
        rowsFull,
        rowsSkill: null,
        rmuLandings,
        team_long_names,
        tradeCount: trade3r,
        slotCount: slots3r.length,
        fullPool,
      };
    }
    const rowsSkill = buildMockDraftSkillOnlyRows(round1Only, team_needs, r1Sorted);
    const rmuLandings = buildRmuMockLandings(
      engineData.r1Board,
      rowsSkill.map((r) => ({ slot: r.slot, selectedName: r.selected?.name ?? null })),
    );
    return {
      kind: "ready",
      fullPoolMode: false,
      rowsFull: null,
      rowsSkill,
      rmuLandings,
      team_long_names,
      tradeCount: trade1r,
      slotCount: round1Only.length,
      fullPool: null,
    };
  }, [engineData, rmuData, board, boardLoading]);

  if (!engineData) {
    return (
      <div className="p-5 font-mono text-xs text-[#7d8fa8]">
        Loading engine artifacts…
      </div>
    );
  }
  if (!engineData.nflDraft) {
    return (
      <div className="p-5 font-mono text-xs text-[#7d8fa8]">
        Real 2026 draft order JSON not found. Run{" "}
        <span className="text-[#d4a843]">python3 scripts/build_2026_draft_order.py</span>.
      </div>
    );
  }
  if (!rmuData) {
    return (
      <div className="p-5 font-mono text-xs text-[#7d8fa8]">
        Loading RMU/SAC prospect pool…
      </div>
    );
  }
  if (draftSim.kind === "board_loading") {
    return (
      <div className="p-5 font-mono text-xs text-[#7d8fa8]">
        Loading nflverse combine-class board (full positional pool)…
      </div>
    );
  }
  if (draftSim.kind !== "ready") {
    return null;
  }

  const {
    fullPoolMode,
    rowsFull,
    rowsSkill,
    rmuLandings,
    team_long_names,
    tradeCount,
    slotCount,
    fullPool,
  } = draftSim;

  const rows = rowsFull ?? rowsSkill!;
  const fits = rows.filter((r) => r.fitRank !== null).length;

  const byPos: Record<string, number> = {};
  for (const r of rows) {
    const sel = "selected" in r && r.selected ? r.selected : null;
    if (!sel) continue;
    const key =
      "pos_bucket" in sel ? (sel as ApiDraftProspect).pos_bucket : (sel as R1BoardRow).position ?? "—";
    byPos[key] = (byPos[key] ?? 0) + 1;
  }

  const rmuHitsOnBoard =
    fullPoolMode && fullPool
      ? fullPool.filter((p) => findR1Overlay(engineData.r1Board, p.player_name)).length
      : engineData.r1Board.length;

  const poolLabel = fullPoolMode ? fullPool!.length : engineData.r1Board.length;
  const boardTeam = board?.team;
  const r1InMock = rmuLandings.filter((x) => x.band === "IN_R1").length;
  const slipCount = rmuLandings.filter(
    (x) => x.model_r1_flag && x.mock_overall != null && x.mock_overall > 32,
  ).length;

  return (
    <div className="space-y-4 border-b border-white/[0.06] p-4">
      {!fullPoolMode && (
        <div className="rounded border border-[#d4a843]/35 bg-[#d4a843]/10 px-3 py-2 font-mono text-[10px] leading-relaxed text-[#dde4ef]">
          <span className="text-[#d4a843]">FALLBACK · SKILL_ONLY.</span> The nflverse draft board
          did not load
          {boardError ? ` (${boardError.message})` : ""}. Showing the 42-name RMU QB/WR/RB pool
          only. Start the GridironIQ API (
          <span className="text-[#7d8fa8]">VITE_API_BASE_URL</span>) so MOCK_DRAFT_3R can simulate
          **{MOCK_DRAFT_3R_PICKS} picks** (rounds 1–3) across the full combine class.
        </div>
      )}

      <div className="giq-module-header border-t-0">
        <div className="giq-mh-title">
          <span>//</span> 2026 NFL DRAFT · MOCK · ROUNDS_1–3
        </div>
        <div className="font-mono text-[10px] uppercase tracking-wider text-[#7d8fa8]">
          {fullPoolMode ? `${slotCount} picks` : "32 picks (R1 only fallback)"} · {tradeCount} trades
          ·{" "}
          {fullPoolMode
            ? "FULL_POOL · nflverse + consensus + needs + positional value + RMU overlay"
            : "RMU SKILL POOL (API unavailable)"}
        </div>
      </div>

      <div className="giq-kpi-bar">
        <div className="giq-kpi-item">
          <div className="giq-kpi-label">POOL_SIZE</div>
          <div className="giq-kpi-value text-[22px] text-[#d4a843]">{poolLabel}</div>
          <div className="giq-kpi-delta">
            {fullPoolMode ? "ALL_POSITIONS · COMBINE_CLASS" : "QB · WR · RB"}
          </div>
        </div>
        <div className="giq-kpi-item">
          <div className="giq-kpi-label">RMU_OVERLAY</div>
          <div className="giq-kpi-value text-[22px] text-[#d4a843]">{rmuHitsOnBoard}</div>
          <div className="giq-kpi-delta">NAMES_MATCH_R1_BOARD</div>
        </div>
        <div className="giq-kpi-item">
          <div className="giq-kpi-label">RMU_IN_R1</div>
          <div className="giq-kpi-value text-[22px] text-[#d4a843]">
            {r1InMock}/{rmuLandings.length}
          </div>
          <div className="giq-kpi-delta">LAND_TOP32_IN_MOCK</div>
        </div>
        <div className="giq-kpi-item">
          <div className="giq-kpi-label">SLIP</div>
          <div className="giq-kpi-value text-[22px] text-[#f0c060]">{slipCount}</div>
          <div className="giq-kpi-delta">MODEL_R1_BUT_MOCK_AFTER_32</div>
        </div>
        <div className="giq-kpi-item">
          <div className="giq-kpi-label">NEED_FITS</div>
          <div className="giq-kpi-value text-[22px] text-[#d4a843]">
            {fits}/{rows.length}
          </div>
          <div className="giq-kpi-delta">PICKS_HIT_TOP5_NEED</div>
        </div>
        <div className="giq-kpi-item">
          <div className="giq-kpi-label">QB · WR · RB</div>
          <div className="giq-kpi-value text-[22px] text-[#d4a843]">
            {(byPos["QB"] ?? 0)} · {(byPos["WR"] ?? 0)} · {(byPos["RB"] ?? 0)}
          </div>
          <div className="giq-kpi-delta">PICKS_IN_MOCK</div>
        </div>
        <div className="giq-kpi-item">
          <div className="giq-kpi-label">NO. 1_OVERALL</div>
          <div className="giq-kpi-value text-[22px] text-[#dde4ef]">
            {rows[0]?.selected
              ? "player_name" in rows[0].selected!
                ? (rows[0].selected as ApiDraftProspect).player_name
                : (rows[0].selected as R1BoardRow).name
              : "—"}
          </div>
          <div className="giq-kpi-delta">
            {rows[0]?.slot.team ?? "—"} · {rows[0] && team_long_names[rows[0].slot.team]}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded border border-white/[0.06]">
        <div className="giq-module-header border-0 border-b border-white/[0.06]">
          <div className="giq-mh-title">
            <span>//</span> {`RMU_LANDING · VS_${fullPoolMode ? "3R" : "R1"}_MOCK`}
          </div>
          <div className="font-mono text-[10px] uppercase tracking-wider text-[#7d8fa8]">
            every hackathon prospect · mock slot · in R1 band vs rounds 2–3 · slips
          </div>
        </div>
        <table className="giq-board-table w-full">
          <thead className="giq-board-thead">
            <tr>
              <th className="text-left">PLAYER</th>
              <th className="text-left">POS</th>
              <th className="text-right">P(R1)</th>
              <th className="text-left">MOCK</th>
              <th className="text-left">BAND</th>
              <th className="text-left">SLIP</th>
            </tr>
          </thead>
          <tbody>
            {rmuLandings.map((lm) => {
              const slip =
                lm.model_r1_flag && lm.mock_overall != null && lm.mock_overall > 32 ? "YES" : "—";
              const bandLabel =
                lm.band === "IN_R1" ? "R1" : lm.band === "R2_R3" ? "R2–R3" : "OUT";
              return (
                <tr
                  key={lm.name}
                  className={`giq-board-row ${lm.band === "IN_R1" ? "giq-board-row-rmu" : ""}`}
                >
                  <td className="font-semibold text-[#dde4ef]">{lm.name}</td>
                  <td className="font-mono text-[10px] text-[#7d8fa8]">{lm.position}</td>
                  <td className="text-right font-mono text-[#d4a843]">
                    {lm.r1_probability != null ? `${(lm.r1_probability * 100).toFixed(0)}%` : "—"}
                  </td>
                  <td className="font-mono text-[10px] text-[#7d8fa8]">
                    {lm.mock_overall != null ? `#${lm.mock_overall} · ${lm.mock_team ?? ""}` : "—"}
                  </td>
                  <td className="font-mono text-[10px] text-[#dde4ef]">{bandLabel}</td>
                  <td className="font-mono text-[10px] text-[#f0c060]">{slip}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="max-h-[min(70vh,780px)] overflow-auto overflow-x-auto rounded border border-white/[0.06]">
        <table className="giq-board-table w-full">
          <thead className="giq-board-thead">
            <tr>
              <th className="text-left">RD</th>
              <th className="text-left">PICK</th>
              <th className="text-left">TEAM · NEEDS</th>
              <th className="text-left">SELECTION</th>
              <th className="text-left">POS</th>
              <th className="text-left">SCHOOL</th>
              {fullPoolMode ? (
                <>
                  <th className="text-right">MOCK</th>
                  <th className="text-right">P(R1)</th>
                </>
              ) : (
                <th className="text-right">P(R1)</th>
              )}
              <th className="text-left">FIT</th>
              <th className="text-left">NEXT_BEST</th>
            </tr>
          </thead>
          <tbody>
            {fullPoolMode && rowsFull
              ? rowsFull.map(({ slot, needs, selected, fitRank, alternates, parts, r1Overlay }) => {
                  const rmu = selected ? matchRmu(rmuData, selected.player_name) : null;
                  const viaBadge =
                    slot.via.length > 0 ? `via ${slot.via.join(" → ")}` : null;
                  return (
                    <tr
                      key={slot.overall}
                      className={`giq-board-row ${r1Overlay ? "giq-board-row-rmu" : ""}`}
                    >
                      <td className="font-mono text-[10px] text-[#7d8fa8]">
                        R{slot.round}·{String(slot.pick_in_round).padStart(2, "0")}
                      </td>
                      <td className="font-mono text-[#d4a843]">
                        {String(slot.overall).padStart(2, "0")}
                      </td>
                      <td>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1 text-[13px] font-semibold text-[#dde4ef]">
                            <span>{slot.team}</span>
                            {viaBadge && (
                              <span
                                className="rounded border border-[#d4a843]/40 bg-[#d4a843]/10 px-1 py-[1px] font-mono text-[9px] uppercase tracking-wider text-[#d4a843]"
                                title={`${slot.original_team} → ${slot.team}`}
                              >
                                TRADE
                              </span>
                            )}
                          </div>
                          <div className="font-mono text-[10px] text-[#7d8fa8]">
                            {needs.length > 0 ? needs.join(" · ") : "—"}
                          </div>
                          {viaBadge && (
                            <div className="font-mono text-[9px] text-[#d4a843]/80">{viaBadge}</div>
                          )}
                        </div>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <Headshot rmu={rmu} name={selected?.player_name ?? "—"} size="sm" />
                          <div className="min-w-0">
                            <div className="truncate text-[13px] font-semibold text-[#dde4ef]">
                              {selected?.player_name ?? "—"}
                            </div>
                            <div className="font-mono text-[10px] text-[#7d8fa8]">
                              MDL {selected?.prospect_score?.toFixed(0) ?? "—"}
                              {selected?.model_rank != null ? ` · RANK ${selected.model_rank}` : ""}
                              {selected?.consensus_rank != null
                                ? ` · CON ${selected.consensus_rank}`
                                : ""}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td>
                        {selected ? (
                          <span className={prospectPosPill(selected.pos ?? "")}>{selected.pos}</span>
                        ) : null}
                      </td>
                      <td className="font-mono text-[10px] text-[#7d8fa8]">{selected?.school ?? "—"}</td>
                      <td className="text-right font-mono text-[#d4a843]">
                        {parts ? String(Math.round(parts.total * 100)) : "—"}
                      </td>
                      <td className="text-right font-mono text-[#7d8fa8]">
                        {r1Overlay?.r1_probability != null
                          ? `${(r1Overlay.r1_probability * 100).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td>
                        {fitRank != null ? (
                          <span className="rounded border border-[#3fd15b]/40 bg-[#3fd15b]/10 px-1.5 py-[1px] font-mono text-[10px] font-semibold text-[#3fd15b]">
                            NEED #{fitRank}
                          </span>
                        ) : (
                          <span className="font-mono text-[10px] text-[#7d8fa8]">BPA</span>
                        )}
                      </td>
                      <td className="font-mono text-[10px] text-[#7d8fa8]">
                        {alternates
                          .map((p) => `${p.player_name} (${p.pos})`)
                          .join(" · ") || "—"}
                      </td>
                    </tr>
                  );
                })
              : rowsSkill!.map(({ slot, needs, selected, fitRank, alternates }) => {
                  const rmu = selected ? matchRmu(rmuData, selected.name) : null;
                  const viaBadge =
                    slot.via.length > 0 ? `via ${slot.via.join(" → ")}` : null;
                  return (
                    <tr key={slot.overall} className={`giq-board-row ${selected ? "giq-board-row-rmu" : ""}`}>
                      <td className="font-mono text-[10px] text-[#7d8fa8]">
                        R{slot.round}·{String(slot.pick_in_round).padStart(2, "0")}
                      </td>
                      <td className="font-mono text-[#d4a843]">
                        {String(slot.overall).padStart(2, "0")}
                      </td>
                      <td>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1 text-[13px] font-semibold text-[#dde4ef]">
                            <span>{slot.team}</span>
                            {viaBadge && (
                              <span
                                className="rounded border border-[#d4a843]/40 bg-[#d4a843]/10 px-1 py-[1px] font-mono text-[9px] uppercase tracking-wider text-[#d4a843]"
                                title={`${slot.original_team} → ${slot.team}`}
                              >
                                TRADE
                              </span>
                            )}
                          </div>
                          <div className="font-mono text-[10px] text-[#7d8fa8]">
                            {needs.length > 0 ? needs.join(" · ") : "—"}
                          </div>
                          {viaBadge && (
                            <div className="font-mono text-[9px] text-[#d4a843]/80">{viaBadge}</div>
                          )}
                        </div>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <Headshot rmu={rmu} name={selected?.name ?? "—"} size="sm" />
                          <div className="min-w-0">
                            <div className="truncate text-[13px] font-semibold text-[#dde4ef]">
                              {selected?.name ?? "—"}
                            </div>
                            <div className="font-mono text-[10px] text-[#7d8fa8]">
                              {selected?.confidence ?? "—"}
                              {selected?.height
                                ? ` · ${Math.floor(selected.height / 12)}'${selected.height % 12}"`
                                : ""}
                              {selected?.weight ? ` · ${selected.weight}lb` : ""}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td>
                        {selected ? (
                          <span className={prospectPosPill(selected.position ?? "")}>
                            {selected.position ?? "—"}
                          </span>
                        ) : null}
                      </td>
                      <td className="font-mono text-[10px] text-[#7d8fa8]">
                        {selected?.college_team ?? "—"}
                      </td>
                      <td className="text-right font-mono text-[#d4a843]">
                        {selected?.r1_probability != null
                          ? `${(selected.r1_probability * 100).toFixed(0)}%`
                          : "—"}
                      </td>
                      <td>
                        {fitRank != null ? (
                          <span className="rounded border border-[#3fd15b]/40 bg-[#3fd15b]/10 px-1.5 py-[1px] font-mono text-[10px] font-semibold text-[#3fd15b]">
                            NEED #{fitRank}
                          </span>
                        ) : (
                          <span className="font-mono text-[10px] text-[#7d8fa8]">BPA</span>
                        )}
                      </td>
                      <td className="font-mono text-[10px] text-[#7d8fa8]">
                        {alternates.map((p) => `${p.name} (${p.position})`).join(" · ") || "—"}
                      </td>
                    </tr>
                  );
                })}
          </tbody>
        </table>
      </div>

      <p className="font-mono text-[10px] leading-relaxed text-[#7d8fa8]">
        Pick order follows the published 2026 NFL draft (trades + compensatory picks).{" "}
        {fullPoolMode ? (
          <>
            Runs <strong>{MOCK_DRAFT_3R_PICKS} consecutive slots</strong> (rounds 1–3). Each pick
            scores every remaining combine invitee using: (1) GridironIQ prospect_score, (2)
            consensus / market slotting, (3) ESPN top-5 needs for the <em>on-clock</em> team, (4)
            positional-value priors, (5) RMU P(R1) overlay on matching QB/WR/RB names. The RMU
            landing table compares every hackathon prospect to that mock: <strong>SLIP</strong> means
            the discrete R1 classifier flagged round-one but this composite mock took them after
            pick 32. Grades were built under API team context{" "}
            <span className="text-[#d4a843]">{boardTeam ?? "—"}</span>.
          </>
        ) : (
          <>
            Fallback uses only the 42-name RMU pool for <strong>round 1</strong> (32 picks). Enable
            the draft API for the full {MOCK_DRAFT_3R_PICKS}-pick three-round simulation.
          </>
        )}
      </p>
    </div>
  );
}
