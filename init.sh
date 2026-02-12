#!/usr/bin/env bash
set -euo pipefail

HOMELAB_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Creating external Docker network 'proxy_net'..."
docker network inspect proxy_net >/dev/null 2>&1 \
  || docker network create proxy_net

echo "==> Creating directory structure..."
mkdir -p "$HOMELAB_DIR"/{gateway,security,media}

echo "==> Distributing .env files from template..."
for stack in gateway security media; do
  if [ ! -f "$HOMELAB_DIR/$stack/.env" ]; then
    cp "$HOMELAB_DIR/.env.template" "$HOMELAB_DIR/$stack/.env"
    echo "    Created $stack/.env"
  else
    echo "    $stack/.env already exists, skipping"
  fi
done

echo "==> Setting permissions on .env files..."
chmod 600 "$HOMELAB_DIR"/*/.env

echo ""
echo "Initialization complete!"
echo ""
echo "Next steps:"
echo "  1. Edit each stack's .env file with your credentials:"
echo "     - gateway/.env  (DOMAIN, CLOUDFLARE_API_TOKEN)"
echo "     - security/.env (VAULTWARDEN_ADMIN_TOKEN, NAS backup creds)"
echo "     - media/.env    (NAS music share creds)"
echo "  2. Start the stacks in order:"
echo "     cd gateway  && docker compose up -d && cd .."
echo "     cd security && docker compose up -d && cd .."
echo "     cd media    && docker compose up -d && cd .."
echo "  3. Verify Caddy TLS: docker compose -f gateway/docker-compose.yml logs caddy"
