#!/usr/bin/env bash
set -euo pipefail

HOMELAB_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Creating external Docker network 'proxy_net'..."
docker network inspect proxy_net >/dev/null 2>&1 \
  || docker network create proxy_net

echo "==> Creating directory structure..."
mkdir -p "$HOMELAB_DIR"/{gateway,security,music,downloads,video,finance,dashboard}

echo "==> Creating .env files from examples..."
for stack in gateway security music downloads video finance dashboard; do
  if [ ! -f "$HOMELAB_DIR/$stack/.env" ]; then
    cp "$HOMELAB_DIR/$stack/.env.example" "$HOMELAB_DIR/$stack/.env"
    echo "    Created $stack/.env"
  else
    echo "    $stack/.env already exists, skipping"
  fi
done

echo ""
echo "Initialization complete!"
echo ""
echo "Next steps:"
echo "  1. Edit each stack's .env file with your credentials"
echo "  2. Start the stacks: ./start.sh"
