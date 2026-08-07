# Plan: Wire the two-container hort (dashboard + server) into the homelab

## Goal

Cut the `garden/` stack over from the old **direct-MQTT** dashboard to the new
**two-container** architecture:

- `hort` — the static dashboard (nginx, generic build artifact, no MQTT, no env).
- `hort-server` — Express-on-Bun, the only MQTT client, connects to the homelab
  broker over `proxy_net` and exposes `/api/*` (SSE stream + commands).

The browser hits a single origin `hort.${DOMAIN}`; **Caddy** path-splits `/api/*`
to `hort-server` and everything else to the static `hort`. Hard cut: the old
`hort` (deprecated `dashboard/` context) and the `hort2` validation service are
removed.

## Prerequisite (blocking — outside this repo)

The homelab builds images from the remote git context
`github.com/masolnada/automated-fertigation-system.git#main:web`. The new
`apps/server` + `apps/dashboard` (static) + `packages/contracts` code is
currently **uncommitted on the fertigation repo** (verified: `git status` dirty,
`main` still at `b12893c`). **Those `web/` changes must be committed and pushed
to `main` before the server image can build.** The homelab file edits below can
be made independently, but `docker compose up` will only produce the new
architecture once the fertigation `main` carries the two-container code.

## Decisions (resolved with the user)

| # | Decision |
|---|---|
| Cutover | **Hard cut.** Replace `hort` + `hort2` with the new pair; one canonical URL `hort.${DOMAIN}`; delete `hort2`. |
| `/api` routing | **Caddy path-split** (dashboard image stays a generic static artifact). `hort.${DOMAIN}`: `/api/*` → `hort-server:4000`, else → `hort:80`. |
| Service names | `hort` (dashboard) + `hort-server` (Express). |
| Broker address | Server → `mqtt://mosquitto:1883` internally over `proxy_net` (not `wss://mqtt.${DOMAIN}`, not the device-facing `10.0.20.20`). No cross-file `depends_on`; rely on `mqtt.js` auto-reconnect. |

## Facts (verified in-repo)

- `mosquitto` is on `proxy_net`, `allow_anonymous false`, auth via
  `MQTT_USERNAME`/`MQTT_PASSWORD` (`automation/docker-compose.yml`,
  `automation/mosquitto/mosquitto.conf`). Reachable as `mosquitto:1883`.
- Current `garden/docker-compose.yml`: `hort` (context `#main:dashboard`) and
  `hort2` (context `#main:web`, `apps/dashboard/Containerfile`), both still
  direct-MQTT with `MQTT_URL=wss://mqtt.${DOMAIN}`.
- Caddy routes today: `@hort → hort:80`, `@hort2 → hort2:80`, `@mqtt →
  mosquitto:9001` (`gateway/Caddyfile`).
- New fertigation Containerfiles: dashboard = pure static nginx
  (`apps/dashboard/Containerfile`, no `/api` proxy baked in); server =
  `apps/server/Containerfile`, `ENV PORT=4000`, `EXPOSE 4000`,
  `CMD ["bun","apps/server/src/main.ts"]`.
- `start.sh` order today: `gateway security media contacts notes agent cpa
  garden automation dashboard` — `garden` starts **before** `automation`
  (the broker).

## Changes

### 1. `garden/docker-compose.yml` — rewrite the services

Replace both `hort` and `hort2` with:

```yaml
services:
  hort:
    build:
      context: https://github.com/masolnada/automated-fertigation-system.git#main:web
      dockerfile: apps/dashboard/Containerfile
    container_name: hort
    restart: unless-stopped
    networks:
      - proxy_net

  hort-server:
    build:
      context: https://github.com/masolnada/automated-fertigation-system.git#main:web
      dockerfile: apps/server/Containerfile
    container_name: hort-server
    restart: unless-stopped
    environment:
      - MQTT_URL=mqtt://mosquitto:1883
      - MQTT_USERNAME=${MQTT_USERNAME}
      - MQTT_PASSWORD=${MQTT_PASSWORD}
      - MQTT_PREFIX=kc868-a8
      - PORT=4000
    networks:
      - proxy_net

networks:
  proxy_net:
    external: true
```

- The dashboard carries **no env** (static artifact).
- `hort-server` exposes `4000` on `proxy_net` (no host port publish needed;
  Caddy reaches it over the network).

