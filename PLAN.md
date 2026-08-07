# Add InfluxDB + Grafana (+ Telegraf) to the automation stack

## Context

A new Zigbee temperature/humidity sensor (`marcscave-temp-sensor`) publishes via Zigbee2MQTT to Mosquitto, but nothing stores or visualizes the readings. Add a metrics pipeline to the `automation/` stack: **Telegraf** subscribes to both z2m base topics and writes to **InfluxDB 2.x**; **Grafana** (exposed at `grafana.<DOMAIN>`) visualizes it with a git-provisioned datasource and starter dashboard.

Decisions already made with the user: InfluxDB 2.x; Telegraf collects **all** devices on both base topics (not just the one sensor); **no** backup sidecars (matches rest of automation stack); pre-provision a marcscave-temp-sensor dashboard.

## Data flow & schema

`z2m → mosquitto → telegraf (mqtt_consumer) → influxdb → grafana (Flux)`

- Topics: `zigbee2mqtt-baixos/+` and `zigbee2mqtt-pis/+`. Single-level `+` deliberately skips `bridge/...` and `<device>/availability` topics (2+ levels).
- Mosquitto requires auth (`allow_anonymous false`) — Telegraf reuses `${MQTT_USERNAME}`/`${MQTT_PASSWORD}`.
- Schema: measurement `zigbee`, tags `base_topic` + `device` (parsed from topic), float fields (`temperature`, `humidity`, `battery`, `linkquality`, `voltage`, …).
- Parser: classic `json` parser — numeric values only, strings/booleans **dropped silently** (deliberate: uniform float types, no Influx type conflicts; comment in conf explains how to add them later via `json_string_fields` + converter for future door/motion sensors).
- Grafana datasource uses **Flux** (works out of the box with InfluxDB 2 token auth; InfluxQL would need a manual DBRP mapping).

## Files

### New files
1. **`automation/telegraf/telegraf.conf`** — agent (10s interval, `omit_hostname = true`), `[[inputs.mqtt_consumer]]` (servers `tcp://mosquitto:1883`, both topics, `${MQTT_USERNAME}`/`${MQTT_PASSWORD}`, `data_format = "json"`, `name_override = "zigbee"`, `topic_parsing` with `topic = "+/+"`, `tags = "base_topic/device"`), `[[outputs.influxdb_v2]]` (url `http://influxdb:8086`, `${INFLUXDB_TOKEN}`/`${INFLUXDB_ORG}`/`${INFLUXDB_BUCKET}`).
2. **`automation/grafana/provisioning/datasources/influxdb.yaml`** — InfluxDB datasource, uid `influxdb-zigbee`, url `http://influxdb:8086`, `jsonData.version: Flux`, org/bucket/token via `$INFLUXDB_*` env interpolation (token never in git), `isDefault: true`.
3. **`automation/grafana/provisioning/dashboards/provider.yaml`** — file provider, folder `Zigbee`, path `/var/lib/grafana/dashboards`, `allowUiUpdates: true`.
4. **`automation/grafana/dashboards/marcscave-temp-sensor.json`** — 4 panels: Temperature + Humidity (timeseries, top row), Battery + Link Quality (stat, bottom). Flux queries filter `r._measurement == "zigbee" and r.device == "marcscave-temp-sensor" and r._field == "<field>"` with `aggregateWindow(every: v.windowPeriod, fn: mean)` (stats: `last` + `lastNotNull`). Note: bucket name `zigbee` is hard-coded in these queries — must match `INFLUXDB_BUCKET`.

