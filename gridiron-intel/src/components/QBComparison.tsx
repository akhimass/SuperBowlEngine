import { Loader2 } from "lucide-react";
import type { ApiQBCompareResponse } from "@/lib/api";

interface QBComparisonProps {
  data?: ApiQBCompareResponse | null;
  loading?: boolean;
  error?: string | null;
}

export function QBComparison({ data, loading, error }: QBComparisonProps) {
  if (loading) {
    return (
      <div className="card-surface rim-light p-6 flex flex-col items-center justify-center gap-2">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
        <p className="text-xs text-muted-foreground">Computing QB production comparison…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card-surface rim-light p-4 text-xs text-destructive">
        QB comparison unavailable: {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card-surface rim-light p-4 text-xs text-muted-foreground">
        Enter quarterback names and run a matchup to see QB production scores.
      </div>
    );
  }

  const { qb_a, qb_b, total_score, sustain_score, situational_score, offscript_score, avg_def_z } = data;

  return (
    <div className="card-surface rim-light p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase text-muted-foreground mb-1">QB A</div>
          <div className="font-semibold text-sm">{qb_a}</div>
        </div>
        <div className="text-center">
          <div className="text-xs uppercase text-muted-foreground mb-1">Production Score</div>
          <div className="text-2xl font-bold">
            {Math.round((total_score[qb_a] ?? 0) * 10) / 10} — {Math.round((total_score[qb_b] ?? 0) * 10) / 10}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs uppercase text-muted-foreground mb-1">QB B</div>
          <div className="font-semibold text-sm">{qb_b}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <div className="text-muted-foreground mb-1">Drive Sustain</div>
          <div className="flex justify-between">
            <span>{qb_a}: {Math.round((sustain_score[qb_a] ?? 0) * 10) / 10}</span>
            <span>{qb_b}: {Math.round((sustain_score[qb_b] ?? 0) * 10) / 10}</span>
          </div>
        </div>
        <div>
          <div className="text-muted-foreground mb-1">Situational</div>
          <div className="flex justify-between">
            <span>{qb_a}: {Math.round((situational_score[qb_a] ?? 0) * 10) / 10}</span>
            <span>{qb_b}: {Math.round((situational_score[qb_b] ?? 0) * 10) / 10}</span>
          </div>
        </div>
        <div>
          <div className="text-muted-foreground mb-1">Off-Script</div>
          <div className="flex justify-between">
            <span>{qb_a}: {Math.round((offscript_score[qb_a] ?? 0) * 10) / 10}</span>
            <span>{qb_b}: {Math.round((offscript_score[qb_b] ?? 0) * 10) / 10}</span>
          </div>
        </div>
        <div>
          <div className="text-muted-foreground mb-1">Defense Strength Faced (z)</div>
          <div className="flex justify-between">
            <span>{qb_a}: {(avg_def_z[qb_a] ?? 0).toFixed(2)}</span>
            <span>{qb_b}: {(avg_def_z[qb_b] ?? 0).toFixed(2)}</span>
          </div>
        </div>
      </div>

      <p className="text-[11px] text-muted-foreground">
        Scores reflect postseason drive sustain, situational execution, and off-script value, adjusted for defensive difficulty — a compact QB production lens to pair with the team matchup view.
      </p>
    </div>
  );
}

