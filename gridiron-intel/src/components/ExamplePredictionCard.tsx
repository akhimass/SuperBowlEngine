import TeamBadge from "@/components/TeamBadge";

interface ExamplePredictionCardProps {
  className?: string;
}

export default function ExamplePredictionCard({ className }: ExamplePredictionCardProps) {
  return (
    <section
      className={`card-surface rim-light relative overflow-hidden p-6 md:p-8 flex flex-col gap-4 md:gap-5 ${className ?? ""}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-1">Example Prediction</p>
          <h2 className="text-xl md:text-2xl font-semibold tracking-tight">Super Bowl LX</h2>
        </div>
        <div className="px-2.5 py-1 rounded-full border border-emerald-500/60 bg-emerald-500/10 text-[10px] font-medium uppercase tracking-[0.18em] text-emerald-300">
          Validated Example
        </div>
      </div>

      <div className="grid md:grid-cols-[1.2fr_auto_1.2fr] items-center gap-4 md:gap-6">
        <div className="flex flex-col items-start gap-2">
          <TeamBadge team="SEA" size="md" showName />
          <p className="text-xs text-muted-foreground uppercase tracking-[0.18em]">Seattle Seahawks</p>
        </div>

        <div className="flex flex-col items-center gap-2 text-center">
          <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
            GridironIQ projected
          </div>
          <div className="font-mono text-lg md:text-xl font-semibold">
            SEA <span className="text-primary">31</span> – NE <span className="text-primary">18</span>
          </div>
          <div className="h-px w-12 bg-border/70" />
          <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
            Final score
          </div>
          <div className="font-mono text-sm md:text-base text-muted-foreground">
            SEA <span className="font-semibold text-foreground">29</span> – NE <span className="font-semibold text-foreground">13</span>
          </div>
        </div>

        <div className="flex flex-col items-end gap-2">
          <TeamBadge team="NE" size="md" showName />
          <p className="text-xs text-muted-foreground uppercase tracking-[0.18em]">New England Patriots</p>
        </div>
      </div>

      <p className="text-sm md:text-[13px] text-muted-foreground leading-relaxed max-w-2xl">
        The platform correctly identified Seattle&apos;s edge and projected a multi-score win in the right scoring
        range — a concrete example of GridironIQ translating matchup fundamentals into actionable, validated insight.
      </p>
    </section>
  );
}

