# Scripts

Helpers to build and run the FinAlly container locally. They wrap the Docker
commands described in `planning/PLAN.md` section 11.

## Prerequisites

- Docker Desktop (macOS / Windows) or a Linux Docker engine
- **Node 20+** with `npm` on PATH. The Next.js static export is built on the
  host (not inside Docker) because `npm ci` inside Docker Desktop is
  unreliably slow. The start scripts run the build for you when needed.
- A `.env` file in the project root. Copy `.env.example` and fill in
  `OPENROUTER_API_KEY`. `MASSIVE_API_KEY` is optional; if absent the simulator
  is used.

## macOS / Linux

```bash
./scripts/start_mac.sh           # build frontend + image if needed, then start
./scripts/start_mac.sh --build   # force a rebuild of frontend and image
./scripts/start_mac.sh --open    # also open the browser
./scripts/stop_mac.sh            # stop and remove the container (volume kept)
```

Mark the scripts executable on first checkout: `chmod +x scripts/*.sh`.

## Windows (PowerShell)

```powershell
.\scripts\start_windows.ps1            # build if needed, then start
.\scripts\start_windows.ps1 -Build     # force a rebuild of frontend and image
.\scripts\start_windows.ps1 -Open      # also open the browser
.\scripts\stop_windows.ps1             # stop and remove (volume kept)
```

If PowerShell blocks the script, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## What the scripts do

1. Detect whether `frontend/out/` is missing, older than any frontend source
   file (`frontend/app/**`, `frontend/components/**`, `frontend/lib/**`,
   `package.json`, `package-lock.json`, `next.config.mjs`,
   `postcss.config.mjs`), or `--build` was passed. If so, run
   `npm ci && npm run build` in `frontend/`.
2. Build the Docker image (`finally:latest`) if it doesn't exist or `--build`
   was passed. The image copies the prebuilt `frontend/out/` into
   `/app/static/` and fails fast if `index.html` is missing.
3. Remove any previous `finally-app` container.
4. Run a new container, port `8000`, named volume `finally-data` mounted at
   `/app/db`, `.env` injected via `--env-file` if present.

The named volume keeps the SQLite database (`finally.db`) across restarts;
trades, watchlist, and chat history persist. `stop` does not remove it.

## Manual equivalents

```bash
# 1. Build the frontend on the host (one-time or after frontend changes)
cd frontend && npm ci && npm run build && cd ..

# 2. Build the Docker image
docker build -t finally:latest .

# 3. Run the container
docker run -d --name finally-app \
    -p 8000:8000 \
    -v finally-data:/app/db \
    --env-file .env \
    finally:latest

# Or via compose (compose does NOT auto-build the frontend; do step 1 first)
docker compose up -d --build
docker compose down            # stop, keep volume
docker compose down -v         # stop and wipe data
```

## Resetting the database

The lazy seeder repopulates a fresh DB with the default profile and watchlist:

```bash
docker rm -f finally-app
docker volume rm finally-data
```
