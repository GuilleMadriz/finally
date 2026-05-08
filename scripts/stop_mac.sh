#!/usr/bin/env bash
# Stop and remove the FinAlly container. The named volume is preserved.
# Usage: ./scripts/stop_mac.sh
set -euo pipefail

CONTAINER="finally-app"

if ! command -v docker >/dev/null 2>&1; then
    echo "docker CLI not found." >&2
    exit 1
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER"; then
    docker rm -f "$CONTAINER" >/dev/null
    echo "Stopped ${CONTAINER}. Data volume 'finally-data' preserved."
else
    echo "No ${CONTAINER} container running."
fi
