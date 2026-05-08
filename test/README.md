# FinAlly E2E Tests

End-to-end test harness using Playwright.

## Prerequisites

- Docker + Docker Compose
- The `finally:latest` image must already be built. From the project root:
  ```bash
  # ensure frontend is built first (Dockerfile copies frontend/out/ in)
  cd frontend && npm ci && npm run build && cd ..
  docker build -t finally:latest .
  ```

## Run the suite

From the project root:

```bash
docker compose -f test/docker-compose.test.yml up --abort-on-container-exit --exit-code-from playwright
```

The exit code matches the Playwright runner. Pass `--build` to rebuild any local changes before the run.

To tear down volumes between runs:

```bash
docker compose -f test/docker-compose.test.yml down -v
```

## What it does

- Starts an `app` container (`finally:latest`) with `LLM_MOCK=true`, no `MASSIVE_API_KEY`, fresh tmpfs database.
- Waits for `/api/health` via the container healthcheck.
- Starts a `playwright` container that runs `npm ci && npx playwright test` against `http://app:8000`.

## Run locally without Docker

If you have Node 20+ and an `app` already running on `http://localhost:8000`:

```bash
cd test
npm ci
BASE_URL=http://localhost:8000 npx playwright test
```

## Test layout

- `tests/smoke.spec.ts` — health endpoint and home page title.
- `tests/*.spec.ts` — scenarios per `planning/PLAN.md` §12.

## LLM mock contract

Tests rely on `LLM_MOCK=true`. Triggers in chat input:

- `buy <qty> <TICKER>` / `sell <qty> <TICKER>` — executes a trade
- `add <TICKER>` / `remove <TICKER>` — modifies the watchlist
- Any other input — `message` is `"Mock: <input>"`, no actions

Owner: integration-tester.
