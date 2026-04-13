#!/usr/bin/env -S python3 -u
"""
Generate the team logo manifest by scanning teamlogo/ and writing outputs/team_logo_manifest.json.

Usage:
  python scripts/generate_team_logo_manifest.py [--teamlogo-dir DIR] [--out PATH]

From project root (or set --teamlogo-dir and --out as needed).
"""

import argparse
import sys
from pathlib import Path

# Ensure src is on path
_repo = Path(__file__).resolve().parent.parent
if str(_repo / "src") not in sys.path:
    sys.path.insert(0, str(_repo / "src"))

from gridironiq.assets import write_logo_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate team logo manifest from teamlogo/")
    parser.add_argument(
        "--teamlogo-dir",
        type=Path,
        default=_repo / "teamlogo",
        help="Directory containing team logo image files",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_repo / "outputs" / "team_logo_manifest.json",
        help="Output JSON manifest path",
    )
    args = parser.parse_args()

    data = write_logo_manifest(args.teamlogo_dir, args.out)

    teams = data.get("teams") or {}
    unmatched = data.get("unmatched") or []
    duplicates = data.get("duplicates") or {}

    print(f"Matched teams: {len(teams)}")
    if unmatched:
        print(f"Unmatched files ({len(unmatched)}):")
        for f in unmatched:
            print(f"  - {f}")
    if duplicates:
        print("Duplicates resolved (first alphabetical chosen):")
        for abbr, files in duplicates.items():
            print(f"  {abbr}: {files}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
