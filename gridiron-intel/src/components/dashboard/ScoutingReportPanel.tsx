import { motion } from "framer-motion";

interface ScoutingReportPanelProps {
  content: string;
  teamA: string;
  teamB: string;
}

export default function ScoutingReportPanel({ content, teamA, teamB }: ScoutingReportPanelProps) {
  const paragraphs = content.split("\n\n").filter(Boolean);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="card-surface rim-light border-l-4 border-l-primary p-6"
    >
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xs uppercase tracking-widest text-muted-foreground font-semibold">Scouting Report</span>
        <span className="pill-neutral">{teamA} vs {teamB}</span>
      </div>
      <div className="space-y-4 font-serif text-sm leading-relaxed text-secondary-foreground">
        {paragraphs.map((p, i) => {
          if (p.startsWith("## ")) {
            return (
              <h4 key={i} className="font-display text-base font-semibold text-foreground mt-4 first:mt-0">
                {p.replace("## ", "")}
              </h4>
            );
          }
          return <p key={i}>{p}</p>;
        })}
      </div>
    </motion.div>
  );
}
