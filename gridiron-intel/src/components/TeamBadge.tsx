import TeamLogo from "@/components/TeamLogo";
import { useTeamLogos } from "@/hooks/useTeamLogos";

const sizeMap = {
  sm: 24,
  md: 32,
  lg: 40,
};

interface TeamBadgeProps {
  team: string;
  size?: "sm" | "md" | "lg";
  showName?: boolean;
  className?: string;
}

export default function TeamBadge({ team, size = "md", showName = false, className = "" }: TeamBadgeProps) {
  const { getLogo } = useTeamLogos();
  const abbr = team?.toUpperCase() ?? "";
  const entry = getLogo(abbr);
  const displayName = entry?.display_name ?? abbr;
  const px = sizeMap[size];

  return (
    <div className={`inline-flex items-center gap-2 shrink-0 ${className}`.trim()}>
      <TeamLogo team={abbr} size={px} className="rounded-full" showFallback />
      {showName && (
        <span className="text-sm font-medium truncate max-w-[120px]" title={displayName}>
          {displayName}
        </span>
      )}
    </div>
  );
}
