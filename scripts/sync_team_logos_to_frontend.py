#!/usr/bin/env -S python3 -u
"""
Copy team logo assets from repo root teamlogo/ to gridiron-intel/public/teamlogo/
so the Vite frontend can serve them at /teamlogo/... (manifest paths).

Run from project root:
  python scripts/sync_team_logos_to_frontend.py
"""

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "teamlogo"
TARGET = REPO_ROOT / "gridiron-intel" / "public" / "teamlogo"


def main() -> int:
    if not SOURCE.is_dir():
        print(f"Source not found: {SOURCE}", file=sys.stderr)
        return 1
    TARGET.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in SOURCE.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".svg", ".webp"):
            continue
        if p.name.startswith("."):
            continue
        dest = TARGET / p.name
        shutil.copy2(p, dest)
        count += 1
    print(f"Synced {count} logo(s) to {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