### 2. `gateway/Caddyfile` — path-split `hort`, remove `hort2`

Replace the `@hort` block and **delete** the `@hort2` block with a single
`route`-ordered handler (SSE needs immediate flushing):

```caddy
@hort host hort.{$DOMAIN}
handle @hort {
	route {
		@hort_api path /api/*
		reverse_proxy @hort_api hort-server:4000 {
			flush_interval -1
		}
		reverse_proxy hort:80
	}
}
```

- `route` preserves written order so `/api/*` is matched before the catch-all.
- `flush_interval -1` disables response buffering so SSE (`GET /api/stream`) is
  delivered incrementally.
- Verify with `caddy validate` / `caddy adapt` (or `caddy fmt`) before deploy.

### 3. `garden/.env.example` — server creds only

```
MQTT_USERNAME=
MQTT_PASSWORD=
```

Drop `DOMAIN` (the new `garden` compose no longer interpolates it; Caddy carries
`DOMAIN` in the `gateway` stack). Keep the real values in the gitignored
`garden/.env` on the server (same broker creds mosquitto uses).

### 4. `start.sh` — start the broker before the server

Reorder so `automation` (mosquitto) precedes `garden`:

```
for stack in gateway security media contacts notes agent cpa automation garden dashboard; do
```

Low-risk correctness fix; without it `hort-server` just retries until the broker
is up (`mqtt.js` reconnect), but ordering avoids the initial error burst.

### 5. `README.md` — update the garden/architecture description

- Under **Architecture**, change the fertigation entry to describe the
  two-container model: static `hort` dashboard + `hort-server` (only MQTT
  client, connects to `mosquitto:1883`), Caddy path-splitting `hort.${DOMAIN}`
  `/api/*` → `hort-server`.
- Note the browser no longer uses MQTT-over-WebSockets.
- Follow the repo convention (update README when a service changes; conventional
  commits; no co-author line).

## Non-goals / leave untouched

- **`mosquitto` `9001` websocket listener and the Caddy `@mqtt` route** are now
  unused by the dashboard but may serve other clients. Do **not** remove them
  here — flag as optional later cleanup only.
- No changes to the rest of `automation/` (telegraf/grafana/influx fertigation
  observability), the deprecated `dashboard/` folder in the fertigation repo, or
  any other stack.
- No host port publishing for `hort-server` (internal-only via Caddy).

## Verification (developer)

1. `docker compose -f garden/docker-compose.yml config` parses.
2. `caddy validate` / `caddy adapt` on the edited Caddyfile succeeds.
3. Build locally to catch context errors (optional, slow):
   `docker compose -f garden/docker-compose.yml build`.
4. Post-deploy smoke (on the server, after the fertigation push):
   - `curl -s https://hort.${DOMAIN}/api/health` → `{"ok":true}`.
   - Load `https://hort.${DOMAIN}` — dashboard renders, live values arrive.
   - `curl -N https://hort.${DOMAIN}/api/stream` streams `data:` snapshots
     incrementally (SSE not buffered).
   - Issue one command from the UI and confirm the device reacts and the
     snapshot updates.

## Deployment (per repo CLAUDE.md)

1. **First** push the fertigation `web/` changes to `main` (prerequisite above).
2. Commit the homelab changes (conventional commit, no co-author line), push.
3. On the server: `cd /opt/homelab && sudo git pull`.
4. Restart affected stacks:
   `sudo docker compose -f automation/docker-compose.yml up -d` (if start order
   matters), `sudo docker compose -f garden/docker-compose.yml up -d --build`,
   and reload gateway: `sudo docker compose -f gateway/docker-compose.yml up -d`
   (or `caddy reload`). `--build` picks up the new remote git context.

## Definition of done

- `garden/` runs `hort` (static) + `hort-server` (Express); old `hort`/`hort2`
  gone; images build from the fertigation `main` `web` context.
- Caddy serves `hort.${DOMAIN}`: `/api/*` → `hort-server:4000` (SSE unbuffered),
  everything else → `hort:80`. `@hort2` route removed.
- `hort-server` connects to `mqtt://mosquitto:1883` with the shared creds.
- `garden/.env.example`, `start.sh` order, and `README.md` updated.
- Smoke checks pass end-to-end from the browser through to the device.
