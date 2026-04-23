# GridironIQ – YC Coding Agent Session

## 1. Overview

GridironIQ is being built as a **full football intelligence platform**, not a single model or tab in a notebook. The system integrates **matchup prediction**, **team-context modeling**, **draft simulation and recommendations**, **coaching- and scouting-style reports**, **backtesting and calibration surfaces**, and **AI-assisted analysis that is explicitly grounded**—so that outputs can support real staff-style questions without pretending the data says more than it does.

The goal is to turn fragmented football data into systems that actually influence decisions, not just describe them.

This artifact is about **how the system was shaped**: through **prompt-driven engineering** in Cursor (exports: `cursor_superbowlengine_project_refactor.md`, `cursor_nfl_draft_decision_engine_develo.md`) plus the resulting repository. The work spans **data contracts**, **modeling discipline**, **pipeline and cache design**, **API and product surfaces**, and **operational reality** (tests, empty datasets, monorepos, optional PDF/ML stacks). YC should read it as evidence of **builder judgment**: the same person who frames product intent also enforces invariants, writes falsifiable checks, and refuses to ship “magic” columns.

The process was deliberately **non-linear**: architecture prompts before large refactors; **read-only audits** before logic changes; **discovery prompts** before AI/report integrations; **end-to-end fix** prompts when the UI betrayed silent failures; **season-scale** prompts when the schedule explorer outgrew one-off demos. The point is not which web framework rendered HTML—it is that **prompts functioned as specs, reviews, and product constraints**, the way a senior engineer uses abstraction layers and written design docs—except here the “doc” often *was* the instruction block driving the agent.

**Note on `claude chat doc.pdf`:** extracted text is mainly **2026 draft media research**, not an IDE transcript. It aligns **thematically** with later strict product specs (e.g. simulators that forbid invented players), but **this narrative’s engineering claims** are grounded in **Cursor exports and code**, not that PDF.

---

## 2. Prompt-Driven System Design

A defining characteristic of this work was treating **prompts as primary design artifacts**, not as “please write code.”

Prompts were used to:

- **Define architecture and boundaries** before touching large surfaces (draft pipeline vs reports vs UI; predictor vs schedule explorer).
- **Encode constraints** that define credibility: free public data only, no fabricated columns, team-agnostic behavior, refusal to assume cloud integrations that are not in-repo.
- **Run read-only audits** that force a complete mental model (per-file sources, columns, stubs, duplication) before refactors—reducing the chance of “clever” regressions.
- **Specify acceptance criteria** the way a strong PRD would: phased logo integration, multi-phase schedule pipeline, pytest plus integration scripts, curl expectations for API error semantics.
- **Drive debugging under uncertainty** (“fix the app, trace Analyze end-to-end,” “run real nflreadpy loads and fail closed,” “validate PDFs and HTTP 400 vs 500”) so failures become **observable** rather than blank UI states.
- **Rewrite systems for generality** (remove R runtime dependency; generalize off one demo matchup while keeping an explicit marketing showcase exception).

That pattern is what “**AI like a senior engineer uses abstraction layers**” means here: the agent is a **co-pilot for specification and execution**, while the human keeps **scope, constraints, and verification**—tests, audits, and product shape.

---

## 3. What Was Being Built

An **integrated decision-support environment**, not a scatter of scripts:

- **Matchup intelligence** — predictive stack plus explainability; historical games as validation objects, not one-off runs.
- **Schedule and game reports** — calendar-shaped browsing, enriched cards (actual vs predicted), deep per-game bundles.
- **Draft intelligence** — team needs, scheme context, room-level signals, prospect fusion, availability-style simulation hooks, war-room outputs consumable by API/CLI/UI.
- **Simulator surfaces** — API-backed draft room plus a **Round 1** client-side mode where latency and board fidelity trade off explicitly (`README.md`).
- **Reporting and assets** — structured bundles plus generated visuals where matplotlib/OS allow; outputs addressable for React without ad hoc path hacks.
- **Grounded AI** — Q&A and analyst flows constrained to **loaded context JSON**, with template fallbacks when local models or libs are absent.

---

## 4. Core Product Thesis

**Turn fragmented football reality into decision systems** people can act on: roster construction, game planning, draft capital, and “what does the data actually support?”

Why that is hard:

- **Football is multi-modal in the human sense, not the ML buzzword sense** — signals live in PBP, participation, injuries, college production, combine measurements, and consensus boards; the product job is to **fuse** them without laundering uncertainty into fake precision.
- **Integrity is the product** — leakage, silent defaults, and schema drift destroy trust faster than a wrong headline pick.
- **Usability is proof** — if Analyze returns nothing, or logos 404, or schedule cards lie about “predicted,” the system is not “mostly right”; it is **untrusted**.

