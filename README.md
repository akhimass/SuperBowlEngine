# GridironIQ — NFL Draft Intelligence (RMU SAC)

**GridironIQ** is a first-round–centric draft intelligence stack built for the **RMU Sports Analytics Conference (SAC)** submission track: combine **structured prospect modeling**, **team need signals** from NFL usage and roster context, **Monte Carlo availability** at a given pick, and a **decision-room interface** that presents the board, levered recommendations, and optional analyst narrative in one place.

The product story is not generic scouting software—it is an **integrated draft desk**: what the class looks like for *your* team at *your* pick, how consensus and model order disagree (reach risk), where trading down moves the needle, and how a Round‑1 simulator behaves when other clubs follow need-aware heuristics.

---

## RMU SAC angle: first-round prediction & decision support

The submission emphasizes **Round 1** as the highest-leverage allocation window: scarce capital, compressed information, and cascading option value. GridironIQ Draft addresses that with:

- **Big board & grades** — Prospects are scored from nflverse combine and career tables, with optional college production enrichment when CollegeFootballData.com (CFBD) is configured. External consensus boards can be blended when `GRIDIRONIQ_DRAFT_CONSENSUS_DIR` is populated, so “market” order and model order can be compared explicitly.
- **Team needs** — Need scores are derived from EPA, snap, injury pressure, room production, and similar signal layers, with hooks for offseason move metadata (tags, pick-slot shifts, documented sources) so the board reflects *current* roster pressure—not a static depth chart label.
- **Availability & levered picks** — Simulations draw from the ordered board with temperature-controlled randomness to estimate who is still on the board at pick *k*; recommendations surface **levered** value (grade × realistic availability), not just raw rank.
- **Round 1 mock** — A browser-only Round 1 exercise (32 picks) uses the same narrative class as the reference board: user club on the clock, need tags, AI-style projections for opponents, and post-pick grading vs the model’s lean—useful as a teaching and demo surface for the conference audience.

Together, these pieces support the hackathon narrative: **data → model → uncertainty → decision**, with the UI making the pipeline legible without requiring the judges to read code.

---

## What “draft intelligence” includes here

| Theme | Description |
|--------|-------------|
| **Board** | Sortable prospect table: model rank, consensus, reach risk, market-style scores, and team-specific final grades. |
| **Needs & scheme** | Positional need scores and scheme-fit components feed the same radar-style breakdown the model sees. |
| **Intel & modes** | Beyond a single “best player” list: multiple ranking modes (e.g. best player available, best fit, upside, safety) grounded in the same simulation draw. |
| **Trade exploration** | Trade-down scan summarizes expected-value style deltas across target slots (approximate independence assumptions; useful for relative ordering). |
| **Reports** | PDF-oriented draft outputs (team needs, full board, prospect card) for a front-office style artifact suitable for a conference appendix. |

The codebase also retains broader GridironIQ capabilities (matchup engine, schedule tooling, etc.), but **this README is scoped to the draft / RMU SAC story** above.

---

## Data & modeling stance (informational)

- **Primary NFL data path:** nflverse-style tables for combine measurables, career summaries, and team-season context used to score needs and build the board.
- **Optional college layer:** CFBD player-season stats when an API key is present; otherwise college-driven subscores default to neutral behavior with explicit metadata in API responses.
- **Consensus:** When third-party board files are available, consensus rank and variance inform reach-risk and simulation ordering; when not, the pipeline is transparently model-forward.
- **RMU / “hackathon module” framing:** The repository and UI copy reference an **RMU SAC** first-round prediction / hackathon module as the narrative wrapper for the Round‑1 projection and class scoring story—aligned with the conference’s emphasis on reproducible sports analytics and clear communication of model limits.

---

## Intellectual honesty for judges

GridironIQ Draft is designed to **show its seams**: consensus vs model, CFBD on vs off, simulation count and temperature, and explicit notes where independence or availability approximations apply. The goal is defensible analytics for a short decision window—not a black-box “trust the number” widget.

---

## License

MIT (see `pyproject.toml`).
