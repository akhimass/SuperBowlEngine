import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Index from "./pages/Index.tsx";
import MatchupAnalysis from "./pages/MatchupAnalysis.tsx";
import Backtesting from "./pages/Backtesting.tsx";
import ScheduleExplorer from "./pages/ScheduleExplorer.tsx";
import GameReport from "./pages/GameReport.tsx";
import ReportLibrary from "./pages/ReportLibrary.tsx";
import DraftRoom from "./pages/DraftRoom.tsx";
import DraftSimulatorPage from "./pages/DraftSimulatorPage.tsx";
import NotFound from "./pages/NotFound.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/matchup" element={<MatchupAnalysis />} />
          <Route path="/schedule" element={<ScheduleExplorer />} />
          <Route path="/schedule/:season/:gameId" element={<GameReport />} />
          <Route path="/accuracy" element={<Backtesting />} />
          <Route path="/reports" element={<ReportLibrary />} />
          <Route path="/draft" element={<DraftRoom />} />
          <Route path="/draft/simulator" element={<DraftSimulatorPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
