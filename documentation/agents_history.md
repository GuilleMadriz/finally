# FinAlly — Agent Teams History

A reconstructed account of how the FinAlly trading workstation was built by orchestrated AI agent teams, drawn from committed planning documents, code-review docs, PR descriptions, commit messages, and the source tree itself.

This document is a learning aid. It is not a verbatim chat transcript — those were not persisted — but everything below is sourced from artifacts that were committed to the repo. File paths, commits, and quoted text point to the durable record.

The build was not a single linear effort. Multiple agent teams, using different orchestration frameworks, took different runs at the same goal across separate branches. Section 1 covers the most exhaustively documented track (the GSD 10-phase build on `origin/finally-gsd`); Section 2 covers the earlier market-data-focused PR pipeline; Section 3 compares the parallel implementations.

---

## 1. The GSD Agent Team

### 1.1 Framework overview

GSD ("Get Shit Done") is an opinionated, file-driven orchestration framework for building software with Claude. Instead of one long-context conversation, GSD splits the work across eleven specialized sub-agents that each have a narrow brief, talk to one another exclusively through markdown artifacts under `.planning/`, and are re-entered by command files in `.claude/commands/` (e.g. `/gsd:new-project`, `/gsd:plan-phase`, `/gsd:execute-phase`). Persistent state (`.planning/STATE.md`) captures the current cursor through the project so any agent can be resumed cold after a `/clear`. A small Node CLI (`./.claude/get-shit-done/bin/gsd-tools.js`) handles state mutations, frontmatter parsing, plan-structure validation, and git commits — agents call it rather than re-implementing the bookkeeping themselves.

The orchestration pattern is strictly phased. A project begins with research and roadmap creation (PROJECT.md, REQUIREMENTS.md, ROADMAP.md, plus `.planning/research/` and `.planning/codebase/` maps). Each ROADMAP phase then runs through a fixed pipeline: **research → plan → check → execute → verify**. The phase researcher writes `NN-RESEARCH.md` (standard stack, pitfalls, code samples). The planner consumes that and produces one or two `NN-NN-PLAN.md` files with XML `<task>` blocks, must-haves frontmatter, and a wave-based dependency graph. The plan-checker statically audits those plans before any execution burns context. The executor runs each plan, writes `NN-NN-SUMMARY.md`, and commits per task. Finally the verifier reads SUMMARY.md skeptically, walks the codebase against the must-haves, and produces `NN-VERIFICATION.md` — the one document that actually decides whether the phase is "done."

The eleven agents collaborate through these documents rather than through chat. The planner never reads code directly when codebase docs already exist; it reads `.planning/codebase/CONVENTIONS.md` instead. The executor never re-derives the goal; it reads must-haves from the plan frontmatter. The verifier never trusts the executor's SUMMARY.md self-report; it re-walks the artifacts and key links the plan promised. This explicit handoff format keeps each agent's working context small (the planner targets ≤50% context per plan) and makes mid-stream resumes safe — STATE.md plus the per-phase markdowns are sufficient to know exactly where the project stopped.

### 1.2 The 11 specialized agents

**gsd-project-researcher** — Domain ecosystem reconnaissance. Spawned by `/gsd:new-project` (often four in parallel, one per focus). Surveys the technology landscape with a mandatory tool priority (Context7 → official docs → WebSearch, with explicit confidence levels HIGH/MEDIUM/LOW). Treats Claude's own training as a hypothesis to verify, not a fact. Produces four files in `.planning/research/`: `STACK.md` (recommended technology with rationale), `FEATURES.md` (table-stakes vs differentiators vs anti-features), `ARCHITECTURE.md` (component boundaries, data flow), and `PITFALLS.md` (critical/moderate/minor traps with phase mapping). Operates in three modes — ecosystem (default), feasibility ("can we do X?"), and comparison ("A vs B vs C") — and chooses output schemas accordingly. Does not commit; the synthesizer does.

**gsd-research-synthesizer** — Read-and-condense agent that runs after the four parallel project-researchers finish. Reads STACK/FEATURES/ARCHITECTURE/PITFALLS, integrates rather than concatenates them, and writes `.planning/research/SUMMARY.md` containing an executive summary, key findings, and most critically the "Implications for Roadmap" section that suggests phase ordering with rationale. Also assigns honest confidence levels per area, identifies remaining gaps, and tags which future phases will need a deeper `/gsd:research-phase`. Commits all five research files together, since the parallel researchers deliberately don't.

**gsd-codebase-mapper** — Reads an existing codebase for one of four focus areas (`tech` → STACK.md + INTEGRATIONS.md, `arch` → ARCHITECTURE.md + STRUCTURE.md, `quality` → CONVENTIONS.md + TESTING.md, `concerns` → CONCERNS.md). Writes documents directly to `.planning/codebase/` using strict templates so downstream agents can grep them. Hard rules: every finding must include a backticked file path, every claim must be prescriptive ("use camelCase for functions") not descriptive ("some functions use camelCase"), and protected files (`.env`, `*.pem`, credentials, etc.) may be noted as existing but never read or quoted. Returns only a confirmation, never document contents.

**gsd-roadmapper** — Transforms requirements into phase structure. Spawned by `/gsd:new-project`. Anti-enterprise philosophy: no sprints, RACI, or stakeholder ceremonies — just one user, one Claude, and "buckets of work." Derives phases from requirement clusters (vertical slices preferred over horizontal layers), assigns every v1 requirement to exactly one phase, and applies goal-backward thinking at the phase level — for each phase it asks "what must be TRUE for users when this phase completes?" and writes 2–5 observable success criteria. Validates 100% requirement coverage (no orphans) before allowing the project to proceed. Initializes STATE.md as the running project memory.

**gsd-phase-researcher** — Per-phase technical reconnaissance, spawned by `/gsd:plan-phase`. Narrower than project-researcher: answers "what do I need to know to PLAN this phase well?" Honors any `CONTEXT.md` from `/gsd:discuss-phase` as locked decisions (no exploring alternatives to user-locked choices, no scoping in deferred ideas). Produces a single `NN-RESEARCH.md` with sections the planner specifically expects: Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples (verified from official sources), State of the Art, Open Questions. Output is prescriptive ("use X") not exploratory ("consider X or Y").

**gsd-planner** — The most prescriptive agent. Decomposes a phase into 1–3 plans of 2–3 tasks each, targeting ~50% context per plan to stay in Claude's "peak quality" zone. Builds an explicit dependency graph (each task records `needs`/`creates`), assigns wave numbers, and prefers vertical slices for parallelism. Each task has four required fields: `<files>` (exact paths), `<action>` (specific instructions including what to avoid and why), `<verify>` (runnable command), `<done>` (acceptance criteria). Derives `must_haves` (truths, artifacts, key_links) using strict goal-backward methodology. Honors locked CONTEXT.md decisions even when research suggests alternatives. Produces `NN-NN-PLAN.md` files with XML task blocks plus YAML frontmatter consumed by every downstream agent.

**gsd-plan-checker** — Static plan auditor that runs after the planner and before the executor. Goal-backward verification of plans (vs codebase): checks seven dimensions — requirement coverage, task completeness (every auto task has files/action/verify/done), dependency correctness (no cycles, valid waves), key-links planned (artifacts wired, not just created), scope sanity (≤3 tasks/plan, ≤8 files), must-haves derivation (user-observable truths, not "bcrypt installed"), and context compliance (locked CONTEXT.md decisions implemented, deferred ideas excluded). Returns either VERIFICATION PASSED or a structured YAML issue list with severities (blocker/warning/info), which the planner consumes in revision mode.

**gsd-executor** — Implements one plan atomically per spawn. Reads must-haves from frontmatter, executes tasks in order, commits each task individually with a strict format (`feat({phase}-{plan}): description`), never `git add .` or `-A`. Has four codified deviation rules: Rule 1 auto-fixes bugs, Rule 2 auto-adds missing critical functionality (validation, auth, indexes), Rule 3 auto-fixes blockers (missing deps, broken imports), Rule 4 stops and asks for architectural changes (new tables, new services). Auth errors are gates not failures (returns checkpoint). After all tasks, writes `NN-NN-SUMMARY.md` with frontmatter, files-changed list, decisions, and explicit deviation reports. Performs a self-check (file existence + commit-hash existence) before updating STATE.md and final-committing.

**gsd-verifier** — The phase's truth-teller. Goal-backward verification of the codebase (vs plans). Critical mindset: do NOT trust SUMMARY.md self-reports. Walks the must-haves three levels deep — exists? substantive (lines, contains)? wired (imports + usage)? Verifies key links explicitly (component → API via fetch, API → DB via query, etc.). Scans for anti-patterns (TODO/FIXME, `return null` stubs, console-log-only handlers). Distinguishes between automated PASS, programmatic-but-needs-human (visual, real-time), and outright gaps. Produces `NN-VERIFICATION.md` with a YAML `gaps:` block that `/gsd:plan-phase --gaps` can directly consume to build a closure plan. Supports re-verification mode (regression checks on previously-passed items).

**gsd-integration-checker** — Cross-phase wiring verifier, used at milestone boundaries. Core principle: existence ≠ integration. Builds an exports/imports map across phases, then verifies APIs are consumed (not orphaned), forms submit to handlers, components call the routes they should, and protected routes actually call auth helpers. Structures findings as `connected/orphaned/missing` and traces full E2E paths (Component → API → DB → Response → Display), reporting break points with file paths and line numbers.

**gsd-debugger** — Scientific-method debugging agent with persistent state under `.planning/debug/`. Mandatory falsifiability: every hypothesis must be testable, no "something is wrong with state" allowed. Maintains an immutable Symptoms section, append-only Eliminated and Evidence sections, and an OVERWRITE Current Focus section so a `/clear` mid-investigation can resume perfectly. Operates in three modes: interactive, find-root-cause-only (returns diagnosis to a `--gaps` flow), and find-and-fix (full cycle ending with archive to `.planning/debug/resolved/`). Codifies cognitive-bias countermeasures (confirmation, anchoring, availability, sunk cost) and explicit "when to restart" criteria.

### 1.3 Project foundation

The project was initialized on 2026-02-11 against an existing `backend/app/market/` market data subsystem (~500 lines, 8 modules, 73 passing tests for GBM simulator, PriceCache, MarketDataSource interface, Massive client, factory selector, and SSE stream router). The vision in `.planning/PROJECT.md` is explicit: a Bloomberg-aesthetic AI-powered trading workstation with live SSE prices, simulated $10,000 portfolio trading, and a chat-driven AI copilot that auto-executes trades, all served from a single Docker container on port 8000 with no auth.

Requirements were enumerated in `.planning/REQUIREMENTS.md` as **62 v1 requirements** across 12 categories: DB (4), PORT (8), WATCH (4), CHAT (8), APP (4), UI (4), FE-WATCH (5), FE-CHART (4), FE-TRADE (4), FE-CHAT (5), FE-RT (3), PKG (6), TEST (3). Each requirement has a stable ID (e.g. `PORT-03`, `FE-CHART-04`) and the file's "Traceability" table maps every ID to exactly one phase — a hard rule enforced by the roadmapper. v2 requirements (candlestick OHLCV, RSI/MACD, news feed, Terraform, CI/CD) are tracked but explicitly out of scope. Out-of-scope items have justifications: limit orders triple complexity, mobile-first conflicts with data-density, OAuth adds zero value for a single-user demo.

