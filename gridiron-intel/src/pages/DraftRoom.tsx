import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Navbar from "@/components/layout/Navbar.tsx";
import {
  getDraftBoard,
  postDraftRecommend,
  postDraftAnalyst,
  postDraftTrade,
  aiChat,
  getTeamLogos,
} from "@/lib/api.ts";
import { matchRmu, useRmuData } from "@/lib/rmu.ts";
import { useEngineData } from "@/lib/engine.ts";
import DraftPlatformView from "./draft/DraftPlatformView.tsx";
import {
  type BoardViewTab,
  type AnalyticsSubTab,
  type DraftRoomTab,
  type PosFilter,
  type RmuHighlightFilter,
  BIG_BOARD_TOP_N,
  DRAFT_CFB_SEASON,
  DRAFT_COMBINE_SEASON,
  DRAFT_EVAL_SEASON,
  filterByBoardTab,
  filterByPosition,
  isAnalyticsSubTab,
  isDraftRoomTab,
  isLegacyDraftModule,
  sortProspects,
  type TableSortKey,
} from "./draft/draftBoardUtils.ts";
import "@/styles/draftPlatform.css";

const NFL_TEAMS = [
  "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB", "HOU",
  "IND", "JAX", "KC", "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG", "NYJ", "PHI",
  "PIT", "SEA", "SF", "TB", "TEN", "WAS",
];

