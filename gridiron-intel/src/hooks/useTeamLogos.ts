import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { getTeamLogos, type ApiTeamLogoEntry, type ApiTeamLogoManifest } from "@/lib/api";

/** Abbreviation alias: some data sources use LAR for Rams; manifest uses LA */
const ABBR_ALIAS: Record<string, string> = { LAR: "LA" };

export function useTeamLogos() {
  const { data: manifest, isLoading, isError, error } = useQuery({
    queryKey: ["team-logos"],
    queryFn: getTeamLogos,
    staleTime: 5 * 60 * 1000,
  });

  const byAbbr = useMemo(() => {
    if (!manifest?.teams) return {} as Record<string, ApiTeamLogoEntry>;
    const map = { ...manifest.teams };
    Object.entries(ABBR_ALIAS).forEach(([alias, canonical]) => {
      if (map[canonical] && !map[alias]) map[alias] = map[canonical];
    });
    return map;
  }, [manifest]);

  const getLogo = useMemo(
    () => (abbr: string) => byAbbr[abbr?.toUpperCase()] ?? byAbbr[ABBR_ALIAS[abbr?.toUpperCase() ?? ""]],
    [byAbbr]
  );

  const getLogoPath = useMemo(
    () => (abbr: string): string | undefined => getLogo(abbr)?.path,
    [getLogo]
  );

  return {
    manifest: manifest ?? null,
    byAbbr,
    getLogo,
    getLogoPath,
    isLoading,
    isError,
    error: error as Error | null,
  };
}