`.planning/ROADMAP.md` lays out a 10-phase build with explicit dependency arrows (Phase 4 needs 1+2+3, Phase 5 needs 2+3+4, Phase 7 needs 6, etc.). Phases 2 and 3 are flagged as parallel-eligible; Phases 7/8/9 can overlap once 6 completes. Each phase carries 2–5 observable success criteria written user-style ("User can buy shares at current market price") and a roll-up of which v1 IDs it satisfies. Final delivery metrics (in STATE.md) record 15 total plans across the 10 phases, 60 total minutes of execution time, and 100% requirement coverage at completion.

The `.planning/codebase/` map (six files) and `.planning/research/` map (five files) lock in architectural decisions before any new code is written. STACK.md mandates aiosqlite ≥0.22.0 (async SQLite, no ORM), litellm ≥1.78.0 (with the `extra_body` workaround for OpenRouter structured outputs), Next.js 16 with `output: 'export'`, Lightweight Charts 5.1.0 for streaming canvas charts, Recharts 3.7.0 for treemap/area charts, Tailwind CSS 4 (CSS-first config via `@theme`), and Zustand 5 for state. CONVENTIONS.md fixes naming (snake_case for Python files/functions, PascalCase classes, factory functions named `create_*`), mandates Ruff with line-length 100, requires `from __future__ import annotations` at the top of every Python module, and bans bare `except:`. ARCHITECTURE.md documents the abstraction-first pattern (PriceCache + MarketDataSource ABC), the closure-based router-factory pattern already in `app/market/stream.py`, and the lifespan-context-manager wiring pattern that all subsequent phases must follow.

