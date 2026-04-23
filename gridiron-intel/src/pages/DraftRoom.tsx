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
import DraftPlatformView from "./draft/DraftPlatformView.tsx";
import {
  type BoardViewTab,
  type DraftModule,
  type PosFilter,
  filterByBoardTab,
  filterByPosition,
  isDraftModule,
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
  const [boardViewTab, setBoardViewTab] = useState<BoardViewTab>("model_board");
  const [compareIdB, setCompareIdB] = useState<string | null>(null);

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

  useEffect(() => {
    if (searchParams.get("tab") === "mock" && searchParams.get("module") == null) {
      const n = new URLSearchParams(searchParams);
      n.delete("tab");
      n.set("module", "simulator");
      setSearchParams(n, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const draftModule: DraftModule = useMemo(() => {
    const m = searchParams.get("module");
    if (isDraftModule(m)) return m;
    return "big_board";
  }, [searchParams]);

  const setDraftModule = (mod: DraftModule) => {
    const n = new URLSearchParams(searchParams);
    n.delete("tab");
    if (mod === "big_board") n.delete("module");
    else n.set("module", mod);
    setSearchParams(n);
  };

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
    return rows;
  }, [sortedBoardRows, posFilter, boardViewTab]);

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
        draftModule={draftModule}
        setDraftModule={setDraftModule}
        posFilter={posFilter}
        setPosFilter={setPosFilter}
        boardViewTab={boardViewTab}
        setBoardViewTab={setBoardViewTab}
        board={boardQ.data}
        boardLoading={boardQ.isLoading}
        boardError={boardQ.error ? (boardQ.error as Error) : null}
        displayRows={displayRows}
        selected={selected}
        selectedId={selectedId}
        setSelectedId={setSelectedId}
        toggleTableSort={toggleTableSort}
        sortHeaderClass={sortHeaderClass}
        team={team}
        setTeam={setTeam}
        displayTeams={displayTeams}
        combineSeason={combineSeason}
        setCombineSeason={setCombineSeason}
        cfbSeason={cfbSeason}
        setCfbSeason={setCfbSeason}
        evalSeason={evalSeason}
        setEvalSeason={setEvalSeason}
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
      />
    </div>
  );
}
