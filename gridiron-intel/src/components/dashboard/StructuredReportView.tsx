import { motion } from "framer-motion";
import { Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ApiScoutingReport } from "@/lib/api";

interface StructuredReportViewProps {
  report: ApiScoutingReport;
  teamA: string;
  teamB: string;
  onDownloadJson?: () => void;
}

export default function StructuredReportView({
  report,
  teamA,
  teamB,
  onDownloadJson,
}: StructuredReportViewProps) {
  const handleDownloadJson = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gridironiq-report-${teamA}-vs-${teamB}-${report.season}.json`;
    a.click();
    URL.revokeObjectURL(url);
    onDownloadJson?.();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="card-surface rim-light border-l-4 border-l-primary p-6 space-y-6"
    >
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <span className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">
          Scouting Report
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="rounded-sm text-xs"
            onClick={handleDownloadJson}
          >
            <Download className="h-3.5 w-3.5 mr-1.5" />
            Download JSON
          </Button>
          <Button variant="ghost" size="sm" className="rounded-sm text-xs text-muted-foreground" disabled title="Future: PDF export and R-engine heatmaps">
            <FileText className="h-3.5 w-3.5 mr-1.5" />
            PDF (coming soon)
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {report.executive_summary?.headline && (
          <p className="text-sm font-semibold text-foreground">
            {report.executive_summary.headline}
          </p>
        )}
        <p className="font-serif text-sm leading-relaxed text-secondary-foreground">
          {report.executive_summary?.detail ?? report.summary}
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            {teamA} strengths
          </h4>
          <ul className="space-y-1 text-sm">
            {report.team_a_strengths.length ? (
              report.team_a_strengths.map((s, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="text-primary">•</span> {s}
                </li>
              ))
            ) : (
              <li className="text-muted-foreground">—</li>
            )}
          </ul>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            {teamB} strengths
          </h4>
          <ul className="space-y-1 text-sm">
            {report.team_b_strengths.length ? (
              report.team_b_strengths.map((s, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="text-primary">•</span> {s}
                </li>
              ))
            ) : (
              <li className="text-muted-foreground">—</li>
            )}
          </ul>
        </div>
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          Offensive profile (key margins)
        </h4>
        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          {report.offensive_profile[teamA] &&
            Object.entries(report.offensive_profile[teamA]).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2">
                <span className="text-muted-foreground">{k}</span>
                <span>{v}</span>
              </div>
            ))}
          {report.offensive_profile[teamB] &&
            Object.entries(report.offensive_profile[teamB]).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2">
                <span className="text-muted-foreground">{k}</span>
                <span>{v}</span>
              </div>
            ))}
        </div>
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          Prediction explanation
        </h4>
        <p className="text-sm text-secondary-foreground">{report.prediction_explanation}</p>
      </div>

      {report.risk_factors && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Key risk factors
          </h4>
          <ul className="space-y-1 text-xs text-muted-foreground">
            {report.risk_factors.map((r, i) => (
              <li key={i}>• {r}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          Confidence notes
        </h4>
        <ul className="space-y-1 text-xs text-muted-foreground">
          {report.confidence_notes.map((note, i) => (
            <li key={i}>• {note}</li>
          ))}
        </ul>
      </div>
    </motion.div>
  );
}
