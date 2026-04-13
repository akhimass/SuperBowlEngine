import { motion } from "framer-motion";
import type { MatchupEdge } from "@/data/mockData";

const categoryStyles: Record<string, string> = {
  offense: "pill-offense",
  defense: "pill-defense",
  qb: "pill-qb",
  situational: "pill-neutral",
};

interface EdgePanelProps {
  edges: MatchupEdge[];
  teamA: string;
  teamB: string;
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06, delayChildren: 0.2 } },
};
const item = {
  hidden: { x: -8, opacity: 0 },
  show: { x: 0, opacity: 1, transition: { ease: [0.16, 1, 0.3, 1] as [number, number, number, number], duration: 0.5 } },
};

export default function EdgePanel({ edges, teamA, teamB }: EdgePanelProps) {
  return (
    <div className="card-surface rim-light p-5">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">
        Key Matchup Edges
      </h3>
      <motion.ul variants={container} initial="hidden" animate="show" className="space-y-3">
        {edges.map((edge, i) => (
          <motion.li key={i} variants={item} className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 min-w-0">
              <span className={categoryStyles[edge.category]}>{edge.category}</span>
              <span className="text-sm truncate">{edge.label}</span>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className={`text-xs font-mono font-semibold ${
                edge.advantage === "A" ? "text-success" : edge.advantage === "B" ? "text-primary" : "text-muted-foreground"
              }`}>
                {edge.advantage === "A" ? teamA : edge.advantage === "B" ? teamB : "EVEN"}
              </span>
              <div className="w-16 h-1.5 rounded-sm bg-secondary overflow-hidden">
                <motion.div
                  className={`h-full rounded-sm ${edge.advantage === "A" ? "bg-success" : "bg-primary"}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(edge.magnitude / 5 * 100, 100)}%` }}
                  transition={{ duration: 0.8, delay: 0.3 + i * 0.05 }}
                />
              </div>
            </div>
          </motion.li>
        ))}
      </motion.ul>
    </div>
  );
}