---

## 5. System Architecture (Product-Shaped, Not Stack-Shaped)

Think in **stages and consumers**, not in framework marketing:

1. **Ingest and normalize** — schedules, PBP, player tables, injuries, snaps, combine, draft picks; college stats through a bounded HTTP client; centralized position and team identity handling.
2. **Feature and score** — matchup features with **pregame-style history** for training; prospect subscores (athletic, production, fit) composed rather than monolithically guessed; team needs as **layered signals** (EPA, usage, injury, room production) rather than one scalar “need.”
3. **Fuse and recommend** — draft board style outputs where multiple dimensions collapse into ranked actions, but **intermediate values remain inspectable** for traceability.
4. **Emit a single structured artifact family** — JSON bundles that can feed **API responses**, **UI tabs**, **PDF/HTML renderers**, and **LLM context** without each layer re-deriving its own joins.
5. **Cache when calendar-scale** — file-backed schedule predictions and per-game reports so the product stays responsive without pretending a database exists yet.
6. **Fail visibly** — empty PBP/schedules throw; report errors surface in UI; optional PDF/ML paths degrade with clear messages.

The repo layout (`gridironiq` package, `superbowlengine` core, `gridiron-intel` client, `outputs/` artifacts, `tests/` contracts) exists to **enforce those boundaries**, not to collect buzzwords.

---

## 6. Data Integrity & Constraints

Representative **specification prompts** (paraphrased themes enforced in session) that directly shaped engineering:

**Free sources only, traceable features.** Use nflverse, CFBD, combine, and PFR-style outcome history for training targets—**no paid vendor APIs** for the class-scoped draft engine. Every feature must be traceable to a loader and column contract, not invented because it “should” exist.

**Schema honesty.** Validate columns against real frames; prefer **loud skips or documented neutrals** over silent coercion. When neutral defaults exist (e.g. athletic partials), audits called them out so they are not mistaken for “real measured inputs.”

**Deterministic identity.** Normalize names, team abbreviations, and position buckets in **central mapping layers** so merges across nflverse and CFBD do not produce phantom duplicates or bucket drift—because inconsistent buckets break both needs and fit.

**No silent “completion.”** Avoid filling missing values with `0` or `50` without justification; when fallbacks exist, expose enough structure in outputs that a reviewer can see **where** the signal thinned.

Session anchor: the **read-only draft audit** demanded per-file **Purpose / Data sources / Columns / Hardcoding / Stubs / Duplicates** tables plus roadmap summaries—exactly the discipline in paragraphs **5–8** above, applied to the whole `draft/` tree.

---

## 7. Product Decisions Through Engineering

Key product choices **emerged through constraints and prompts**, not as a slide deck separate from code:

- **Draft engine as a core primitive** — Once the board JSON is real, **simulator**, **reports**, **analyst payloads**, and **API endpoints** become projections of the same object—avoiding “three definitions of truth.”
- **`TeamContext`-style aggregation** — Needs, scheme summaries, and room layers packaged so recommendations are **team-shaped**, not generic rankings.
- **Structured payloads for multi-consumer use** — Slim intel dicts for LLMs, full boards for PDFs, typed API shapes for React—each a **view** over shared logic, not a reimplementation per surface.
- **War-room outputs** — PDF/HTML paths tie analytics to **artifacts staff recognize** (needs sheets, boards, one-pagers), with OS-level honesty when WeasyPrint cannot load.
- **Simulation as decision glue** — Availability and trade-style scans turn static boards into **“who is realistically there”** questions—while audits also name where synthetic pick orders are still simplifications (honesty as roadmap).
- **Frontend-first integration** — Matchup vs schedule split, game report depth, logo consistency, and “no silent blank tabs” forced **contract fixes** in `api.ts` and handlers—not cosmetic polish after the fact.

That is the shift from **“we trained a model”** to **“we built a decision system”**: the product is the loop from **data → scored state → human-facing artifact → feedback**.

---

## 8. Prompt Specifications That Shaped GridironIQ

Below are **representative 3–4 sentence specification prompts**—the class of instructions used (or equivalent to what was enforced) while building. They double as **design docs**: architecture, audit, modeling, needs, scheme fit, simulation, decision logic, AI discipline, report systems, and operations (**specs 1–100** grouped thematically). After each cluster, a **session anchor** ties the pattern to what actually happened in Cursor exports.

### 8.1 Unified pipeline & modular boundaries (specs 1–4)

