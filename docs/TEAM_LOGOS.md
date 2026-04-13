# Team logo mapping

This document describes the **team logo manifest**: how filenames in `teamlogo/` are mapped to NFL team abbreviations and how to regenerate the manifest.

## Filename format

- **Pattern:** `{city_and_team_name}_{suffix}.{ext}`
- **Examples:**
  - `green_bay_packers_3191.png`
  - `san_francisco_49ers-primary-2009.png`
  - `new_england_patriots_logo_primary_20005480.png`
- **Rules:**
  - Multi-word cities and team names are joined with **underscores** (e.g. `green_bay_packers`, `new_orleans_saints`).
  - Hyphens in filenames are treated like underscores for matching (e.g. `tennessee-titans-logo-primary-1999-6125.png` still maps to Tennessee Titans).
  - The **trailing suffix** (e.g. `_123`, `_primary_2009`, `-primary-2020`) is ignored for matching; the mapping uses the longest known team-name prefix.
- **Supported extensions:** `.png`, `.jpg`, `.jpeg`, `.svg`, `.webp`

You do **not** need to rename files to a single pattern—the scanner matches stems to the 32 known teams and picks one file per team (see duplicates below).

## Regenerating the manifest

From the project root:

```bash
python scripts/generate_team_logo_manifest.py
```

This scans `teamlogo/` and writes **`outputs/team_logo_manifest.json`**.

Options:

- `--teamlogo-dir DIR` — Directory containing logo files (default: `teamlogo/`).
- `--out PATH` — Output JSON path (default: `outputs/team_logo_manifest.json`).

Example:

```bash
python scripts/generate_team_logo_manifest.py --teamlogo-dir ./teamlogo --out ./outputs/team_logo_manifest.json
```

The script prints:

- Number of **matched teams**
- Any **unmatched** filenames (no known team name prefix)
- Any **duplicates** (multiple files for the same team) and which file was chosen

## Duplicates and unmatched files

- **Duplicates:** If more than one file matches the same team (e.g. two Packers logos), the manifest keeps the **first filename alphabetically** and logs a warning. The written manifest’s `duplicates` object lists all filenames per team so you can see what was skipped.
- **Unmatched:** Files whose stem does not match any of the 32 NFL team name prefixes are listed in the manifest under `unmatched` and do not cause the script to fail. Add a mapping in `src/gridironiq/assets/team_logos.py` (`TEAM_NAME_TO_ABBR`) if you want them to map to a team.

## Manifest JSON shape

Written manifest (and returned by `GET /api/assets/team-logos`):

```json
{
  "teams": {
    "GB": {
      "abbr": "GB",
      "display_name": "Green Bay Packers",
      "normalized_name": "green_bay_packers",
      "filename": "green_bay_packers_3191.png",
      "path": "/teamlogo/green_bay_packers_3191.png"
    }
  },
  "unmatched": [],
  "duplicates": {}
}
```

- **path** uses a leading slash (`/teamlogo/...`) so the frontend can serve static files from that path (e.g. `public/teamlogo` or a proxy). If your app uses a different public path, you can transform `path` when loading the manifest or add a config option in the asset loader.

## Backend usage

- **Load manifest:** `from gridironiq.assets import load_logo_manifest; manifest = load_logo_manifest()` (default path: `outputs/team_logo_manifest.json`).
- **Resolve logo path:** `from gridironiq.assets import get_team_logo; path = get_team_logo("GB")` → `"/teamlogo/green_bay_packers_3191.png"` (or `None` if not found).

## Frontend static serving

The manifest’s `path` values are **`/teamlogo/<filename>`**. The GridironIQ frontend (Vite) serves files from `gridiron-intel/public/` at the site root, so logo images must be available under `gridiron-intel/public/teamlogo/`.

**Sync logos into the frontend:**

From the project root:

```bash
python scripts/sync_team_logos_to_frontend.py
```

This copies all logo images from `teamlogo/` to `gridiron-intel/public/teamlogo/`. Run it after adding or changing logos so the frontend can load them at `/teamlogo/...`.

## Frontend

- **Fetch manifest:** `GET /api/assets/team-logos` returns the full JSON. Use `teams[abbr].path` for the logo URL (e.g. `/teamlogo/green_bay_packers_3191.png`). Ensure logos are synced so that path resolves (see above).
