import { useTeamLogos } from "@/hooks/useTeamLogos";

interface TeamLogoProps {
  team: string;
  size?: number;
  className?: string;
  showFallback?: boolean;
}

export default function TeamLogo({ team, size = 32, className = "", showFallback = true }: TeamLogoProps) {
  const { getLogoPath, isLoading } = useTeamLogos();
  const abbr = team?.toUpperCase() ?? "";
  const path = getLogoPath(abbr);

  const sizePx = Math.max(16, Math.min(96, size));
  const containerClass = `inline-flex items-center justify-center shrink-0 rounded-full overflow-hidden bg-muted border border-border ${className}`.trim();

  if (isLoading) {
    return (
      <div
        className={containerClass}
        style={{ width: sizePx, height: sizePx }}
        aria-hidden
      />
    );
  }

  if (path) {
    return (
      <span className={containerClass} style={{ width: sizePx, height: sizePx }}>
        <img
          src={path}
          alt={`${abbr} logo`}
          className="w-full h-full object-contain"
          style={{ width: sizePx, height: sizePx }}
          loading="lazy"
        />
      </span>
    );
  }

  if (!showFallback) return null;

  return (
    <div
      className={containerClass}
      style={{ width: sizePx, height: sizePx }}
      title={abbr}
    >
      <span className="text-[10px] font-bold uppercase text-muted-foreground leading-none">
        {abbr.slice(0, 2)}
      </span>
    </div>
  );
}
