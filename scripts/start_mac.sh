#!/usr/bin/env bash
# Build the frontend (if needed), build the image (if needed), and run the container.
# Usage: ./scripts/start_mac.sh [--build] [--open]
set -euo pipefail

IMAGE="finally:latest"
CONTAINER="finally-app"
VOLUME="finally-data"
PORT="8000"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"
OUT_DIR="${FRONTEND_DIR}/out"

force_build=0
open_browser=0
for arg in "$@"; do
    case "$arg" in
        --build) force_build=1 ;;
        --open) open_browser=1 ;;
        -h|--help)
            echo "Usage: $0 [--build] [--open]"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

if ! command -v docker >/dev/null 2>&1; then
    echo "docker CLI not found. Install Docker Desktop or the docker engine." >&2
    exit 1
fi

# Decide whether the frontend needs (re)building.
need_frontend_build=0
if [ ! -f "${OUT_DIR}/index.html" ] || [ ! -d "${OUT_DIR}/_next" ]; then
    need_frontend_build=1
elif [ "$force_build" -eq 1 ]; then
    need_frontend_build=1
else
    newest_src=$(find "${FRONTEND_DIR}/app" "${FRONTEND_DIR}/components" "${FRONTEND_DIR}/lib" \
        "${FRONTEND_DIR}/package.json" "${FRONTEND_DIR}/package-lock.json" \
        "${FRONTEND_DIR}/next.config.mjs" "${FRONTEND_DIR}/postcss.config.mjs" \
        -type f -newer "${OUT_DIR}/index.html" 2>/dev/null | head -n1 || true)
    if [ -n "$newest_src" ]; then
        need_frontend_build=1
    fi
fi

if [ "$need_frontend_build" -eq 1 ]; then
    if ! command -v npm >/dev/null 2>&1; then
        echo "npm not found. Install Node 20+ (https://nodejs.org/) and re-run this script." >&2
        exit 1
    fi
    echo "Building frontend (npm ci + npm run build)..."
    (cd "${FRONTEND_DIR}" && npm ci && npm run build)
fi

if [ "$force_build" -eq 1 ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "Building image ${IMAGE}..."
    docker build -t "$IMAGE" "$ROOT_DIR"
fi

env_args=()
if [ -f "${ROOT_DIR}/.env" ]; then
    env_args+=(--env-file "${ROOT_DIR}/.env")
else
    echo "Note: ${ROOT_DIR}/.env not found. Continuing without --env-file."
    echo "      Copy .env.example to .env to enable LLM chat / Massive market data."
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER"; then
    echo "Removing existing container ${CONTAINER}..."
    docker rm -f "$CONTAINER" >/dev/null
fi

echo "Starting ${CONTAINER}..."
docker run -d \
    --name "$CONTAINER" \
    -p "${PORT}:8000" \
    -v "${VOLUME}:/app/db" \
    "${env_args[@]}" \
    "$IMAGE" >/dev/null

URL="http://localhost:${PORT}"
echo "FinAlly is running at ${URL}"
echo "Logs: docker logs -f ${CONTAINER}"
echo "Stop: ./scripts/stop_mac.sh"

if [ "$open_browser" -eq 1 ]; then
    if command -v open >/dev/null 2>&1; then
        open "$URL"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$URL"
    fi
fi