### Edited files
5. **`automation/docker-compose.yml`** — append 3 services after `z2m-pis` + 3 named volumes (`influxdb_data`, `influxdb_config`, `grafana_data`):
   - **influxdb** — `influxdb:2.7` (NOT `latest` = InfluxDB 3), `DOCKER_INFLUXDB_INIT_MODE=setup` + `INIT_USERNAME/PASSWORD/ORG/BUCKET/ADMIN_TOKEN` from env, `INIT_RETENTION=0`, volumes `influxdb_data:/var/lib/influxdb2` + `influxdb_config:/etc/influxdb2`, healthcheck `influx ping`.
   - **telegraf** — `telegraf:1.35`, `depends_on: mosquitto (started), influxdb (healthy)`, env passthrough of MQTT + INFLUXDB vars, bind mount `./telegraf/telegraf.conf:/etc/telegraf/telegraf.conf:ro`.
   - **grafana** — `grafana/grafana:12.0`, `depends_on influxdb (healthy)`, env: `GF_SECURITY_ADMIN_USER/PASSWORD`, `GF_SERVER_ROOT_URL=https://grafana.${DOMAIN}`, `GF_USERS_ALLOW_SIGN_UP=false`, `GF_ANALYTICS_REPORTING_ENABLED=false`, `TZ`, plus `INFLUXDB_TOKEN/ORG/BUCKET` (consumed by provisioning yaml); volumes `grafana_data:/var/lib/grafana`, `./grafana/provisioning:/etc/grafana/provisioning:ro`, `./grafana/dashboards:/var/lib/grafana/dashboards:ro`.
   - All on `proxy_net`, comment style matching existing services.
6. **`automation/.env.example`** — append: `INFLUXDB_USERNAME=admin`, `INFLUXDB_PASSWORD=`, `INFLUXDB_ORG=homelab`, `INFLUXDB_BUCKET=zigbee`, `INFLUXDB_TOKEN=` (comment: `openssl rand -hex 32`; init runs only on empty volume), `GRAFANA_ADMIN_USER=admin`, `GRAFANA_ADMIN_PASSWORD=` (first-boot only), `DOMAIN=` (new to this stack; must match gateway/.env, needed for GF_SERVER_ROOT_URL).
7. **`gateway/Caddyfile`** — before the final `handle { abort }` (Caddyfile:87):
   ```
   @grafana host grafana.{$DOMAIN}
   handle @grafana {
       reverse_proxy grafana:3000
   }
   ```
8. **`dashboard/config/services.yaml`** — Grafana tile in the Automation group (after Zigbee2MQTT (pis), before Mosquitto): icon `grafana`, href/description `grafana.{{HOMEPAGE_VAR_DOMAIN}}`, `siteMonitor: http://grafana:3000`, `server: my-docker`, `container: grafana`.
9. **`README.md`** — extend the Automation architecture bullet (Telegraf bridges both z2m topics → InfluxDB 2 bucket `zigbee`, numeric fields only, tagged by device; Grafana at `grafana.<DOMAIN>` with git-provisioned datasource + dashboards; volumes).

## Deployment (after commit + push)

1. On server: add the new keys to `/opt/homelab/automation/.env` (generate token with `openssl rand -hex 32`, set `DOMAIN` to match gateway/.env) — **before** `up -d`, since InfluxDB init only runs against an empty volume.
2. `sudo git pull`, then `sudo docker compose -f automation/docker-compose.yml up -d`.
3. Force-recreate caddy (bind-mount inode gotcha): `sudo docker compose -f gateway/docker-compose.yml up -d --force-recreate caddy`.

## Verification

1. `docker compose -f automation/docker-compose.yml ps` — influxdb healthy, telegraf/grafana up.
2. `docker logs telegraf` — `Connected [tcp://mosquitto:1883]`, no auth/parse spam.
3. Sensor publishing: `docker exec mosquitto mosquitto_sub -u ... -t 'zigbee2mqtt-baixos/marcscave-temp-sensor' -C 1 -v` (adjust base topic to whichever coordinator it's paired to; press device button to force a report).
4. Influx has points: `docker exec influxdb influx query --org homelab --token $INFLUXDB_TOKEN 'from(bucket:"zigbee") |> range(start:-1h) |> filter(fn:(r)=> r.device == "marcscave-temp-sensor") |> limit(n:5)'`.
5. `https://grafana.<DOMAIN>` — login, datasource green, Zigbee folder → dashboard renders all 4 panels.
6. Homepage shows the Grafana tile with green monitor dot.

## Pitfalls to remember during implementation

- InfluxDB `DOCKER_INFLUXDB_INIT_*` and Grafana admin password are **first-boot-only** (wrong creds → `down` + `docker volume rm automation_influxdb_data` to retry).
- Datasource yaml must reference `$INFLUXDB_TOKEN`, never a literal (file is committed).
- If the sensor isn't paired/renamed yet, panels stay empty until it is — pairing in the z2m frontend is a user step, not part of this change.
