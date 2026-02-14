#!/usr/bin/env bash
set -euo pipefail

HOMELAB_DIR="$(cd "$(dirname "$0")" && pwd)"

for stack in gateway security media finance dashboard; do
  echo "==> Starting $stack..."
  docker compose -f "$HOMELAB_DIR/$stack/docker-compose.yml" up -d
done

echo ""
echo "All stacks started."
