import { motion } from "framer-motion";
import type { MetricComparison } from "@/data/mockData";

interface ComparisonTableProps {
  metrics: MetricComparison[];
  teamA: string;
  teamB: string;
}

export default function ComparisonTable({ metrics, teamA, teamB }: ComparisonTableProps) {
  return (
    <div className="card-surface rim-light overflow-hidden">
      <div className="grid grid-cols-3 px-5 py-3 border-b border-border text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        <span>{teamA}</span>
        <span className="text-center">Metric</span>
        <span className="text-right">{teamB}</span>
      </div>
      {metrics.map((m, i) => {
        const aWins = m.higherIsBetter ? m.teamAValue > m.teamBValue : m.teamAValue < m.teamBValue;
        const bWins = m.higherIsBetter ? m.teamBValue > m.teamAValue : m.teamBValue < m.teamAValue;
        return (
          <motion.div
            key={m.metric}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.04, duration: 0.4 }}
            className="grid grid-cols-3 px-5 py-3 border-b border-border last:border-b-0 text-sm"
          >
            <span className={`font-mono font-semibold ${aWins ? "text-success" : ""}`}>
              {m.teamAValue}{m.unit}
            </span>
            <span className="text-center text-muted-foreground text-xs">{m.metric}</span>
            <span className={`font-mono font-semibold text-right ${bWins ? "text-success" : ""}`}>
              {m.teamBValue}{m.unit}
            </span>
          </motion.div>
        );
      })}
    </div>
  );
}