PITFALLS.md identifies seven critical traps with phase mappings: (1) SQLite "database is locked" under concurrent async writes (Phase 1 must enable WAL mode + busy_timeout=5000 + isolation_level=None), (2) LiteLLM stripping `response_format` for OpenRouter models (Phase 5 must use `extra_body`), (3) SSE buffering through Docker networking (verify in Phase 10), (4) Next.js static export breaking with API routes (Phase 6), (5) Lightweight Charts memory leaks from improper React lifecycle (Phase 7), (6) Docker multi-stage build producing broken venvs (Phase 10 needs `UV_LINK_MODE=copy`), (7) LLM auto-execution without validation (Phase 5 must reuse Phase 2's validation pipeline). Every one of these later shows up as a key decision recorded in STATE.md.

### 1.4 Phase-by-phase build

#### Phase 01 — Database Foundation

**Domain research findings** (`01-RESEARCH.md`, HIGH confidence). The phase needed only one new dependency: `aiosqlite>=0.22.0`. Research locked in four critical configuration decisions: open the DB with `isolation_level=None` (true autocommit, avoids the upgrade-deadlock pitfall where two implicit transactions both try to promote from reader to writer); set `db.row_factory = aiosqlite.Row` for dict-like column access; configure `PRAGMA journal_mode=WAL` (persistent across connections, enables concurrent readers + 1 writer), `PRAGMA busy_timeout=5000`, and `PRAGMA foreign_keys=ON`; use a single shared connection (aiosqlite serializes through an internal background-thread queue, so multi-coroutine contention is impossible). Schema is initialized with `CREATE TABLE IF NOT EXISTS` (idempotent), and seed data uses `INSERT OR IGNORE` for the watchlist (UNIQUE constraint protects against duplicates) and check-then-insert for the user (preserves modified cash balance). The research explicitly flagged six pitfalls, including the `db/finally.db` + `*.db-wal` + `*.db-shm` patterns missing from `.gitignore`.

**Plan** (`01-01-PLAN.md`, single plan, 2 tasks, autonomous). Task 1 creates the four-file `backend/app/db/` module (`__init__.py`, `connection.py`, `schema.py`, `seed.py`) and updates `.gitignore`. Task 2 creates the four-file `backend/tests/db/` test suite (`conftest.py` with `tmp_path`-based isolated fixtures, plus `test_schema.py`, `test_seed.py`, `test_connection.py`). Must-haves frontmatter spelled out exactly four observable truths, seven required artifacts with `min_lines` constraints, and three key links (`init_db calls create_tables`, `init_db calls seed_default_data`, `__init__ re-exports init_db/close_db`).

**Execution & files produced** (`01-01-SUMMARY.md`, 2-min execution). Two atomic commits: `b8f54b5` (feat) and `9df628d` (test). Created 9 files, modified `backend/pyproject.toml` (added `aiosqlite`) and `.gitignore`. 14 new tests joined the existing 73 market-data tests for an 87/87 green regression. Self-check passed.

**Issues found & resolved during verification**. Phase 01 verification (`01-VERIFICATION.md`) returned `passed` with score 4/4 truths verified, no anti-patterns, all three key links wired (e.g. line 29 of `connection.py` confirmed `await create_tables(db)`). The verifier additionally performed a live integration check: created a temp DB, modified cash to $7,500, re-initialized, and confirmed the modified balance was preserved (not reset to $10,000). **Zero issues found.** This was the cleanest phase of the build.

**Outcome**: All 4 v1 DB requirements satisfied; foundation established for every subsequent backend phase.

#### Phase 02 — Portfolio & Trade Execution

**Domain research findings** (`02-RESEARCH.md`, HIGH confidence). With the DB layer using `isolation_level=None`, multi-statement trade execution must wrap operations in explicit `BEGIN`/`COMMIT`/`ROLLBACK` for atomicity. Two critical patterns surfaced: (1) compute weighted-average cost at the SQL level via `ON CONFLICT(user_id, ticker) DO UPDATE SET avg_cost = (positions.avg_cost * positions.quantity + ? * ?) / (positions.quantity + ?)` rather than Python-side, eliminating a read-modify-write race; (2) the snapshot background task should use `asyncio.create_task()` with start/stop lifecycle methods (matching the existing market-data source pattern), NOT FastAPI's request-scoped `BackgroundTasks`. The actual lifespan wiring belongs to Phase 4. Service functions must take `(db, price_cache)` as explicit dependency-injection arguments — no globals.

**Plan** (split into two plans). `02-01-PLAN.md` covers the service layer — Pydantic v2 models (`TradeRequest`, `TradeResponse`, `PositionResponse`, `PortfolioResponse`, `SnapshotResponse`, `PortfolioHistoryResponse`), `execute_trade`, `get_portfolio`, `get_portfolio_history`, plus 20 unit tests. `02-02-PLAN.md` covers the route factory `create_portfolio_router(db, price_cache)`, the snapshot background task module (`record_snapshot`, `start_snapshot_task`, `stop_snapshot_task`), and 16 HTTP-level + snapshot tests using `httpx.AsyncClient` + `ASGITransport`.

**Execution & files produced**. Plan 02-01 (3 min, commits `94f42a4` feat + `f98ff1f` test) created `backend/app/portfolio/{__init__,models,service}.py` plus three test files. Plan 02-02 (3 min, single combined commit `475db6e` because sandbox restrictions prevented separating per-task commits) created `backend/app/portfolio/snapshots.py`, `backend/app/routes/portfolio.py`, and snapshot/route tests. Notable concrete decisions logged: floating-point dust threshold of `0.0001` for position deletion on full sell (prevents leftover zero-quantity rows from float math); price fallback to `avg_cost` when `price_cache` has no current price (graceful startup); immediate `await record_snapshot(...)` after each trade (real-time P&L chart accuracy); background loop wraps each iteration in try/except with logging so one failure doesn't kill the periodic task.

**Issues found & resolved during verification**. Phase 02 verification (`02-VERIFICATION.md`) returned `passed` with 19/19 truths verified across both plans. **Zero anti-patterns.** Two minor execution-time issues were noted in the SUMMARY but auto-resolved without user intervention: (a) ruff I001 import-ordering lint failure in a test file, fixed automatically with `ruff check --fix`; (b) Plan 02-01 Task 1 commit was bundled with the parallel watchlist plan's commit `94f42a4` due to concurrent execution — code itself was verified correct. Total tests: 36 new (20 service + 5 snapshot + 11 route), 139/139 full-suite green.

**Outcome**: All 8 v1 PORT requirements satisfied; trade execution + portfolio valuation complete.

#### Phase 03 — Watchlist API

**Domain research findings** (`03-RESEARCH.md`, HIGH confidence). The phase is straightforward CRUD with one critical addition: changes must propagate to the live `MarketDataSource` (added tickers stream prices, removed tickers stop). Research mandated the closure-based router factory (matching the existing `create_stream_router` pattern) over FastAPI's `Depends()` system for consistency. New dev dependency identified: `httpx` should be promoted from transitive to explicit `[project.optional-dependencies] dev`.

**Plan** (single plan `03-01-PLAN.md`, 2 tasks, autonomous). Task 1: models + service layer + service unit tests. Task 2: router + HTTP tests. The router factory takes `(db, price_cache, market_data_source)` and wires GET (enriches with `price_cache.get(ticker)`), POST (calls `service.add_ticker` then `await market_data_source.add_ticker(ticker)`), DELETE (mirror).

**Execution & files produced** (3 min, commits `94f42a4` feat + `1e15e71` feat). Created the 8-file `backend/app/watchlist/` + `backend/tests/watchlist/` tree. Service functions are pure async (not classes), case-normalize tickers via `ticker.upper().strip()` (so `" pypl "` matches seeded `AAPL`), and raise `HTTPException(409)` on `sqlite3.IntegrityError` and `HTTPException(404)` when `cursor.rowcount == 0`. Test conftest established a `MockMarketDataSource` with `added`/`removed` lists for assertion — this pattern was reused throughout subsequent phases.

**Issues found & resolved during verification**. Phase 03 verification (`03-VERIFICATION.md`) returned `passed` with 6/6 truths verified, all three key links (`router.py → service.py`, `router.py → market/interface.py`, `router.py → market/cache.py`) confirmed wired. **Zero anti-patterns. Zero issues.** 16 new tests, 139/139 regression green.

**Outcome**: All 4 v1 WATCH requirements satisfied; watchlist CRUD + market-data sync ready to be mounted in Phase 4.

#### Phase 04 — App Assembly

**Domain research findings** (`04-RESEARCH.md`, HIGH confidence). The lifespan context manager is the single point of resource management; FastAPI's older `on_startup`/`on_shutdown` events are not called when `lifespan=` is provided. SPA static serving for the eventual Next.js export requires a custom `SPAStaticFiles` subclass of `starlette.staticfiles.StaticFiles` that catches 404s and falls back to `index.html`, and the static mount must come last so API routes take priority. New dev dependency identified: `asgi-lifespan` for testing the full app with lifespan events via `LifespanManager` + `httpx.AsyncClient`.

**Plan** (single plan `04-01-PLAN.md`, 2 tasks, autonomous). Task 1: `main.py` (lifespan wiring), `static_files.py` (SPAStaticFiles subclass), placeholder `static/index.html`. Task 2: 6 integration tests using `LifespanManager` to exercise the full assembled app — health, watchlist loaded, portfolio initial, trade through assembled app, static index, SPA fallback.

**Execution & files produced** (4 min, commits `df3b0b5` feat + `b643719` test). Created `backend/app/main.py`, `backend/app/static_files.py`, `backend/static/index.html`, `backend/tests/test_app.py`; modified `backend/app/market/stream.py` and `backend/pyproject.toml`.

**Issues found & resolved during verification**. Phase 04 had **three real bugs** discovered during execution and fixed inline as Rule-1/Rule-3 deviations (all logged in `04-01-SUMMARY.md` and verified clean in `04-VERIFICATION.md`):

| # | Rule | Bug | Root cause | Fix |
|---|------|-----|------------|-----|
| 1 | Rule 1 (bug) | `GET /api/watchlist` returned HTML instead of JSON | Module-level `app.mount("/", SPAStaticFiles(...))` registered the catch-all before API routers (which are added during lifespan), so the catch-all intercepted `/api/*` paths | Moved the static mount **into the lifespan**, after all `include_router` calls. API routes are now checked first. Located in `backend/app/main.py` lines 51–54. |
| 2 | Rule 1 (bug) | Route handler accumulation across test runs | `backend/app/market/stream.py` had a module-level `router = APIRouter(...)`. Each call to `create_stream_router()` added a duplicate route handler to the shared router object | Moved `router = APIRouter(...)` **inside the factory function** so each call creates a fresh router. |
| 3 | Rule 3 (blocking) | Tests failed with `ModuleNotFoundError: No module named 'httpx'` | `httpx` was a transitive dependency that got removed during `uv sync` | Added `httpx>=0.28.1` to `[project.optional-dependencies] dev` in `backend/pyproject.toml` |

A separate process gripe was logged: `uv add --dev` creates a `[dependency-groups]` section instead of adding to `[project.optional-dependencies] dev`, so the dev dep was added manually both for `asgi-lifespan` and `httpx`. The verifier confirmed `passed`, 5/5 truths, with two human-verification items flagged (uvicorn process startup + browser rendering, and SSE stream connectivity through real HTTP — neither testable with `LifespanManager`). 145/145 tests green.

**Outcome**: Single FastAPI app starts, initializes everything in lifespan order (DB → PriceCache → MarketDataSource → load watchlist → start streaming → start snapshots → mount routers → mount static), serves all routes on port 8000. APP-01 through APP-04 satisfied.

#### Phase 05 — LLM Chat Integration

**Domain research findings** (`05-RESEARCH.md`). The critical finding was Pitfall #2 from project research: LiteLLM's `supports_response_schema` returns `False` for OpenRouter models, silently stripping `response_format` from the request. The documented workaround (LiteLLM GitHub issues #10465 and #13438) is to pass `response_format` via `extra_body` to bypass the provider-capability check. Defensive JSON parsing is mandatory: try `model_validate_json` first, fall back to a plain message response on malformed output. Trade auto-execution must reuse the Phase 2 validation pipeline (Pitfall #7) — never bypass `execute_trade`'s cash/share checks.

**Plan** (split into two plans). `05-01-PLAN.md`: LLM service layer — Pydantic schemas (`TradeAction`, `WatchlistAction`, `ChatLLMResponse`, `ChatRequest`, `TradeResult`, `WatchlistResult`, `ChatResponse`), `build_system_prompt` with live portfolio context, `get_mock_response` (keyword-matched deterministic responses for `LLM_MOCK=true`), `process_chat_message` orchestrator, chat-history persistence, plus 18 unit tests. `05-02-PLAN.md`: `create_chat_router` factory wiring `POST /api/chat`, mounted in `main.py`, plus 8 HTTP-level tests.

**Execution & files produced**. Plan 05-01 (4 min, commits `8e44ca1` + `9eb79ae`): created `backend/app/llm/{__init__,models,prompt,mock,service}.py` plus tests. Plan 05-02 (3 min, commits `1bdadac` + `81c90a8`): created `backend/app/llm/router.py` and `backend/tests/llm/test_chat_routes.py`. Key decisions: error collection pattern (each trade/watchlist action executes independently inside a try/except, failures become `TradeResult(status="failed", error=...)` entries in the response rather than HTTP errors); no try/except in the router endpoint handler (`process_chat_message` always returns a `ChatResponse`); `record_snapshot` called when any trade in the response succeeded; chat history loads last 20 messages for LLM context (rolling window cap from PITFALLS).

**Issues found & resolved during verification**. Two ruff lint issues auto-fixed during Plan 05-02 (Rule 1):

| # | Rule | Issue | Fix | File |
|---|------|-------|-----|------|
| 1 | Rule 1 (bug) | Adding `create_chat_router` import broke alphabetical ordering (ruff I001) | Reordered imports alphabetically | `backend/app/main.py` |
| 2 | Rule 1 (bug) | Pre-existing extra blank line between import block and first constant (ruff I001) | Removed extra blank line | `backend/tests/db/test_schema.py` |

Phase 05 verification (`05-VERIFICATION.md`) returned `passed` with 11/11 truths verified, including the high-risk ones: Truth 2 confirmed `acompletion` is called with `extra_body` containing `response_format` and provider order; Truth 3 confirmed `parse_llm_response` tries `model_validate_json` then falls back to plain message; Truth 11 confirmed `record_snapshot` is called when any trade succeeded. **Zero anti-patterns.** All 26 LLM tests run in mock mode (no API key needed). Total: 26 new LLM tests, 171/171 full-suite green.

**Outcome**: All 8 v1 CHAT requirements satisfied. End-to-end backend complete — `/api/chat` runs structured-output LLM calls, auto-executes validated trades, applies watchlist changes, persists everything, and respects `LLM_MOCK=true`.

#### Phase 06 — Frontend Foundation

**Domain research findings** (`06-RESEARCH.md`, HIGH confidence). Stack locked: Next.js 16.1.x with `output: 'export'` in `next.config.ts`, React 19.2.x, Tailwind CSS 4 (CSS-first config via `@theme` in `globals.css`, no `tailwind.config.js`), Zustand 5 for state. Research warned explicitly against React Context for SSE-fed state (re-renders all consumers on any state change — disastrous at 500ms tick rates) and against Tailwind v3 (create-next-app installs v4 by default and the @theme syntax is cleaner for the custom dark palette). Native `EventSource` is sufficient for SSE — the browser handles reconnection automatically, no custom retry logic needed.

**Plan** (single plan `06-01-PLAN.md`, 2 tasks). Task 1: scaffold the Next.js project, configure static export, lay out the CSS Grid terminal layout with five panel placeholders. Task 2: Zustand stores, SSE EventSource hook, portfolio fetch helper, Header with live portfolio data + colored connection dot.

**Execution & files produced** (3 min, commits `f32a9d1` feat + `d08123f` feat). Sixteen files created/modified, including `frontend/next.config.ts`, `frontend/src/app/globals.css`, `frontend/src/stores/{price-store,portfolio-store}.ts`, `frontend/src/hooks/use-price-stream.ts`, `frontend/src/lib/api.ts`, `frontend/src/components/layout/{Header,TerminalGrid}.tsx`, `frontend/src/components/ui/ConnectionDot.tsx`, and four placeholder panel components. Concrete patterns established: Zustand selector pattern (`usePriceStore((s) => s.field)`) so each component subscribes only to its own state slice; CSS Grid `gap-px` with `bg-terminal-border` to create 1px borders between panels for the Bloomberg look; `Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'})` for money formatting.

**Issues found & resolved during verification**. Phase 06 has no separate `06-VERIFICATION.md` file — it is the only phase in the build without one. The SUMMARY documents one auto-fixed Rule 3 (blocking) deviation:

| # | Rule | Issue | Root cause | Fix |
|---|------|-------|------------|-----|
| 1 | Rule 3 (blocking) | `git add frontend/src/lib/api.ts` was being silently ignored | The root `.gitignore` had a Python-style `lib/` rule (from a generic Python template) which caught `frontend/src/lib/` even though the user wanted that directory tracked | Added `!frontend/src/lib/` negation to `.gitignore` |

The build was self-verified by `npm run build` producing `frontend/out/index.html` successfully — i.e. the static export pipeline worked end-to-end. No `06-VERIFICATION.md` was created, presumably because the next phase (07) immediately built on top and its verification implicitly exercised 06's primitives. (This is a documented gap in the artifact set.)

**Outcome**: Dark terminal layout shell renders, SSE stream + portfolio fetch wired into Zustand, all four panel placeholders ready for replacement. UI-01 through UI-04 + FE-RT-01 through FE-RT-03 satisfied.

#### Phase 07 — Watchlist & Price Display

**Domain research findings** (`07-RESEARCH.md`). For the price-flash animation, hand-rolled keyframes (`flash-up`, `flash-down`, 500ms fade) triggered by React **key remounting** (`key={ticker + timestamp}`) is cleaner than a `useEffect`-driven class-toggle dance. For sparklines, a hand-rolled SVG polyline beats pulling in another charting library. Price history must be capped (5000 points per ticker) to bound memory. For the main chart, lightweight-charts v5 changed its API from v4: use `chart.addSeries(LineSeries)` not the deprecated `chart.addLineSeries()`, and time values must be cast to the branded `UTCTimestamp` type. The chart instance must live in `useRef` with a cleanup function calling `chart.remove()` (Pitfall #5 from project research).

**Plan** (split into two plans). `07-01-PLAN.md`: extend `price-store.ts` with `priceHistory` accumulation, create `watchlist-store.ts` (CRUD + selectedTicker), create `Sparkline.tsx` and `PriceCell.tsx`, replace the `WatchlistPanel.tsx` placeholder. `07-02-PLAN.md`: install `lightweight-charts@5.1.0`, replace `ChartPanel.tsx` placeholder with full canvas chart.

**Execution & files produced**. Plan 07-01 (2 min, commits `8a56b5b` + `d966e1c`): full watchlist with flash animations, sparklines, ticker selection, add/remove controls. Plan 07-02 (1 min, commit `b4f71ac`): canvas chart with `ResizeObserver` for responsive sizing, dark terminal palette (`#1a1a2e` background, `#209dd7` line color), full-history `setData` on each update.

**Issues found & resolved during verification**. Phase 07 logged one auto-fixed Rule-1 deviation in Plan 07-02:

| # | Rule | Issue | Root cause | Fix |
|---|------|-------|------------|-----|
| 1 | Rule 1 (bug) | TypeScript compilation failed with `UTCTimestamp` type incompatibility | `PriceHistoryPoint.time` is `number` but lightweight-charts v5 expects the branded `UTCTimestamp` nominal type | Imported `UTCTimestamp` and cast via `.map(p => ({ time: p.time as UTCTimestamp, value: p.value }))`. Located in `frontend/src/components/panels/ChartPanel.tsx`. `npx tsc --noEmit` then passed clean. |

Phase 07 verification (`07-VERIFICATION.md`) returned `passed` with 8/8 truths verified. **Zero anti-patterns** (a `return null` guard in `Sparkline.tsx` line 10 and the input `placeholder` attribute in `WatchlistPanel.tsx` were both noted as Info-severity false positives — the first is a valid insufficient-data guard, the second is the standard HTML attribute). Five human-verification items flagged (price-flash visual smoothness, sparkline rendering quality, chart interactivity, full CRUD flow including remove-while-selected edge cases, and connection-status indicator behavior).

**Outcome**: All 7 v1 watchlist + chart frontend requirements satisfied (FE-WATCH-01..05, FE-CHART-01..02). The watchlist now flashes on price ticks, accumulates sparklines from SSE, and clicking a ticker drives the main chart panel.

#### Phase 08 — Portfolio Visualizations & Trading

**Domain research findings** (`08-RESEARCH.md`). Recharts 3.7.0 for the treemap and P&L line chart. Critical: use the Recharts Treemap with a custom `content` prop renderer (v3 pattern) rather than the deprecated `<Cell>` component. P&L color function: linear RGB interpolation from red (`#ef4444`) through neutral gray (`#484f58`) to green (`#22c55e`), clamped at ±10%. The PnlChart component should follow the **exact same lifecycle pattern** as `ChartPanel.tsx` (create-once in `useEffect` with empty deps, sync data in a separate effect) — re-establishing the chart-instance discipline from Phase 07.

**Plan** (split into two plans). `08-01-PLAN.md`: install Recharts, extend `portfolio-store.ts` with `Position`/`Snapshot` types, `positions` array, `snapshots`, `executeTrade` action, `fetchHistory`. Create `Heatmap.tsx` (Recharts Treemap with custom P&L-colored content) and `PnlChart.tsx` (lightweight-charts AreaSeries in accent yellow `#ecad0a`). `08-02-PLAN.md`: create `PositionsTable.tsx` (with `Intl.NumberFormat` currency formatting and conditional green/red coloring), `TradeBar.tsx` (with `selectedTicker` pre-fill from watchlist store, instant buy/sell, inline `tradeError` display in red), wire all components into the page grid with `fetchHistory` on mount.

**Execution & files produced**. Plan 08-01 (1 min, commits `6a05d16` + `710b2dc`): extended portfolio store, Heatmap, PnlChart. Plan 08-02 (2 min, commits `211a17c` + `99d08db`): PositionsTable, TradeBar, rewired PortfolioPanel to stack Heatmap (top half) + PnlChart (bottom half), updated page.tsx to add `fetchHistory` to mount lifecycle. Pattern decision: trade-error handling uses `usePortfolioStore.getState()` to check `tradeError` after the async `executeTrade` resolves (avoids stale-closure bugs).

**Issues found & resolved during verification**. Phase 08 verification (`08-VERIFICATION.md`) returned `passed` with 5/5 truths verified, all key links wired (PortfolioStore ↔ /api/portfolio, /api/portfolio/history, /api/portfolio/trade; TradeBar ↔ executeTrade; TradeBar ↔ selectedTicker pre-fill). **Zero issues during execution itself.** The verifier flagged a `return null` in `Heatmap.tsx:26` as Info-severity (intentional SVG rendering guard for tiny rectangles) — this would later prove to be **incomplete**, see Phase 10 below where a related null-guard bug surfaced.

5 human-verification items: heatmap visual layout balance, P&L chart real-time updates after trade, end-to-end "no confirmation dialog" trade flow, error-message clarity for insufficient cash/shares, currency formatting/color contrast.

**Outcome**: All 6 v1 viz + trade frontend requirements satisfied (FE-CHART-03..04, FE-TRADE-01..04). Frontend now has a complete trading workstation minus chat.

#### Phase 09 — Chat Interface

**Domain research findings** (`09-RESEARCH.md`). The chat panel needs a `useChatStore` Zustand store that handles **cross-store refresh** — after the AI returns successful trades, call `usePortfolioStore.getState().fetchPortfolio()` and `fetchHistory()`; after successful watchlist changes, call `useWatchlistStore.getState().fetchWatchlist()`. Optimistic UI: append the user's message immediately before the API call resolves. Smart auto-scroll: only scroll to bottom when the user is already within 100px of bottom (don't yank them away if they've scrolled up to read history). Frontend TypeScript types must mirror backend Pydantic models exactly — the contract is `TradeResult { status, ticker, side, quantity?, price?, total?, error? }` and `WatchlistResult { status, ticker, action, error? }`.

**Plan** (single plan `09-01-PLAN.md`, 2 tasks). Task 1: `chat-store.ts` with `messages`, `sending`, `error`, `sendMessage` (POST /api/chat + cross-store refresh). Task 2: replace `ChatPanel.tsx` placeholder with full UI — collapsible sidebar (vertical "AI Chat" text via `writing-mode: vertical-lr` when collapsed), distinct user (right-aligned, purple-tinted) vs assistant (left-aligned, dark) bubbles, inline `TradeCard` and `WatchlistCard` action confirmations, three-dot pulsing "Thinking..." loading state.

**Execution & files produced** (1 min, commits `49ad120` + `a968fc6`). Two files: `frontend/src/stores/chat-store.ts` (106 lines) and `frontend/src/components/panels/ChatPanel.tsx` (187 lines).

**Issues found & resolved during verification**. Phase 09 verification (`09-VERIFICATION.md`) returned `passed` with 8/8 truths verified. **Zero anti-patterns. Zero issues.** Contract verification confirmed the frontend `TradeResult` and `WatchlistResult` types match `backend/app/llm/models.py` exactly. TypeScript check + static build both passed. Four human-verification items: visual chat panel layout, collapse/expand interaction, send-message + loading-state animation timing, inline action card rendering with a live backend.

**Outcome**: All 5 v1 chat frontend requirements satisfied (FE-CHAT-01..05). The full UI is now feature-complete; only packaging remains.

#### Phase 10 — Packaging & Testing

**Domain research findings** (`10-RESEARCH.md`). The hot-button pitfalls were Pitfall #6 (Docker venv path mismatch — needs `ENV UV_LINK_MODE=copy` because uv's default hardlinks fail across Docker stage boundaries) and Pitfall #3 (SSE buffering through Docker networking — verify with curl after build). Recommended Dockerfile pattern: Stage 1 `node:20-slim` runs `npm run build` to produce `frontend/out/`, Stage 2 `python:3.12-slim` does `uv sync --locked` with `--mount=type=cache,target=/root/.cache/uv` for build caching, copies `--from=frontend-builder /app/frontend/out ./static`, installs `curl` for the Docker healthcheck, and `CMD`s straight into `/app/.venv/bin/uvicorn` (no shell activation). Playwright 1.58.2 with the matching `mcr.microsoft.com/playwright:v1.58.2-noble` Docker image. E2E tests must run with `workers: 1` because all tests share a single backend database.

**Plan** (split into two plans). `10-01-PLAN.md`: Dockerfile, .dockerignore, docker-compose.yml, .env.example, four start/stop scripts (`scripts/start_mac.sh`, `stop_mac.sh`, `start_windows.ps1`, `stop_windows.ps1`). `10-02-PLAN.md`: Playwright project setup (package.json, tsconfig, playwright.config.ts), 5 spec files covering 14 tests (fresh-start: 4, watchlist: 2, trading: 3, portfolio: 2, chat: 3), `docker-compose.test.yml`, plus a Task 3 human-verification checkpoint.

**Execution & files produced**. Plan 10-01 (2 min, commits `ff8abde` feat + `57fffd8` feat): clean execution, no deviations. Plan 10-02 was the longest plan in the entire project at **26 minutes** — the trend recorded in STATE.md notes "E2E testing required iterative selector fixes." Three commits: `0ded356` (test), `05842ba` (fix), `7328c2d` (feat).

**Issues found & resolved during verification**. Phase 10 had the most issues of any phase in the build, all surfaced during E2E test execution as Rule-1 and Rule-3 deviations:

| # | Rule | Issue | Root cause | Fix |
|---|------|-------|------------|-----|
| 1 | Rule 1 (bug) | Heatmap component crashed at runtime: `Cannot read properties of undefined (reading 'toFixed')` after a trade was executed | Recharts Treemap calls the `CustomContent` prop with a props object that does **not** always include the user-defined custom data fields (`pnl`, `pnlPercent`) during certain render phases — particularly during the initial layout pass before data has been fully wired. The Phase 08 implementation assumed those fields would always be present. | Added null-coalescing guards: `pnl ?? 0` and `pnlPercent ?? 0` inside the CustomContent renderer. Located in `frontend/src/components/portfolio/Heatmap.tsx`. Committed separately as `05842ba` for surgical isolation. |
| 2 | Rule 3 (blocking) | Multiple Playwright strict-mode violations: selectors resolved to multiple elements (two `$10,000.00` values for header Cash + Portfolio Value, two `<table>` elements because Recharts internals render tables, multiple "PYPL" text matches across components) | The initial test selectors used loose text/role matchers that worked in dev but failed strict-mode | Scoped all selectors using CSS class anchors: header cash uses `div.flex-col` with a `:has-text("Cash")` parent; positions table uses `table.w-full` to avoid Recharts internal tables; PriceCell rows use the `.group` class (which `PriceCell.tsx` already had on its root) to target individual watchlist rows; trade bar inputs use `placeholder="TICKER"` with `nth(1)` since the watchlist add-input is `nth(0)`. All 5 spec files + `playwright.config.ts` were updated. Committed as `7328c2d`. |
| 3 | (process) | Tests initially failed unpredictably with race conditions | All Playwright tests share a single backend database (one container), so default 5-worker parallelism caused interleaving writes | Set `workers: 1` in `playwright.config.ts` for serial execution |
| 4 | (versioning) | Plan specified Playwright 1.50.1 but the planner instructed "check npm for latest" | Latest at execution time was 1.58.2 | Used `@playwright/test@1.58.2` plus the matching `mcr.microsoft.com/playwright:v1.58.2-noble` image |
| 5 | (assertion style) | Tests asserted absolute `$10,000.00` for cash but tests sometimes ran on a non-fresh DB | Shared database across tests | Switched to **relative cash assertions**: capture the value before the trade, verify it changes after |

The Heatmap fix in particular was a real production bug — the Phase 08 verifier had marked the same `return null` in `Heatmap.tsx:26` as Info-severity, missing that `pnl` and `pnlPercent` could be undefined during Recharts internal render passes. Only running real Playwright traffic against a populated portfolio surfaced the crash.

Phase 10 verification (`10-VERIFICATION.md`) returned `passed` with 10/10 truths verified, all 17 required artifacts confirmed, all 11 cross-cutting key links wired (Dockerfile Stage 1 → frontend/out, Dockerfile Stage 2 → uv sync, docker-compose → named volume, Playwright config → BASE_URL, trading.spec.ts → TradeBar placeholder selectors, chat.spec.ts → mock.py response text, etc.). Notable wiring confirmations:
- `chat.spec.ts` assertions match `mock.py` MOCK_RESPONSES text **exactly**: "I can see your portfolio", "I've bought 5 shares of AAPL", "added PYPL to your watchlist".
- `trading.spec.ts` error-test regex `/Insufficient/i` matches the `ValueError("Insufficient cash"/"Insufficient shares")` raised by `backend/app/portfolio/service.py`.

**Three human-verification items remained**: visual application verification (real browser), full trading flow with cross-component state propagation, and live execution of all 14 Playwright tests against the running container.

**Outcome**: All 9 v1 packaging + testing requirements satisfied (PKG-01..06, TEST-01..03). Final tally: 14 E2E tests passing, 171 backend tests passing, all 62 v1 requirements satisfied, 100% mapped, project complete in 60 minutes of total Claude execution time across 15 plans and 10 phases.

---

## 2. Market Data Agent Track (Pre-GSD)

### 2.1 Track overview

The market data subsystem was the first substantive piece of FinAlly built end-to-end by Claude agents, and it was done before the GSD (Goal/Spec/Done) framework was introduced. Instead of a single agent producing the whole feature, the work was deliberately split into four sequential GitHub PRs, each opened by a Claude agent triggered through the `claude.yml` and `claude-code-review.yml` GitHub Actions workflows that landed in PR #1 (commit `678a538`). Those workflows wired `@claude` mentions on issues and PR comments into a Claude run with repo write access — that is the pipe through which every subsequent agent was invoked.

The macro-workflow was: design (PR #2) → implement (PR #4) → review (PR #5) → fix (PR #6) → demo (PR #7) → archive/summarise (commit `5594a85`). Each phase is a separate branch and a separate PR, with a separate Claude invocation, and each phase only consumes the documents produced by the previous phase. The agents communicated through markdown files committed under `planning/` (later moved to `planning/archive/`). Concretely: the design agent wrote `planning/archive/MARKET_DATA_DESIGN.md`; the implementer worked from that doc and produced `backend/app/market/`; the review agent ran the implementation, wrote `planning/archive/MARKET_DATA_REVIEW.md`; a fix agent consumed that review and produced patches; finally a demo agent built `backend/market_data_demo.py`, and a wrap-up commit moved the planning docs into `planning/archive/` and produced `planning/MARKET_DATA_SUMMARY.md`.

This is essentially a hand-rolled multi-agent pipeline, with humans (Ed Donner via merges) gating each step. Several patterns visible here — design-first, an explicit code-review pass, archival of superseded planning docs, and a small Rich-based demo as a smoke test — carry directly into the later GSD-framework agent work in the project. The track also exposed a number of failure modes (build config, lazy imports, mocking strategy) that the team subsequently codified into stricter contracts for downstream agents.

### 2.2 Design phase (PR #2)

The design agent ran on branch `claude/market-data-backend-design-eoSLj`. Commit `9df2c79` ("Add detailed market data backend design document") added a single 1,490-line file: `planning/MARKET_DATA_DESIGN.md` (now at `planning/archive/MARKET_DATA_DESIGN.md`). The agent did not touch any code in this phase — its only output was a contract that the implementation agent could execute against.

The design's central choice was a strategy pattern over an abstract `MarketDataSource` ABC, with two concrete implementations selected at runtime by an environment-variable-driven factory:

```
MarketDataSource (ABC)
  ├── SimulatorDataSource   (GBM, used by default)
  └── MassiveDataSource     (Polygon.io REST polling, used when MASSIVE_API_KEY is set)
        │
        ▼
   PriceCache  (thread-safe, in-memory, version counter)
        │
        ▼
   SSE stream (/api/stream/prices)  →  Frontend
```

The doc fixed nine specific decisions that shaped everything that followed:

- **Single shared `PriceCache`** (`backend/app/market/cache.py`) as the only writeable surface. Producers (simulator/poller) write; consumers (SSE, valuation, trade execution) read. This decouples producer cadence from consumer cadence — the simulator can tick at 500 ms, Massive can poll at 15 s, and SSE can drain at its own rate.
- **`threading.Lock` rather than `asyncio.Lock`** in the cache. The Massive REST client is synchronous and runs under `asyncio.to_thread(...)`, so the cache must be safe from a real OS thread, not just from coroutines.
- **Monotonic `version` counter** on the cache so the SSE generator can skip sends when nothing has changed, instead of re-serializing the full price dict every 500 ms.
- **Immutable, slotted `PriceUpdate` dataclass** (`backend/app/market/models.py`) with `frozen=True, slots=True`, exposing computed properties for `change`, `change_percent`, and `direction` — derived state can never go stale.
- **GBM math** in `simulator.py`: `S(t+dt) = S(t) * exp((mu - sigma^2/2)*dt + sigma*sqrt(dt)*Z)` with `dt ≈ 8.48e-8` (500 ms over 252 trading days × 6.5 h). Per-ticker `mu`/`sigma` (e.g., TSLA at sigma=0.50, V at 0.17) are kept in `seed_prices.py`.
- **Cholesky-decomposed correlation matrix** so tech tickers correlate at 0.6, finance at 0.5, and cross-sector at 0.3, with TSLA hard-wired to 0.3 against everything ("does its own thing").
- **Random shock events** (~0.1 % per tick per ticker, ±2–5 %) for visible drama without destabilizing the underlying GBM path.
- **Lazy import of `massive`** inside `MassiveDataSource.start()` and `_fetch_snapshots()` so simulator-only deployments would not need the package. (This decision was reversed in PR #6 — see 2.5.)
- **SSE over WebSockets**, with `retry: 1000\n\n` injected at stream start and `X-Accel-Buffering: no` to defeat proxy buffering, and an `await request.is_disconnected()` guard inside the generator loop.

The design also pre-specified the public re-exports (`PriceUpdate`, `PriceCache`, `MarketDataSource`, `create_market_data_source`, `create_stream_router`) and FastAPI lifespan integration, including a watchlist-coordination flow with the explicit edge case that a ticker with an open position must not be removed from the data source even if it is removed from the watchlist.

### 2.3 Implementation phase (PR #4)

The implementer agent ran on branch `claude/issue-3-20260210-1826`. Commit `395eaa7` ("feat: implement complete market data backend") was a single +1,626-line drop. `git show --stat 395eaa7` reveals the full inventory:

```
backend/README.md                              |  55 +
backend/app/__init__.py                        |   1 +
backend/app/market/__init__.py                 |  23 +
backend/app/market/cache.py                    |  75 +
backend/app/market/factory.py                  |  33 +
backend/app/market/interface.py                |  57 +
backend/app/market/massive_client.py           | 132 +
backend/app/market/models.py                   |  49 +
backend/app/market/seed_prices.py              |  48 +
backend/app/market/simulator.py                | 266 +
backend/app/market/stream.py                   |  86 +
backend/pyproject.toml                         |  54 +
backend/tests/__init__.py                      |   1 +
backend/tests/conftest.py                      |  11 +
backend/tests/market/__init__.py               |   1 +
backend/tests/market/test_cache.py             | 105 +
backend/tests/market/test_factory.py           |  81 +
backend/tests/market/test_massive.py           | 198 +
backend/tests/market/test_models.py            |  77 +
backend/tests/market/test_simulator.py         | 135 +
backend/tests/market/test_simulator_source.py  | 138 +
21 files changed, 1626 insertions(+)
```

The implementation track follows the design almost verbatim — the eight production modules under `backend/app/market/` correspond one-to-one with the file structure prescribed in section 1 of `MARKET_DATA_DESIGN.md`. The implementer also produced six test modules (`test_models.py`, `test_cache.py`, `test_simulator.py`, `test_simulator_source.py`, `test_factory.py`, `test_massive.py`) totalling roughly 90 tests, along with `pyproject.toml`, a `backend/README.md`, and a top-level `tests/conftest.py`.

The implementation strategy was straightforward "do exactly what the design says, with tests for each module". A few details worth noting:

- It honoured the lazy-import convention for `massive`, hiding `from massive import RESTClient` inside `start()` and `from massive.rest.models import SnapshotMarketType` inside `_fetch_snapshots()`.
- It implemented the SSE router as a factory `create_stream_router(price_cache)` that closes over the cache and registers `/prices` on a module-level `APIRouter` instance.
- `SimulatorDataSource.get_tickers` reached directly into the simulator's private `_tickers` list with `list(self._sim._tickers) if self._sim else []` — the design itself contained this exact line, and the implementer copied it.
- `pyproject.toml` declared `massive>=1.0.0` as a **core** runtime dependency, which contradicted the design's lazy-import rationale (the design said "students who don't have a Massive API key don't need the package installed at all"). This contradiction is what later forced the lazy imports to be torn out.
- The implementer also missed the `[tool.hatch.build.targets.wheel]` block, leaving `pyproject.toml` unbuildable.

The implementation was merged in commit `cdea3fb` (PR #4).

### 2.4 Code review phase (PR #5)

The review agent ran on branch `market-data-review`. Commit `7e823b6` added `planning/MARKET_DATA_REVIEW.md` (since archived to `planning/archive/MARKET_DATA_REVIEW.md`), 173 lines, no code changes. The reviewer ran the test suite and `ruff`, calculated coverage, and produced a structured assessment.

**Headline test result.** "73 tests collected, 68 passed, 5 failed." All five failures were in `test_massive.py`, all from the same root cause: the `massive` package was not installed in the test environment, so `patch("app.market.massive_client.RESTClient")` failed with `AttributeError` because `RESTClient` was never imported at module level (it was a lazy import). Three further tests that mocked `source._fetch_snapshots` directly still hit `asyncio.to_thread(self._fetch_snapshots)`, which in some cases tried to import the real `massive.rest.models`. The reviewer was careful to note that the bugs sit at the seam between the design's lazy-import policy and the test agent's mock targets — the production code logic was correct.

**Coverage:** 84 % overall, with `models.py`, `cache.py`, `interface.py`, `seed_prices.py`, and `factory.py` at 100 %; `simulator.py` at 98 %; `massive_client.py` at 56 % (expected, since real API methods can't run); and `stream.py` at 31 % — flagged as a real gap because SSE has no dedicated tests at all.

**Issues raised.** The review enumerated seven concrete issues with severity tags:

| # | Severity | Title | Location | Description |
|---|----------|-------|----------|-------------|
| 3.1 | High | Build configuration bug | `backend/pyproject.toml` | Missing `[tool.hatch.build.targets.wheel] packages = ["app"]`. `uv sync` fails with `ValueError: Unable to determine which files to ship inside the wheel`. **Blocks Docker builds and any fresh `uv sync`.** |
| 3.2 | Medium | Massive test fragility | `backend/tests/market/test_massive.py` | Five tests fail without the `massive` package installed. Two root causes: (a) `_poll_once` calls `asyncio.to_thread(self._fetch_snapshots)` which still routes through code that imports `massive.rest.models`; (b) `patch("app.market.massive_client.RESTClient")` targets a name that does not exist at module level because of lazy import. Reviewer's prescription: `create=True` on the patch, or restructure so tests work without the package. |
| 3.3 | Low | Wrong return-type annotation | `backend/app/market/stream.py:54` | `_generate_events` is annotated `-> None` but it is an async generator (`yield`s strings). Should be `-> AsyncGenerator[str, None]`. Misleads type-checkers but does not affect runtime. |
| 3.4 | Low | `version` property not under lock | `backend/app/market/cache.py` | `PriceCache.version` reads `self._version` without acquiring `self._lock`. Atomic on CPython with the GIL, but inconsistent with the rest of the class and a latent issue under the no-GIL build (PEP 703, 3.13t+). |
| 3.5 | Low | Private-state access across boundary | `backend/app/market/simulator.py:254` | `SimulatorDataSource.get_tickers` does `list(self._sim._tickers) if self._sim else []`, reaching into `GBMSimulator`'s private attribute. Should call a public method on the simulator. |
| 3.6 | Low | Module-level router instance | `backend/app/market/stream.py:16` | `router = APIRouter(...)` lives at module scope and `create_stream_router()` registers `/prices` on it via closure. Calling the factory twice (e.g., in tests) registers `/prices` twice — a latent footgun for testing. |
| 3.7 | Trivial | Unused imports in tests | `test_cache.py`, `test_factory.py`, `test_massive.py`, `test_simulator.py` | Five `ruff` warnings: unused `pytest`, unused `math`, unused `asyncio`. |

**Design observations.** The reviewer also called out three additional concerns that did not get filed as issues but are notable:

- **Missing SSE integration test.** `stream.py` has no dedicated test; an `httpx.AsyncClient` test against the FastAPI app would be straightforward.
- **No concurrent thread-safety test for `PriceCache`.** Lock usage looks correct by inspection but has not been exercised under contention.
- **No GBM test with all 10 default tickers.** Existing simulator tests use 1–2 tickers; a smoke test with the full default set would catch correlation-matrix issues (e.g., a non-PSD matrix breaking `np.linalg.cholesky`).
- **`DEFAULT_CORR` vs `CROSS_GROUP_CORR` naming confusion** in `seed_prices.py` — both are 0.3, but `DEFAULT_CORR` is defined and never referenced. The static method `_pairwise_correlation` returns `CROSS_GROUP_CORR` for both cross-sector and unknown-ticker cases. Behaviour is correct; naming is misleading.

**Verdict.** The reviewer separated must-fix (1: build config), should-fix (2: test mocks; 3: return type; 7: unused imports), and nice-to-have (5: public `get_tickers`; 6: SSE integration test; 8: correlation-constant cleanup). This explicit triage is what the next phase consumed.

### 2.5 Fix phase (PR #6)

The fix agent ran on branch `fix/market-data-review-items`. Commit `f89aa14` ("Fix all issues from market data code review") landed nine files changed, +60 / −15 lines. The agent walked the review's bullet list and produced a one-to-one mapping of issue → patch:

| Review item | Severity | Patch landed in `f89aa14` |
|---|---|---|
| 3.1 Build configuration bug | High | Added `[tool.hatch.build.targets.wheel] packages = ["app"]` to `backend/pyproject.toml`. |
| 3.2 Massive test fragility | Medium | New `backend/tests/market/conftest.py` (43 lines): autouse fixture that, on `ImportError`, builds stub `massive`, `massive.rest`, and `massive.rest.models` modules in `sys.modules` so `from massive import RESTClient` and `from massive.rest.models import SnapshotMarketType` resolve. Also added `source._client = MagicMock()` to four tests so `_poll_once`'s guard (`if not self._tickers or not self._client: return`) is satisfied before `_fetch_snapshots` is patched. The two `patch("app.market.massive_client.RESTClient")` call sites were updated to `patch("app.market.massive_client.RESTClient", create=True)`. |
| 3.3 Wrong return-type annotation | Low | In `backend/app/market/stream.py`, added `from collections.abc import AsyncGenerator` and changed `_generate_events`'s return type from `-> None` to `-> AsyncGenerator[str, None]`. |
| 3.5 Private-state access | Low | Added a public `get_tickers()` method to `GBMSimulator` returning `list(self._tickers)`, and changed `SimulatorDataSource.get_tickers` from `list(self._sim._tickers) if self._sim else []` to `self._sim.get_tickers() if self._sim else []`. |
| 4.3 Correlation constants | Low | Removed `DEFAULT_CORR = 0.3` from `backend/app/market/seed_prices.py` and updated the `CROSS_GROUP_CORR` comment to read "Between sectors / unknown tickers". |
| 3.7 Unused imports | Trivial | Stripped unused `pytest` from `test_cache.py` and `test_factory.py`, unused `math` and `pytest` from `test_simulator.py`, unused `asyncio` from `test_massive.py`. |

The commit message states "All 73 tests pass. Lint clean." Notably the agent did **not** address review items 3.4 (version property under lock — explicitly judged "minor concern given the current context") or 3.6 (module-level router footgun — latent only). That triage decision was kept implicit; the agent only acted on the "must" and "should" tiers, plus one "nice to have" (the `get_tickers` public method and the constant cleanup).

**The follow-up commit `6a2b36e` ("Remove lazy imports for massive package")** is the most instructive in the whole track. The fix in `f89aa14` had patched up the test mocking machinery — `create=True`, sys.modules stubs, manual `_client = MagicMock()` — to keep the *design's* lazy-import discipline alive. But that discipline contradicted the implementer's `pyproject.toml`, which declared `massive>=1.0.0` as a core runtime dependency. The agent on this commit (the same Claude Opus 4.6 instance) recognised the contradiction and inverted the original design decision rather than perpetuate the workaround:

```diff
 # backend/app/market/massive_client.py
-from typing import Any
+
+from massive import RESTClient
+from massive.rest.models import SnapshotMarketType

 class MassiveDataSource(MarketDataSource):
     ...
-    self._client: Any = None  # Lazy import to avoid hard dependency
+    self._client: RESTClient | None = None

 async def start(self, tickers: list[str]) -> None:
-    # Lazy import: only import massive when actually using real market data.
-    from massive import RESTClient
-
     self._client = RESTClient(api_key=self._api_key)
```

```diff
 # backend/app/market/factory.py
+from .massive_client import MassiveDataSource
+from .simulator import SimulatorDataSource

 if api_key:
-    from .massive_client import MassiveDataSource
     return MassiveDataSource(...)
 else:
-    from .simulator import SimulatorDataSource
     return SimulatorDataSource(...)
```

The same commit also **deleted the 43-line `tests/market/conftest.py` stub** that `f89aa14` had just introduced, and dropped `create=True` from the two `RESTClient` patches in `test_massive.py`. The commit body summarises the reasoning crisply: *"`massive` is a core dependency in pyproject.toml and will always be installed. Move imports to top level… remove the sys.modules stub conftest, and drop `create=True` from test patches. Tests now work naturally with the installed package."* Net diff: +8 / −57 — workaround code removed, real fix kept.

The lesson here is mechanical: a lazy-import pattern is only worth its complexity if the package is genuinely optional. As soon as it ships in the lockfile as a hard dep, the lazy import is dead weight that breaks naive mocking. The design agent's policy was sound *in isolation* but the implementer made it inconsistent with `pyproject.toml`, and the review caught the symptom (failing tests) before the contradiction was caught at the source.

PR #6 was merged as commit `5e65c50`.

### 2.6 Demo phase (PR #7)

The demo agent ran on branch `market-data-demo`. Commit `e20c56a` ("Add rich terminal demo for market data simulator") added a single Python file, `backend/market_data_demo.py` (272 lines), and added `rich` to `backend/pyproject.toml` as a dev dependency.

The script wires a `PriceCache` and a `SimulatorDataSource` together, starts the source against the 10 default tickers, and renders a `rich.live.Live` dashboard for 60 seconds (or until `Ctrl+C`). Each frame builds a `rich.table.Table` of all 10 tickers showing seed price, current price, change %, a unicode sparkline (`▁▂▃▄▅▆▇█` characters mapped from min/max of a per-ticker `deque`), and a coloured direction arrow. A side panel renders a small event log of notable moves (the random ±2–5 % shock events). On exit it prints a summary comparing final prices against seeds.

The point of this PR is not new functionality — it is a smoke test that a human can watch. After the design/implement/review/fix cycle was done, the only signal that everything actually worked end-to-end was a green test suite. The demo turned that into something a human reviewer could see for themselves: prices that move, that flash colour, that occasionally jump on shock events, that respect per-ticker volatilities (TSLA visibly more volatile than V), and that look like a market. It also doubles as a reference implementation for a frontend developer who wants to know what the cache looks like at runtime without standing up a browser.

PR #7 was merged as `01ee159`. The track was then closed by commit `5594a85` ("Add market data summary, backend CLAUDE.md, archive old planning docs"), which authored `planning/MARKET_DATA_SUMMARY.md` and `backend/CLAUDE.md`, and `git mv`-ed the five superseded design documents (`MARKET_DATA_DESIGN.md`, `MARKET_DATA_REVIEW.md`, `MARKET_INTERFACE.md`, `MARKET_SIMULATOR.md`, `MASSIVE_API.md`) from `planning/` to `planning/archive/`. The summary file at `C:\Users\guill\OneDrive\Documents\Cursor\Projects\finally\planning\MARKET_DATA_SUMMARY.md` is the canonical hand-off document for any agent working on a downstream feature.

### 2.7 Final summary and lessons

**What was delivered.** A complete, tested, reviewed market-data subsystem in `backend/app/market/` (eight modules, ~500 lines of production code, 73 tests, 84 % coverage). The public API exposed from `app.market` is exactly five names:

```python
from app.market import (
    PriceUpdate,            # immutable dataclass: ticker, price, previous_price, timestamp, + computed change/direction
    PriceCache,             # thread-safe store with version counter
    MarketDataSource,       # ABC: start / stop / add_ticker / remove_ticker / get_tickers
    create_market_data_source,  # factory: simulator vs Massive based on MASSIVE_API_KEY
    create_stream_router,   # FastAPI router factory for /api/stream/prices SSE endpoint
)
```

The simulator path runs with no API key required and seeds the cache before its loop starts so the SSE endpoint has data on its first tick. The Massive path runs the synchronous `RESTClient` under `asyncio.to_thread(...)`, swallows API errors so a bad poll never kills the loop, and falls back to last-known prices in the cache.

**Patterns that carried into later GSD work.**

- **Design-document-as-contract.** Every later GSD agent works against a markdown spec that pre-fixes file paths, public API, and edge cases, just as `MARKET_DATA_DESIGN.md` did.
- **Explicit code-review pass as a separate agent run.** The review-then-fix loop turned out to be much more reliable than asking the implementer to self-review.
- **Severity-tagged issue lists.** The High / Medium / Low / Trivial ladder in `MARKET_DATA_REVIEW.md` made it trivial for the fix agent to triage.
- **Strategy pattern + factory selecting on env vars.** Reused later for the LLM client (`LLM_MOCK=true`) and for any other "real vs mock" duality.
- **Shared in-memory cache as the single source of truth.** Producers write, consumers read; no consumer ever talks to a producer directly. This stayed the architectural backbone of the rest of the platform.
- **Archive on completion.** The `planning/archive/` convention — superseded docs are kept readable but moved out of the active set, and a thin `*_SUMMARY.md` is the only thing left in `planning/` — became the standard hand-off pattern.

**Lessons from what went wrong.**

1. **A lazy import is a contract you also have to enforce in `pyproject.toml`.** If the package is a runtime dep, lose the lazy import; the testing complexity it forces is not worth it.
2. **The design agent should ship a working `pyproject.toml` build configuration**, not just the source tree. The High-severity issue (`uv sync` failing) was a pure config oversight that blocked Docker builds — entirely preventable with a single `uv sync` smoke check before the commit was opened.
3. **Mock targets must exist where you patch them.** `patch("module.RESTClient")` against a name that is only imported inside a function is a guaranteed `AttributeError`. Either move the import or pass `create=True`. The cleaner answer is to fix the contradiction at the source rather than paper over it in tests.
4. **Coverage gaps tell you what you forgot to test.** `stream.py` at 31 % was the loudest signal in the review — the SSE generator is the primary consumer of the cache and the only path the frontend touches, and it had zero dedicated tests.
5. **Public methods at module boundaries.** Reaching into `_tickers` is the kind of friction-creating shortcut that's invisible to the implementer but immediately obvious to a reviewer, and the cost of `def get_tickers(self): return list(self._tickers)` is two lines.
6. **A small visual demo is cheap insurance.** PR #7 added 272 lines of dev-only code that no production path depends on, and it was the single artifact that proved the system *looks* right rather than just passes tests.

---

## 3. Parallel Agent Implementations

### 3.1 Overview

After the shared market-data foundation landed on `main` (through commit `14550e1` "Ready for Teams"), the FinAlly codebase fanned out into several parallel branches in which different agent teams independently built — or rebuilt — the rest of the trading workstation. The same `planning/PLAN.md` specification was the contract; the agents differed in orchestration framework, model, scope, and discipline. Comparing the branches side-by-side is the most direct way to see how those choices shape an end product.

Four lineages are worth comparing in detail:

- **`origin/finally-gsd`** — a strictly phased, plan-driven build with 103 commits that walk through ten numbered phases (`docs(phase-XX)`, `feat(XX-YY)`, `test(XX-YY)`). It serves here as the reference point for "the methodical version" and is documented elsewhere in this history.
- **`origin/polecat/obsidian/fi-gf9@mlinq3m5`** — a single-shot build by an agent named "obsidian" running Claude Opus 4.6, which dropped the entire workstation in one mega-commit.
- **`origin/codex`** — a Codex-driven track (committer "Sprite") that started fresh from the market-data baseline with its own opinions about UI architecture, then iterated.
- **`origin/agent-teams`** (current line) — a continuation branch that picked up after `Agent Teams v1` (`5dcd36b`) and refactored, extended, and deployed the system through 27 incremental commits.

The two earlier bootstrap branches (`origin/start`, `origin/basic`) are also worth noting because they show the deliberate "reset points" the course used to give parallel teams a clean slate.

Read the comparison along three axes: **how much was changed per commit** (single-shot vs. phased vs. iterative), **how the backend is decomposed** (flat-by-domain modules vs. layered modules vs. monolithic `main.py`), and **what each track surfaced as new problems** (deployment, multi-source market data, prompt hygiene, etc.).

---

### 3.2 The "obsidian" single-shot build (`origin/polecat/obsidian/fi-gf9@mlinq3m5`)

The obsidian branch contains exactly two commits beyond the shared baseline:

- `d521645` — "Build full FinAlly trading workstation" (author: `obsidian <ed.donner@gmail.com>`, Co-Authored-By: Claude Opus 4.6) — **61 files changed, 10,756 insertions, 1 deletion**.
- `a886ea8` — "Add frontend README" — 36-line follow-up.

The first commit is a *complete* implementation of everything the market-data baseline didn't already cover. The file structure tells you the agent's mental model.

**Backend layout — flat by domain:**

```
backend/app/chat/{__init__.py, routes.py, service.py}
backend/app/portfolio/{__init__.py, routes.py, service.py}
backend/app/watchlist/{__init__.py, routes.py, service.py}
backend/app/db/{__init__.py, database.py, schema.sql}
backend/app/main.py
```

Each domain (chat, portfolio, watchlist) gets its own package with exactly two modules: `routes.py` (FastAPI router) and `service.py` (business logic). The database layer is a sibling, not a dependency injected upward. There is no `routes/` aggregator and no separate `models/` directory — Pydantic models live next to the code that uses them. This is a deliberately *flat-by-domain* shape and it pairs well with the single-commit delivery: each domain folder is internally complete and independent of the others.

**Tests mirror the layout:**

```
backend/tests/chat/test_service.py        (56 lines)
backend/tests/portfolio/test_service.py   (109 lines)
backend/tests/watchlist/test_service.py   (63 lines)
backend/tests/db/test_database.py         (57 lines)
backend/tests/test_api.py                 (41 lines, integration)
```

The commit message claims **32 new tests, 105 total passing**. Tests are domain-local; only `test_api.py` is an integration test sitting at the package root.

**Frontend — flat components folder under `frontend/app/`:**

```
frontend/app/components/{ChatPanel, Header, Heatmap, PnLChart, Positions,
                         PriceChart, Sparkline, TradeBar, Watchlist}.tsx
frontend/app/lib/{api.ts, types.ts, useSSE.ts}
frontend/app/page.tsx          (80 lines)
frontend/app/layout.tsx        (19 lines)
frontend/app/globals.css       (56 lines)
```

Notice the components live *inside* the Next.js `app/` directory rather than a sibling `components/` folder — the obsidian agent leaned into the App Router convention as far as it would go. The whole surface area (9 components + 3 lib files) sits at one level of nesting.

**Strengths and limitations.** The single-shot approach gives you a coherent, internally-consistent design — every module looks like every other module because one agent wrote them in one pass. The tradeoff is reviewability: the diff is 10,756 lines, so it is essentially impossible to audit incrementally, and any bug in the design propagates to every domain. There is no roadmap, no STATE file, no per-phase verification artifact — the planning trail visible elsewhere in the project simply does not exist here. The branch also stops cold after the README commit; nothing in obsidian addresses deployment, real market data integration, or the LLM-call quality issues that the iterative branches later surfaced.

---

### 3.3 The Codex agent track (`origin/codex`)

`origin/codex` (committer `Sprite <noreply@sprite.dev>`, indicating an OpenAI Codex-flavored orchestrator) started from the same `14550e1` "Ready for Teams" baseline but produced three distinctively-named commits and a handful of follow-ons:

- `305bc17` — "codex build" — **60 files changed, 9,626 insertions, 72 deletions**
- `0154fc6` — "Codex fixes to market data" — 5 files, +189/-6
- `a91cc24` — "Codex new UI" — 27 files, +1,085/-150
- `a886ea8` — "Add frontend README" (later added)

**The "codex build" commit is shaped completely differently from obsidian.** The backend is *not* domain-flat; it is monolithic:

```
backend/app/db.py        (169 lines)
backend/app/llm.py       (172 lines)
backend/app/main.py      (511 lines)
backend/app/market/stream.py  (modified)
backend/tests/test_api.py     (137 lines)
```

There is no `backend/app/portfolio/` or `backend/app/watchlist/` folder — *all* of the portfolio, watchlist, and chat route handling lives inside the 511-line `main.py`. `db.py` and `llm.py` are top-level modules, not packages. Compared to obsidian's clean per-domain decomposition, this is a single-file FastAPI application with helper modules. It is faster to write, harder to evolve.

**The frontend, in contrast, is more ambitious than obsidian's:**

```
frontend/src/components/{ChatPanel, ConnectionDot, Header, Heatmap, MainChart,
                         Panel, PnlChart, PositionsTable, Sparkline, TradeBar,
                         WatchlistPanel}.tsx
frontend/src/hooks/{useMarketStream.ts, useTradingData.ts}
frontend/src/types/trading.ts
frontend/tailwind.config.ts
frontend/tests/{api.test.ts, tradebar.test.tsx, useMarketStream.test.tsx}
frontend/vitest.config.ts, vitest.setup.ts
```

Codex used `src/` rather than `app/components/`, split a `Panel` primitive out as its own component (a Bloomberg-terminal-style reusable chrome), added a dedicated `ConnectionDot` for the SSE indicator, introduced two non-trivial hooks (`useMarketStream`, `useTradingData`), and brought in **vitest** for frontend unit tests — none of which obsidian did. Codex also rewrote `frontend/app/page.tsx` (84 lines) as a thin shell that wires those hooks/components together.

Codex was also the first track to take E2E testing seriously: `305bc17` adds `test/docker-compose.test.yml`, `test/playwright.config.ts`, and `test/specs/smoke.spec.ts` (149 lines), plus `scripts/test_mac.sh` / `test_windows.ps1` and a `scripts/container_app.py` shim. The Dockerfile in this commit (48 lines vs obsidian's 33) is correspondingly more elaborate.

**The follow-ons reveal what Codex missed the first time.** `0154fc6` "Codex fixes to market data" adds `backend/app/market/factory.py` patching and rewrites `massive_client.py` (the actual external integration was incomplete on day one), plus a `planning/MASSIVE_API_FIX.md` post-mortem. `a91cc24` "Codex new UI" is a 1,085-line UI rebuild that adds a `frontend/src/components/WatchlistPanel.tsx` rewrite (+156/-48), a new `MarketSourceToggle`-style affordance, and a substantial `frontend/tests/useTradingData.test.tsx` suite — and it documents itself in `planning/NEW_UI.md`. The pattern is iterate-with-postmortem, in contrast to obsidian's land-once-and-stop.

**Compared to GSD:** the GSD branch (`origin/finally-gsd`) shipped an explicit Phase 6 frontend foundation, Phase 7 watchlist, Phase 8 portfolio, Phase 9 chat, and Phase 10 packaging/testing — each as a `docs(XX-YY)` plan plus a `feat(XX-YY)` implementation plus a verification doc, totaling ~80 commits past the baseline. Codex compresses that into essentially three commits but loses the audit trail.

---

### 3.4 The agent-teams iteration track (`origin/agent-teams`)

`origin/agent-teams` is the active line. It branches from `14550e1` "Ready for Teams" through a checkpoint commit `5dcd36b` "Agent Teams v1" and then accumulates 27 further commits as multiple sub-agents iterate on the same codebase. `5dcd36b` itself is a *third* re-implementation of the post-market-data work — 75 files, 16,775 insertions, layered backend (`backend/app/{db, llm, routes}/`) with `routes/` as the aggregator (`chat.py`, `portfolio.py`, `watchlist.py`), a separate `llm/{mock.py, models.py, service.py}` package, and frontend tests under `frontend/__tests__/`. So the starting point for this track is *neither* obsidian's flat-by-domain nor Codex's monolithic — it's a fourth shape: layered-by-concern.

The 27 follow-on commits group into four themes.

**Bootstrap and reset cluster (Feb 11–21, 2026)**

- `d8ccc96` "Added in the lib directory and moved to port 8001" — adds `frontend/lib/{api.ts, format.ts, types.ts, use-prices.ts}` (a new client-side library directory) and bumps the dev port to 8001 to dodge a collision. 8 files, +304/-7.
- `7b160d9` "Ready for push" — strips `.DS_Store` and tightens `.gitignore`. 2 files.
- `cf41801` "Put port back to 8000" — single-line `scripts/start_mac.sh` change reverting the port.
- `4e94a35` "Changed port back to 8000" — 4 lines in `scripts/start_mac.sh` (a second pass at the same revert; the file had drifted).

This cluster is small but it is the most human moment in the log: an agent team reflexively moved off port 8000 to avoid local conflicts, then had to walk it back twice to keep parity with the documented `localhost:8000` UX promise.

**Deployment cluster**

- `54453b3` "deployment to fly.io" — adds `planning/DEPLOY.md` (160 lines), `planning/fly.toml` (20 lines), and `scripts/deploy.sh` (52 lines). This was the first track to address production hosting at all. None of obsidian, codex, or GSD attempted it.

**Reset to "basic" and rebuild**

- `9c1b7d7` "added Massive API description" — adds a 195-line `MASSIVE.md` at repo root summarizing the Polygon/Massive integration contract.
- `c11222f` "Basic starting point" — a deliberate **97-file deletion** (16,115 deletions) that strips backend/, frontend/, scripts/, planning/archive/, etc. and renames `MASSIVE.md` into `.claude/skills/massive/SKILL.md` and `planning/PLAN.md` into `CLAUDE.md`. The commit re-bootstraps the project as a clean skill-driven slate.
- `3f9599a` "Tweaked basic" — moves CLAUDE.md content into a 450-line `AGENTS.md` companion (the convention Codex introduced), 2 files.
- `eef1ddc` "Added plugins" — `.claude/settings.json` plugin registration, 9 lines changed.

This is the most aggressive move on the branch: the team chose to throw away `Agent Teams v1` and rebuild from a leaner skill-based scaffold rather than continue patching it.

**LLM and UX iteration cluster**

- `306ebcf` "took lib out of gitignore" — adds `frontend/src/lib/{api.ts (282), format.ts (16)}`. The library was being created but ignored; one-line `.gitignore` fix exposed it. +298/-1.
- `a8d9363` "Updated LLM calls to simplify and improve" — `backend/app/llm.py` shrinks from ~225 lines down by ~100 (124 changed, mostly deletions), `backend/app/main.py` simplifies its LLM wiring (12 lines), test fixtures updated. The agent identified that the LLM service had become bloated and pulled it back to essentials. +63/-100.
- `9fd10a9` "Support tickers not in watchlist" — `backend/app/main.py` (+9), `backend/app/llm.py` (+3), `backend/app/market/seed_prices.py` (+21). Surfaced a real bug: when the LLM was asked to act on a ticker the user hadn't yet watched, the price cache had no entry. The fix seeds prices for any ticker the LLM mentions.
- `04ac7ad` "Improved prompt" — 8 lines in `backend/app/llm.py`. A targeted prompt-engineering tweak after the previous two commits made the LLM more capable.
- `ee495c0` "Added short sell protection and toast" — `backend/app/llm.py` (+5), plus a new `frontend/src/components/ToastContainer.tsx` (29 lines), `frontend/src/hooks/useToast.ts` (30 lines), and wiring in `frontend/app/page.tsx` (+32). Fixes the case where the LLM tries to sell more shares than the user holds, and gives the UI a way to surface the error gracefully. +110/-5.
- `fdf88fc` "Updated dependencies" — major lock-file refresh, `frontend/package-lock.json` regenerates 8,143 lines (+6,321/-1,920). Keeps the project on current APIs as required by the project conventions.
- `0472e7d` "Market data switcher" — adds `frontend/src/components/MarketSourceToggle.tsx` (96 lines) and matching backend support in `backend/app/market/factory.py` (+65/-19) so a user can flip between simulator and Massive at runtime, not just at boot. +248/-19.

**Finalization**

- `b935f5f` and the second `14550e1` "Ready for Teams" — minor `.claude/settings.local.json` and lockfile refreshes, marking the branch as ready for the next cohort.

The shape of the iteration is: small commits, each addressing one observable problem, often paired with a docstring or planning note. Compared to obsidian's land-everything-once or Codex's land-rebuild-rebuild, agent-teams is the most genuinely *agile* branch — and it is also the only one to carry the project all the way through deployment and post-deploy bug fixes (short-sell, off-watchlist tickers, dependency drift).

---

### 3.5 Origins: `origin/start` and `origin/basic`

The earliest two reference points are tiny.

`origin/start` is just five commits — the bootstrap state of the repo *before* any agent work began:

- `8e9bb6b` "Initial commit" — `.gitignore` (207 lines), `LICENSE`, `README.md` (2 lines).
- `8f25050` "First plan and command" — `planning/PLAN.md` (606 lines), `.claude/commands/doc-review.md`, `.claude/skills/cerebras/SKILL.md` (43 lines). This is the moment the project's contract was written.
- `77a03ca` "Prepared for lecture", `15480f8` "Simplified plan", `6b568a9` "Updated docs and settings" — adds `.claude/agents/change-reviewer.md`, `.claude/settings.json`, and prunes the plan into the form the agent teams would actually consume.

`origin/start` contains **no application code at all** — it is purely the planning skeleton plus Claude harness configuration.

`origin/basic` is a slightly later "alternative bootstrap" line that sits between the early planning commits and the iteration tracks. Its tip commits (`c11222f` "Basic starting point", `3f9599a` "Tweaked basic", `eef1ddc` "Added plugins", with shared ancestors back through `9c1b7d7`, `54453b3`, `5688357`, `a440dd8`, `3d220bb`, `921ead9`, `ba93d9e`) are the same cluster of "rebuild from a leaner skill-driven scaffold" commits that show up on `agent-teams` — meaning `agent-teams` and `basic` share that reset rather than diverging from it. `origin/basic` exists primarily as a labeled checkpoint of "the leanest viable starting point for the next agent team," distinct from the heavier `Agent Teams v1` scaffold.

---

### 3.6 Comparison table

| Dimension | GSD (`origin/finally-gsd`) | Obsidian (`origin/polecat/obsidian/...`) | Codex (`origin/codex`) | Agent-teams (`origin/agent-teams`) |
|---|---|---|---|---|
| **Orchestration style** | Phased plan-driven; explicit `docs(phase-XX)` / `feat(XX-YY)` / `test(XX-YY)` / `docs(XX-VERIFICATION)` cadence | Single-shot mega-commit + README follow-up | Build-then-rebuild (3 large commits each with a postmortem MD) | Continuous incremental iteration with periodic resets |
| **Commits past `14550e1` baseline** | ~80 (10 phases x ~8 commits) | 2 | 18 (3 codex + 15 follow-on) | 27 |
| **Largest single commit** | feat(06-01) ~Next.js scaffold (modest) | `d521645` 10,756 insertions | `305bc17` 9,626 insertions | `5dcd36b` 16,775 insertions; later `c11222f` deletes 16,115 |
| **Backend structure** | Layered: `backend/app/{db, llm, routes, market}` with separate `routes/` aggregator | Flat-by-domain: `backend/app/{chat, portfolio, watchlist, db}/{routes.py, service.py}` | Monolithic: 511-line `backend/app/main.py` + top-level `db.py`, `llm.py` | Started layered (Agent Teams v1), reset to lean Codex-style monolith with `app/main.py` + `app/llm.py` + `app/db.py` and `app/market/` |
| **Frontend approach** | `frontend/components/` + `frontend/__tests__/` (Jest) + Zustand stores | `frontend/app/components/` (App Router-native) + `frontend/app/lib/` | `frontend/src/components/` + hooks + Vitest + Tailwind config | `frontend/src/components/` + `frontend/src/hooks/` + `frontend/src/lib/` (had to be rescued from gitignore) + `frontend/lib/` (older parallel dir) |
| **Tests added** | Phase-by-phase unit + 14 Playwright E2E specs in `test/e2e/{chat, fresh-start, portfolio, trading, watchlist}.spec.ts` | 32 new (105 total passing per commit msg) — pytest only | pytest + vitest unit + 1 Playwright `smoke.spec.ts` (149 lines) | Inherits Agent Teams v1 suites; adds `useTradingData`, `theme.test.tsx`, etc. via codex-cluster commits; later trims |
| **LLM integration** | `backend/app/llm/{mock.py, models.py, service.py}` modular | `backend/app/chat/service.py` (224 lines) | `backend/app/llm.py` monolith (172 lines), later simplified | Iteratively cut down from ~225 to ~125 lines (`a8d9363`), prompt tuned (`04ac7ad`), short-sell guard (`ee495c0`) |
| **Notable issues surfaced** | E2E Heatmap null-coalescing for Recharts Treemap (`05842ba`); 62-requirement traceability | (none documented — single shot, no postmortem) | Massive client incomplete on first try (`MASSIVE_API_FIX.md`); UI required full rebuild (`NEW_UI.md`) | Off-watchlist ticker handling, short-sell guard, port collision, gitignored lib dir, runtime market-source switching, Fly.io deploy |
| **Deployment** | Dockerfile + docker-compose + start/stop scripts only | Dockerfile + docker-compose + start/stop scripts only | Dockerfile (48 lines, more elaborate) + container_app.py + test_*.sh | All of the above PLUS `planning/fly.toml` + `planning/DEPLOY.md` + `scripts/deploy.sh` |
| **Author signature** | `Edward Donner` w/ Claude Opus 4.6 co-author | `obsidian` w/ Claude Opus 4.6 co-author | `Sprite <noreply@sprite.dev>` (Codex orchestrator) | Mixed: `Edward Donner`, `Sprite`, `GuileMadriz` |

---

### 3.7 What carried forward

Looking at the current working tree on `agent-teams` and comparing it to each parallel attempt clarifies which design decisions survived the natural selection of multiple rebuilds.

**Carried forward from Codex:**

- The **monolithic `backend/app/main.py`** with sibling `db.py` and `llm.py` modules is the shape that lives on in the agent-teams branch today. The backend listing in the project status (`backend/app/main.py`, `backend/app/llm/`, `backend/app/db/`, `backend/app/services/`) shows the layered evolution but the FastAPI surface still concentrates in `main.py` and `llm.py` — Codex's bet that the application was small enough to live in one file paid off enough to keep the structure.
- The **frontend `src/` layout** (`frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/lib/`, `frontend/src/types/`, `frontend/src/context/`) is Codex's invention and is the layout the agent-teams branch standardized on.
- **Vitest** instead of Jest as the frontend test runner.
- **`scripts/container_app.py`** and **`test/docker-compose.test.yml`** as the harness for E2E tests.
- The **`Panel.tsx` reusable chrome primitive** and **`ConnectionDot.tsx`** components.
- **`AGENTS.md`** alongside `CLAUDE.md` — the dual-instructions-file convention Codex required.

**Carried forward from agent-teams iteration itself:**

- **`MarketSourceToggle.tsx`** for runtime simulator/Massive switching.
- **`ToastContainer.tsx` + `useToast.ts`** for surfacing trade-validation errors (the short-sell guard).
- **Off-watchlist ticker support** in `seed_prices.py` and the LLM prompt.
- The **simplified `llm.py`** (~125 lines, post-`a8d9363`) over the heavier earlier versions.
- **Fly.io deployment** (`planning/DEPLOY.md`, `planning/fly.toml`, `scripts/deploy.sh`) — the only branch that addressed production hosting.
- **The "Basic starting point" reset** as a methodology — `c11222f`'s aggressive deletion of the `Agent Teams v1` scaffold demonstrates that for an agent-driven project, a clean slate sometimes beats incremental refactor.

**Discarded:**

- **Obsidian's flat-by-domain backend** (`backend/app/{chat, portfolio, watchlist}/{routes.py, service.py}`). It was the cleanest decomposition of any branch on paper, but it lost out to Codex's monolith because the per-domain files were thin enough that splitting them added overhead without clear benefit.
- **Agent Teams v1's layered backend with a `routes/` aggregator** (`backend/app/routes/{chat.py, portfolio.py, watchlist.py}` + `backend/app/llm/{mock.py, models.py, service.py}`). Wiped wholesale by `c11222f` "Basic starting point."
- **Obsidian's `frontend/app/components/` placement.** The App Router-native layout was abandoned in favor of `frontend/src/components/`, separating React component code from Next.js routing concerns.
- **GSD's per-phase `RESEARCH.md` / `PLAN.md` / `VERIFICATION.md` triplets.** None of the merged branches preserved that level of planning artifact density; they survive only on `origin/finally-gsd` itself as a reference build.
- **Codex's single Playwright `smoke.spec.ts`.** The agent-teams branch inherited the broader 14-test, five-spec layout from `Agent Teams v1` as the testing foundation rather than the lighter Codex alternative.
- **Port 8001.** Tried twice (`d8ccc96`), reverted twice (`cf41801`, `4e94a35`).

The synthesis pattern is clear: the project converged on a *Codex-shaped backend skeleton, an agent-teams-driven UX layer with operational concerns (toasts, deployment, runtime switches) that the single-shot branches never reached, and a planning/testing trail that was deliberately lighter than GSD's*. None of the four branches dominated — the final state is a deliberate composite, with each parallel attempt contributing the parts it did best.