Design a **full NFL draft decision engine** that integrates prospect evaluation, team needs, scheme fit, and simulation into **one cohesive pipeline**, not a folder of disconnected scripts. Each stage’s outputs must feed the next without ad hoc re-joins in the frontend. Organize modules (`draft`, `models`, simulation, reports) with **clean interfaces** testable in isolation. Produce a **single structured JSON artifact family** so API, UI, and reporting consume the same truth, including intermediates for traceability.

**Session anchor:** Draft pipeline + `build_draft_intel_payload` / board JSON patterns; multi-phase **schedule + cache** prompts requiring season-wide enrichment rather than per-demo wiring.

### 8.2 Data integrity & constraints (specs 5–8)

Restrict to **free public data**; forbid paid APIs and **fabricated columns**. If a column is missing or renamed, **fail loudly** or document neutrals—never silently substitute. Reconcile naming across nflverse and CFBD in **one mapping layer**. Treat transparency about missing data as more important than forcing fake completeness.

**Session anchor:** Opening **free-data-only** draft mandate + full read-only audit before edits.

### 8.3 Codebase audit & refactor discipline (specs 9–12, 21–30)

Walk **every** relevant file: purpose, inputs, outputs, dependencies; verify sources against constraints—**do not assume correctness**. Flag hardcoded teams/seasons/thresholds that block generalization; flag duplicate loaders and repeated PBP pulls; flag TODOs that would ship as hidden failure modes. Consolidate shared utilities where duplication risks divergence. End with a **prioritized roadmap**, not a one-off fix list.

**Session anchor:** Per-file draft audit tables; antipattern checklist (team-agnostic, silent fills, caching); post-PDF **validation phases** (pytest, CLI, curl, PDF bytes); **`build_room_need_raw_by_team` cache** after audit quantified redundant loads.

### 8.4 Modeling & scoring (specs 13–16, 31–40)

Build prospect scoring as **independent normalized components** (athletic, production, efficiency) before fusion on a consistent scale. Convert combine raw metrics to **position-group percentiles**; handle outliers explicitly. Integrate CFBD with **competition-aware** adjustments, documented—not as raw stat worship. **Dispatch** scoring by position instead of one generic formula; keep intermediate components for auditability; prefer deterministic, reproducible scoring unless randomness is explicitly part of a simulation layer. Where NFL AV or similar proxies appear, **document limitations** and keep interfaces swappable for future ML without rewriting the whole pipeline.

**Session anchor:** `player_model.py` dispatch and combine percentiles discussed in audit; v2 matchup training spec (`MODEL_TRAINING_SUMMARY.md`) for **leakage-aware** historical rows.

### 8.5 Team context & needs (specs 17–20, 41–50)

Compute needs from **EPA, snap usage, injuries, and room-level production**, normalized into comparable buckets. Use **multi-season trends** with sane weighting toward recency. Aggregate room depth from player stats so “weak room” is a real object, not a headline. Enforce **one position-bucket ontology** across loaders, needs, and fit—otherwise the system disagrees with itself. Emit a structured **team context summary** consumable by API, UI, and LLM payloads.

**Session anchor:** `team_needs.py`, `room_production.py`, `team_context.py` audit narrative; cache fix tied to repeated room loads.

### 8.6 Scheme fit modeling (specs 51–60)

Build team scheme vectors from **PBP-derived tendencies** (usage, formations proxies where documented—not vibes-only labels). Represent players as **archetype-relevant attributes** per role; score fit with explicit similarity logic and position-specific adjustments. Document proxies when personnel columns are imperfect; keep outputs **interpretable** (components, not one black box). Integrate fit with needs and prospect scores in the final decision layer so fit is not an orphan feature.

**Session anchor:** `scheme_fit.py` audit (PBP + pass-game shares); discovery prompt reconciling **template vs Phi-4** paths before expanding report work.

### 8.7 Product, integration, and “no fantasy integrations”

**End-to-end product prompts** forced tracing the Analyze button through React and FastAPI, verifying logos and reports, and proving nflreadpy loads were non-empty. **Discovery-only** prompts required grep proof for **Azure / remote Microsoft** assumptions before implementing PDF/AI flows—then implementation was explicitly bounded to **local Phi-4 text** and templates already in-repo.

**Team-agnostic discipline (explicit refactor spec):** A one-team reference (e.g. Carolina during early development) must never become **special-cased logic** in scoring, needs, or simulation—only a default CLI example. Prompts framed audits to catch “accepts `team` but ignores it” and “weights tuned for one franchise” classes of bugs, because **reusable engines** are the product, not a personalized spreadsheet.

