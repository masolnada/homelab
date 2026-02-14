# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Deployment

```bash
# Deploy changes: commit, push, then pull on server
git push
ssh -i ~/.ssh/id_infra_v2 ubuntu@homelab "cd /opt/homelab && sudo git pull"

# Restart a specific stack after pulling
ssh -i ~/.ssh/id_infra_v2 ubuntu@homelab "cd /opt/homelab && sudo docker compose -f <stack>/docker-compose.yml up -d"

# Start all stacks in order (gateway → security → media → finance → dashboard)
ssh -i ~/.ssh/id_infra_v2 ubuntu@homelab "cd /opt/homelab && sudo ./start.sh"
```

README-only changes don't need a stack restart.

## Architecture

Five independent Docker Compose stacks share a single `proxy_net` bridge network:

- **gateway/** — Tailscale sidecar + Caddy (custom build with Cloudflare DNS plugin). Caddy uses `network_mode: service:tailscale` to share its network namespace. TLS via DNS-01 challenge with Cloudflare.
- **security/** — Vaultwarden + backup sidecar (daily CIFS backup to TrueNAS, pauses container during backup)
- **media/** — Navidrome with read-only CIFS mount from TrueNAS music share
- **finance/** — IHateMoney + backup sidecar (same pattern as security)
- **dashboard/** — Homepage + Docker socket proxy (Tecnativa). Homepage connects to the proxy over TCP:2375, never touches the Docker socket directly.

All inter-service traffic is plain HTTP over `proxy_net`. External access goes through Tailscale (WireGuard) → Caddy (TLS termination). NAS access is direct LAN via CIFS.

## Conventions

- **Conventional commits**: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, etc.
- **No co-author line** in commit messages.
- **Update README.md** when adding a new service.
- **Environment variables**: each stack has `.env.example` (committed) and `.env` (gitignored). Homepage uses `HOMEPAGE_VAR_*` prefix for template substitution in config files.
- Backup sidecars use `docker-volume-backup` with `stop-during-backup` labels, 30-day retention, cron at `0 3 * * *`.

## Key Config Locations

- `gateway/Caddyfile` — reverse proxy rules, wildcard TLS, named matchers per service
- `dashboard/config/` — Homepage YAML configs (services, widgets, docker connection, settings)
- `dashboard/config/docker.yaml` — Docker socket proxy connection (host: dockerproxy, port: 2375)
