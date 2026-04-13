import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { FileText, Search, CheckCircle, XCircle } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import TeamLogo from "@/components/TeamLogo";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MOCK_SAVED_REPORTS, SEASONS } from "@/data/mockData";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06, delayChildren: 0.15 } },
};
const item = {
  hidden: { y: 10, opacity: 0 },
  show: { y: 0, opacity: 1, transition: { ease: [0.16, 1, 0.3, 1] as [number, number, number, number], duration: 0.5 } },
};

export default function ReportLibrary() {
  const [seasonFilter, setSeasonFilter] = useState("all");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    return MOCK_SAVED_REPORTS.filter((r) => {
      if (seasonFilter !== "all" && String(r.season) !== seasonFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          r.teamA.toLowerCase().includes(q) ||
          r.teamB.toLowerCase().includes(q) ||
          r.week.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [seasonFilter, search]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="pt-20 pb-12 px-4">
        <div className="container max-w-5xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold tracking-tighter mb-1">Report Library</h1>
            <p className="text-sm text-muted-foreground">Previously generated scouting reports and matchup analyses</p>
          </div>

          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by team, week, or round…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 bg-secondary border-border rounded-sm"
              />
            </div>
            <Select value={seasonFilter} onValueChange={setSeasonFilter}>
              <SelectTrigger className="w-36 bg-secondary border-border rounded-sm"><SelectValue placeholder="Season" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Seasons</SelectItem>
                {SEASONS.map((s) => <SelectItem key={s} value={String(s)}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {/* Reports grid */}
          {filtered.length === 0 ? (
            <div className="card-surface rim-light p-16 text-center">
              <FileText className="h-10 w-10 mx-auto text-muted-foreground mb-4" />
              <p className="text-sm text-muted-foreground">No reports found matching your criteria.</p>
            </div>
          ) : (
            <motion.div variants={container} initial="hidden" animate="show" className="grid md:grid-cols-2 gap-4">
              {filtered.map((report) => {
                const correct = report.predictedWinner === report.actualWinner;
                return (
                  <motion.div
                    key={report.id}
                    variants={item}
                    className="card-surface rim-light p-5 border-l-4 border-l-primary hover:border-l-accent transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 shrink-0">
                          <TeamLogo team={report.teamA} size={36} className="rounded-full" />
                          <span className="text-muted-foreground font-medium">vs</span>
                          <TeamLogo team={report.teamB} size={36} className="rounded-full" />
                        </div>
                        <div>
                          <h3 className="font-semibold tracking-tight text-lg">
                            {report.teamA} vs {report.teamB}
                          </h3>
                          <p className="text-xs text-muted-foreground">
                            {report.season} · {report.week}
                          </p>
                        </div>
                      </div>
                      <span className="pill-neutral font-mono">{report.confidence}%</span>
                    </div>
                    <div className="grid grid-cols-3 gap-3 text-sm">
                      <div>
                        <span className="text-xs text-muted-foreground block">Predicted</span>
                        <span className="font-semibold">{report.predictedWinner}</span>
                      </div>
                      <div>
                        <span className="text-xs text-muted-foreground block">Actual</span>
                        <span className="font-semibold">{report.actualWinner}</span>
                      </div>
                      <div className="flex items-end justify-end">
                        {correct ? (
                          <span className="flex items-center gap-1 text-xs text-success font-medium">
                            <CheckCircle className="h-3.5 w-3.5" /> Correct
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-xs text-primary font-medium">
                            <XCircle className="h-3.5 w-3.5" /> Missed
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-border">
                      <span className="text-xs text-muted-foreground">
                        Generated {new Date(report.generatedAt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                      </span>
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