**Session anchor:** “**YOU MUST FIX THE APP**” triage; “**Do not change any code**” discovery pass listing AI modules and routes; “**Build… using ONLY what exists… No Azure**” implementation gate; audit antipatterns around **team parameters and generalization**.

### 8.8 Calendar-scale product and operations

Separate **free-form matchup prediction** from **schedule exploration**; require season-wide prediction/report generation with **cache keys** and optional precompute scripts; add navigation and copy that teach users the difference between “run any matchup” and “browse history with validation.” Operational prompts included **command matrices** (data smoke test, pytest, dev servers, env vars) so verification is repeatable—not tribal knowledge.

**Session anchor:** Multi-phase `/schedule`, `/api/game-report`, `pipeline_cache.py`, `POST /api/schedule/build`, `scripts/build_schedule_pipeline.py` direction in refactor export.

### 8.9 Simulation & draft modeling (specs 61–70)

Build a **Monte Carlo** draft engine that models **availability at picks**, not a single deterministic world—many runs, stable probability estimates, and explicit sampling rules (e.g. softmax over a top-K slice of the board) so higher-ranked players are usually taken but **variance remains**. Wire **availability into recommendations** so the system does not only rank “best player” but “best player **likely there**”; use the same machinery to inform **trade-up / trade-down** style scans as expected-value comparisons across slots. Keep runs **fast enough for interactive use** (tunable `n_simulations`, temperature, top-K); document every simplification—fake pick orders, independence assumptions, missing preference models—so outputs are never **more precise than the simulation deserves**.

**Session anchor:** `draft/simulator.py`, `trade_simulator.py`, `pipeline.run_availability_and_recommendations` discussed in audit (including **synthetic order** limitations called out explicitly rather than hidden).

### 8.10 Decision engine (specs 71–80)

Rank prospects by **fusing quality with simulated availability**—two dimensions, one recommendation surface. Expose **multiple ranking modes** (BPA, fit-heavy, upside, safety) as re-weightings of the same scored components, not unrelated hacks. Always thread **team context** into ranks so outputs stay franchise-shaped; emit **structured payloads** with top-N options per pick, score breakdowns, and clear explanations—deterministic given fixed inputs and fixed sim seeding where randomness applies. **Scrub misleading inputs**: if a parameter does not enter the math, do not pretend it does (audits flagged “team echoed only in metadata” classes of issues until clarified or fixed in docs/API contracts).

**Session anchor:** `draft/decision_engine.py`, `draft/draft_board.py`, `draft/report.py` and API intelligence payloads; validation-phase prompts around **`recommend_pick`** semantics and **400 vs 500** API behavior.

### 8.11 AI integration & prompt discipline (specs 81–90)

**Audit before integrate**: enumerate real AI entry points (`phi4_provider`, `explainer`, `draft_analyst`, chat); grep for **Azure / remote** clients; add **no new cloud dependency** unless it is real and justified. Prefer **template-first** paths so PDFs and APIs always return something; cap calls per request where needed; **strict parsing** for JSON-shaped model output with bounded retry and fallback. Ground every narrative in **structured context JSON**; refuse or template-fallback on out-of-scope questions. Log and test guardrails (`tests/test_ai_chat_guardrails.py` direction) so AI is an **enhancer**, not a single point of failure.

**Session anchor:** Discovery task blocks (read-only) + `build_chat_prompt` / grounded chat productization; “**only what exists in repo**” implementation gate for draft reports.

### 8.12 Report generation & output systems (specs 91–100)

Treat **war-room PDFs/HTML as core product**, not a weekend script: data models drive Jinja templates; WeasyPrint (or HTML-only fallbacks) produces **printable** needs sheets, prospect cards, and board layouts callable from **CLI and API**. Separate **data from presentation** so layout iteration does not fork scoring logic; embed **audit trails** (score components, policy notes) where templates allow. Reports must **survive missing AI** (fallback copy, skip sections); must handle **large boards** without pathological render time; must stay **visually consistent** across teams. When OS libs block PDF, the system still returns **actionable artifacts** (paths, HTML, clear errors)—reliability over demo magic.

**Session anchor:** `POST /api/draft/report`, `reports/renderer.py`, pipeline `--report` / `--no-ai`, WeasyPrint skip vs `SystemExit` / 500 honesty in validation transcripts.

---

## 9. Iteration, Debugging, and Hardening

Prompts here acted as **incident response and QA playbooks**:

