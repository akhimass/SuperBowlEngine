## Final productization summary (v2)

### What was productized

#### Matchup Predictor
- **Situational Tendencies** tab now renders **real generated heatmap PNGs** (when available) using the full matchup report pipeline.
- **AI Statistician** tab now includes a compact, game-grounded **“Ask about this matchup”** Q&A panel.

#### Game Report
- Removed the dedicated **Developer JSON** tab from the primary tab row.
- Added a compact, game-grounded **“Ask about this game”** Q&A panel in the AI tab.
- Added a single **Developer Debug** accordion below the tab set to preserve diagnostics without polluting the primary UX.

### Visuals integrated

- Generated report assets are now **served by the backend** and displayed in the UI:
  - `outputs/reports/*.png` mounted at `GET /report-assets/<filename>`
  - `build_matchup_report(..., generate_heatmaps=True)` returns `report_assets[].url` for direct `<img>` usage.

### AI chat (game constrained)

- Added backend endpoint:
  - `POST /api/ai/chat`
- Guardrails:
  - Prompt forces answers to rely on the **current report context only**.
  - Template mode refuses out-of-scope questions with the explicit guardrail message.
- Added test:
  - `tests/test_ai_chat_guardrails.py`

### Files changed / added

**Backend**
- Updated: `src/gridironiq/api.py` (static mount + `/api/ai/chat`)
- Updated: `src/gridironiq/reports/matchup_report.py` (adds `report_assets[].url`)
- Added: `src/gridironiq/ai/chat.py`
- Added: `tests/test_ai_chat_guardrails.py`

**Frontend**
- Added: `gridiron-intel/src/components/dashboard/ChartPanel.tsx`
- Added: `gridiron-intel/src/components/dashboard/DeveloperDebugAccordion.tsx`
- Updated: `gridiron-intel/src/lib/api.ts` (full matchup report + ai chat client)
- Updated: `gridiron-intel/src/pages/MatchupAnalysis.tsx` (situational visuals + AI Q&A)
- Updated: `gridiron-intel/src/pages/GameReport.tsx` (AI Q&A + dev debug accordion)

### Remaining optional enhancements (not blockers)

- Replace the remaining dev-only situational tables with fully rendered tables (no debug JSON at all).
- Add more situational visuals beyond heatmaps (field position diagram, red zone diagram, run direction lanes) and render them in a dedicated `SituationalVisualGrid`.
- Add a tiny “export” action for broadcast/presentation views (PDF later).

