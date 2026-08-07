# Report: Wire the two-container hort into the homelab

## Status: complete (homelab side)

All plan tasks implemented. The remaining prerequisite (committing/pushing the
fertigation `web/` two-container code to `main`) is **outside this repo** and not
actionable here; images will only build the new architecture once that push
lands.

## Changes

### `garden/docker-compose.yml` — rewritten
- Removed the old direct-MQTT `hort` (context `#main:dashboard`) and the `hort2`
  validation service.
- `hort`: static nginx artifact, context `#main:web`,
  `apps/dashboard/Containerfile`, **no env**, on `proxy_net`.
- `hort-server`: context `#main:web`, `apps/server/Containerfile`, env
  `MQTT_URL=mqtt://mosquitto:1883`, `MQTT_USERNAME`/`MQTT_PASSWORD`,
  `MQTT_PREFIX=kc868-a8`, `PORT=4000`, on `proxy_net`. No host port publish.

### `gateway/Caddyfile:72` — path-split `@hort`, removed `@hort2`
- `@hort` now uses a `route` block: `/api/*` → `hort-server:4000` with
  `flush_interval -1` (SSE unbuffered), catch-all → `hort:80`.
- `@hort2` block deleted. `@mqtt` (mosquitto:9001) left intact per plan non-goals.

### `garden/.env.example` — server creds only
- Dropped `DOMAIN`; kept `MQTT_USERNAME` / `MQTT_PASSWORD`.

### `start.sh:6` — broker before server
- Reordered `... cpa automation garden dashboard` so `automation` (mosquitto)
  starts before `garden`.

### `README.md`
- Garden bullet rewritten to the two-container model (static `hort` +
  `hort-server` as the only MQTT client at `mqtt://mosquitto:1883`; Caddy
  path-splits `/api/*`; browser no longer uses MQTT-over-WebSockets).
- Mermaid diagram: added `hort-server` node (Caddy `/api` → hort-server → Mosquitto).
- `garden/.env` table: removed `DOMAIN` row; noted creds live only on
  `hort-server`.

## Verification
- `docker compose -f garden/docker-compose.yml config` → parses cleanly.
- Caddyfile validated with `caddy validate` (base `caddy:latest` image; the
  Cloudflare-DNS `tls` block was temporarily swapped to `tls internal` for the
  check only, since the base image lacks the plugin and the custom gateway image
  can't be built here due to a builder-image arch mismatch). Result:
  **"Valid configuration"**. My edit is confined to the `@hort` block, unrelated
  to TLS.
- Local `docker compose build` not run: the new `apps/server` / static
  `apps/dashboard` code is not yet on fertigation `main`, so the remote git
  context would still build the old artifact.

## Follow-ups / notes
- **Blocking prerequisite:** push the fertigation `web/` two-container code to
  `main` before `docker compose -f garden/docker-compose.yml up -d --build`.
- Post-deploy smoke checks (per plan) to run on the server after that push:
  `/api/health` → `{"ok":true}`, dashboard renders with live values,
  `curl -N .../api/stream` streams incrementally, UI command reaches the device.
- Optional later cleanup (explicit plan non-goal): mosquitto `9001` websocket
  listener and Caddy `@mqtt` route are now unused by the dashboard.