- **Silent failures → explicit failures** — Empty schedule/PBP paths became throws and UI-visible report errors after “real data, no silent empty frames” pressure.
- **Monorepo traps** — `npm install` from repo root vs `gridiron-intel/` documented in “audit full app, give commands” style prompts.
- **Dependency graph conflicts** — Vite peer resolution surfaced as engineering work, not “try again.”
- **Optional heavy stacks** — WeasyPrint native libs and local LLM imports treated as **capabilities with graceful degradation**, not hard dependencies that crash imports.
- **Performance discovered by audit** — Room raw map recomputation quantified and fixed via caching once a prompt demanded measurement, not vibes.
- **Deployment-shaped failures** — Prompts that treat “no open ports,” missing static directories, and split UI/API hosting as **first-class bugs** (create dirs before static mounts, CORS allow-lists, env-driven API base URLs)—the same class of issues that kill student demos in production.

This is **builder thinking through prompts**: each failure mode gets a **named owner** (loader, handler, mount, cache, test).

---

## 10. Key Engineering Tradeoffs (Compact)

- **Truth vs speed** — JSON caches and optional precompute for schedule scale; still file-backed, not over-engineered.
- **Slim LLM context vs full board** — Draft analyst payloads trimmed to reduce hallucination surface; full rows stay on the board object where templates/PDF need them.
- **Explainability vs backbone** — v2 models for win/margin/total; Five Keys and reports as interpretive layers—separation is intentional.
- **Marketing exception vs core generality** — Hardcoded showcase card allowed; core flows audited for GB/DET-only assumptions.
- **Tests as living spec** — Integration scripts and pytest for pipelines, payloads, guardrails—not snapshot magic numbers tied to one team’s retrain.
- **Simulation realism vs compute** — Many Monte Carlo draws and rich pick-order models fight latency; the shipped system documents shortcuts (e.g. synthetic order) while still delivering **availability-shaped** recommendations.
- **AI value vs reliability** — Optional Phi-4 and strict context grounding; templates and fallbacks so war-room and chat never depend on a remote API that is not in-repo.
- **Report polish vs portability** — WeasyPrint-quality PDFs vs OS deps; HTML and JSON paths remain first-class when PDF cannot load.

---

## 11. Code Fingerprints (Evidence, Not the Story)

Two small excerpts show **invariants** the prose claims—without turning this into a framework tutorial.

**Pregame-style history for training rows (leakage discipline):**

```51:74:src/gridironiq/models/training_data.py
def _pbp_prior_for_game(pbp_all: pd.DataFrame, season_type: str, week: Any) -> pd.DataFrame:
    """
    Return PBP subset representing data available before the given game.

    - For REG games: only REG plays with week < current week.
    - For POST games: REG plays for the season + POST plays with week < current week (if week present).
      If postseason week is unavailable, falls back to all REG plays (no POST learning for that game).
    """
```

**Grounded analyst Q&A (context-only answers):**

```14:18:src/gridironiq/ai/chat.py
def build_chat_prompt(question: str, ctx: ExplainerContext) -> str:
    """
    A strict, grounded chat prompt: answer ONLY using the provided context JSON.
    If out-of-scope, refuse and ask for a question about the current matchup/game.
    """
```

---

## 12. What This Session Demonstrates

This session demonstrates the ability to:

- **Design multi-layer systems** spanning ingestion, modeling, **simulation and decision fusion**, **grounded AI**, **report generation**, API contracts, React surfaces, and operational verification—without collapsing them into one undifferentiated script.
- **Use coding agents as system-design collaborators**: prompts as **specs, audits, acceptance tests, and refactors**—not as autocomplete for random files.
- **Maintain data integrity under real constraints**: free sources, schema honesty, centralized identity maps, and explicit handling of missing football reality.
- **Translate ambiguous product intent into working systems**: predictor vs schedule split, calendar-scale caching, grounded AI, draft room artifacts, and “fix the app” closures when UX exposed contract bugs.
- **Iterate without fooling yourself**: audits that name duplicate loads, synthetic simulator order shortcuts, and neutral-score paths—**labeled**, not hidden.

**Build narrative (one paragraph):** The arc runs from **“audit everything, change nothing”** to **“implement under strict discovery”**, in parallel with **product integration prompts** that forced logos, Analyze, schedule cards, and game reports to tell the same story as the backend. The through-line is **intellectual honesty plus shipping**: not claiming NFL team adoption or production revenue here—only that the builder **thinks in systems**, **writes constraints like a staff engineer**, and **uses prompts the way strong teams use design docs and runbooks**—to shape a football intelligence platform that can keep growing without lying about what the data knows.

I'm building GridironIQ as a platform for sports decision-making systems, and this session reflects how I turn complex, real-world domains into structured, usable intelligence.