export default function DraftRoom() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [posFilter, setPosFilter] = useState<PosFilter>("ALL");
  const [rmuHighlightFilter, setRmuHighlightFilter] = useState<RmuHighlightFilter>("ALL");
  const [boardViewTab, setBoardViewTab] = useState<BoardViewTab>("model_board");
  const [compareIdB, setCompareIdB] = useState<string | null>(null);
  const [prospectSearch, setProspectSearch] = useState("");

  const [team, setTeam] = useState("CAR");
  const [pickNumber, setPickNumber] = useState(19);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [chatQ, setChatQ] = useState("What happens if we pass on the top levered player?");
  const [chatOut, setChatOut] = useState("");
  const [tableSortKey, setTableSortKey] = useState<TableSortKey>("final_draft_score");
  const [tableSortDir, setTableSortDir] = useState<"asc" | "desc">("desc");
  const [maxTradeTarget, setMaxTradeTarget] = useState(47);

  const roomTab: DraftRoomTab = useMemo(() => {
    const r = searchParams.get("room");
    if (isDraftRoomTab(r)) {
      return r === "board" ? "big_board" : r;
    }
    return "big_board";
  }, [searchParams]);

  useEffect(() => {
    if (roomTab !== "prospect_db") setProspectSearch("");
  }, [roomTab]);

  const analyticsSub: AnalyticsSubTab = useMemo(() => {
    const a = searchParams.get("a");
    if (isAnalyticsSubTab(a)) return a;
    return "model_intel";
  }, [searchParams]);

  const setRoomTab = (tab: DraftRoomTab) => {
    const n = new URLSearchParams(searchParams);
    n.delete("tab");
    n.delete("module");
    const canonical = tab === "board" ? "big_board" : tab;
    if (canonical === "big_board") n.delete("room");
    else n.set("room", canonical);
    if (canonical !== "analytics") n.delete("a");
    setSearchParams(n);
  };

  const setAnalyticsSub = (sub: AnalyticsSubTab) => {
    const n = new URLSearchParams(searchParams);
    n.delete("module");
    n.set("room", "analytics");
    n.set("a", sub);
    setSearchParams(n);
  };

  useEffect(() => {
    const legacy = searchParams.get("module");
    if (!legacy || searchParams.get("room")) return;
    if (!isLegacyDraftModule(legacy)) return;

    const n = new URLSearchParams(searchParams);
    n.delete("module");
    n.delete("tab");

    if (legacy === "big_board" || legacy === "r1_projections") {
      n.delete("room");
      setSearchParams(n, { replace: true });
      if (legacy === "r1_projections") setBoardViewTab("r1_projections_tab");
      return;
    }
    if (legacy === "prospect_db") {
      n.set("room", "prospect_db");
      setSearchParams(n, { replace: true });
      return;
    }
    if (legacy === "simulator") {
      n.set("room", "simulator");
      setSearchParams(n, { replace: true });
      return;
    }
    if (legacy === "compare") {
      n.set("room", "compare");
      setSearchParams(n, { replace: true });
      return;
    }

    const analyticsLegacy: Record<string, AnalyticsSubTab> = {
      model_intel: "model_intel",
      team_needs: "team_needs",
      scheme_fit: "scheme_fit",
      combine_lab: "combine_lab",
      trend_signals: "trend_signals",
    };
    const sub = analyticsLegacy[legacy] ?? "model_intel";
    n.set("room", "analytics");
    n.set("a", sub);
    setSearchParams(n, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    if (searchParams.get("tab") === "mock" && searchParams.get("room") == null) {
      const n = new URLSearchParams(searchParams);
      n.delete("tab");
      n.delete("module");
      n.set("room", "simulator");
      setSearchParams(n, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    setMaxTradeTarget(pickNumber + 28);
  }, [pickNumber]);

  const boardQ = useQuery({
    queryKey: ["draft-board", team, DRAFT_COMBINE_SEASON, DRAFT_EVAL_SEASON, DRAFT_CFB_SEASON],
    queryFn: () =>
      getDraftBoard(team, DRAFT_COMBINE_SEASON, DRAFT_EVAL_SEASON, DRAFT_CFB_SEASON),
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
        combine_season: DRAFT_COMBINE_SEASON,
        eval_season: DRAFT_EVAL_SEASON,
        pick_number: pickNumber,
        n_simulations: 600,
        temperature: 2.0,
        cfb_season: DRAFT_CFB_SEASON,
      }),
  });

  const analystMut = useMutation({
    mutationFn: () =>
      postDraftAnalyst({
        team,
        combine_season: DRAFT_COMBINE_SEASON,
        eval_season: DRAFT_EVAL_SEASON,
        pick_number: pickNumber,
        n_simulations: 600,
        temperature: 2.0,
        ai_mode: "template",
        cfb_season: DRAFT_CFB_SEASON,
      }),
  });

  const tradeMut = useMutation({
    mutationFn: () =>
      postDraftTrade({
        team,
        combine_season: DRAFT_COMBINE_SEASON,
        eval_season: DRAFT_EVAL_SEASON,
        current_pick: pickNumber,
        max_target_pick: maxTradeTarget,
        n_simulations: 500,
        temperature: 2.0,
        cfb_season: DRAFT_CFB_SEASON,
      }),
  });

  const runIntel = () => {
    recMut.mutate();
    analystMut.mutate();
  };

  const sendChat = async () => {
    if (!chatQ.trim()) return;
    setChatOut("…");
    try {
      const res = await aiChat({
        question: chatQ,
        context_type: "draft",
        draft_team: team,
        combine_season: DRAFT_COMBINE_SEASON,
        eval_season: DRAFT_EVAL_SEASON,
        pick_number: pickNumber,
        ai_mode: "template",
        cfb_season: DRAFT_CFB_SEASON,
      });
      setChatOut(res.answer);
    } catch (e) {
      setChatOut(e instanceof Error ? e.message : "Chat failed");
    }
  };

  const logosQ = useQuery({ queryKey: ["team-logos"], queryFn: getTeamLogos });
  const rmuQ = useRmuData();
  const engineQ = useEngineData();

  const displayTeams = useMemo(() => {
    const m = logosQ.data?.teams;
    if (m && Object.keys(m).length) return Object.keys(m).sort();
    return NFL_TEAMS;
  }, [logosQ.data]);

  const sortedBoardRows = useMemo(() => {
    const rows = boardQ.data?.prospects ?? [];
    return sortProspects(rows, tableSortKey, tableSortDir);
  }, [boardQ.data?.prospects, tableSortKey, tableSortDir]);

  const displayRows = useMemo(() => {
    let rows = filterByPosition(sortedBoardRows, posFilter);
    if (boardViewTab === "consensus_board") {
      rows = [...rows].sort((a, b) => (a.consensus_rank ?? 1e9) - (b.consensus_rank ?? 1e9));
    } else if (boardViewTab === "by_team_fit") {
      rows = [...rows].sort(
        (a, b) => b.team_need_score + b.scheme_fit_score - (a.team_need_score + a.scheme_fit_score),
      );
    }
    rows = filterByBoardTab(rows, boardViewTab);
    if (rmuHighlightFilter === "RMU_ONLY" && rmuQ.data) {
      rows = rows.filter((r) => matchRmu(rmuQ.data, r.player_name));
    }
    const isBigBoard = roomTab === "big_board" || roomTab === "board";
    if (isBigBoard && boardViewTab !== "r1_projections_tab") {
      rows = [...rows].sort((a, b) => b.prospect_score - a.prospect_score).slice(0, BIG_BOARD_TOP_N);
    }
    return rows;
  }, [sortedBoardRows, posFilter, boardViewTab, roomTab, rmuHighlightFilter, rmuQ.data]);

  const prospectDbRows = useMemo(() => {
    const q = prospectSearch.trim().toLowerCase();
    if (!q) return displayRows;
    return displayRows.filter(
      (r) =>
        r.player_name.toLowerCase().includes(q) ||
        (r.school || "").toLowerCase().includes(q) ||
        (r.pos || "").toLowerCase().includes(q),
    );
  }, [displayRows, prospectSearch]);

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
    `cursor-pointer select-none hover:text-[#f0c060] ${tableSortKey === k ? "text-[#d4a843]" : "text-[#7d8fa8]"}`;

  const consensusMeta = boardQ.data?.meta?.consensus as { consensus_configured?: boolean } | undefined;
  const consensusConfigured = consensusMeta?.consensus_configured === true;

  return (
    <div className="giq-draft-root min-h-screen bg-[#050709] text-[#dde4ef]">
      <Navbar />
      <DraftPlatformView
        roomTab={roomTab}
        setRoomTab={setRoomTab}
        analyticsSub={analyticsSub}
        setAnalyticsSub={setAnalyticsSub}
        posFilter={posFilter}
        setPosFilter={setPosFilter}
        rmuHighlightFilter={rmuHighlightFilter}
        setRmuHighlightFilter={setRmuHighlightFilter}
        boardViewTab={boardViewTab}
        setBoardViewTab={setBoardViewTab}
        board={boardQ.data}
        boardLoading={boardQ.isLoading}
        boardError={boardQ.error ? (boardQ.error as Error) : null}
        displayRows={displayRows}
        prospectDbRows={prospectDbRows}
        prospectSearch={prospectSearch}
        setProspectSearch={setProspectSearch}
        selected={selected}
        selectedId={selectedId}
        setSelectedId={setSelectedId}
        toggleTableSort={toggleTableSort}
        sortHeaderClass={sortHeaderClass}
        team={team}
        setTeam={setTeam}
        displayTeams={displayTeams}
        pickNumber={pickNumber}
        setPickNumber={setPickNumber}
        maxTradeTarget={maxTradeTarget}
        setMaxTradeTarget={setMaxTradeTarget}
        runIntel={runIntel}
        intelBusy={recMut.isPending || analystMut.isPending}
        recData={recMut.data}
        analystData={analystMut.data}
        analystPending={analystMut.isPending}
        tradePending={tradeMut.isPending}
        tradeError={tradeMut.error ? (tradeMut.error as Error) : null}
        tradeScan={tradeMut.data?.trade_down_scan}
        runTrade={() => tradeMut.mutate()}
        compareIdB={compareIdB}
        setCompareIdB={setCompareIdB}
        chatQ={chatQ}
        setChatQ={setChatQ}
        chatOut={chatOut}
        sendChat={sendChat}
        consensusConfigured={consensusConfigured}
        refetchBoard={() => boardQ.refetch()}
        rmuData={rmuQ.data}
        rmuLoading={rmuQ.isLoading}
        rmuError={rmuQ.error ? (rmuQ.error as Error) : null}
        engineData={engineQ.data}
        engineLoading={engineQ.isLoading}
        engineError={engineQ.error ? (engineQ.error as Error) : null}
      />
    </div>
  );
}
