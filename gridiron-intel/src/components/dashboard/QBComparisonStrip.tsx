import { motion } from "framer-motion";
import type { QBComparison } from "@/data/mockData";

interface QBComparisonStripProps {
  data: QBComparison;
}

const metrics = [
  { key: "epaPerPlay" as const, label: "EPA/Play", higherIsBetter: true },
  { key: "cpoe" as const, label: "CPOE", higherIsBetter: true },
  { key: "pressuredRate" as const, label: "Pressure Rate", higherIsBetter: false },
  { key: "aggPct" as const, label: "Aggressiveness %", higherIsBetter: true },
];

export default function QBComparisonStrip({ data }: QBComparisonStripProps) {
  const { qbA, qbB } = data;

  return (
    <div className="card-surface rim-light p-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <span className="pill-qb">{qbA.name}</span>
        </div>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">QB Comparison</h3>
        <div>
          <span className="pill-qb">{qbB.name}</span>
        </div>
      </div>
      <div className="space-y-4">
        {metrics.map((m, i) => {
          const aVal = qbA[m.key];
          const bVal = qbB[m.key];
          const maxVal = Math.max(Math.abs(aVal), Math.abs(bVal)) * 1.3 || 1;
          const aWidth = (Math.abs(aVal) / maxVal) * 100;
          const bWidth = (Math.abs(bVal) / maxVal) * 100;
          const aWins = m.higherIsBetter ? aVal > bVal : aVal < bVal;

          return (
            <div key={m.key}>
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span className={`font-mono font-semibold ${aWins ? "text-success" : "text-foreground"}`}>
                  {aVal}
                </span>
                <span>{m.label}</span>
                <span className={`font-mono font-semibold ${!aWins ? "text-success" : "text-foreground"}`}>
                  {bVal}
                </span>
              </div>
              <div className="flex gap-1 h-2">
                <div className="flex-1 flex justify-end">
                  <motion.div
                    className={`h-full rounded-sm ${aWins ? "bg-success" : "bg-secondary"}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${aWidth}%` }}
                    transition={{ duration: 0.8, delay: 0.2 + i * 0.08 }}
                  />
                </div>
                <div className="flex-1">
                  <motion.div
                    className={`h-full rounded-sm ${!aWins ? "bg-success" : "bg-secondary"}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${bWidth}%` }}
                    transition={{ duration: 0.8, delay: 0.2 + i * 0.08 }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
