#!/usr/bin/env python3
"""One morning digest; existing InfluxDB history supplies outage/recovery state."""
import argparse
import csv
import io
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ZONE = ZoneInfo("Europe/Madrid")
SILENCE = timedelta(hours=3)


def docker_info(name):
    return json.loads(subprocess.check_output(["docker", "inspect", name]))[0]


def request(url, data=None, headers=None):
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers or {}), timeout=60) as response:
        return response.read().decode()


def summarize(devices, reports, now, previous):
    offline, recovered = [], []
    for name, group in sorted(devices.items(), key=lambda item: (item[1], item[0])):
        points = sorted(set(reports.get(name, [])))
        label = f"{group} / {name}"
        if not points or now - points[-1] >= SILENCE:
            offline.append(label)
        else:
            # Include the beginning of the query: a first report after a long silence is a recovery.
            before = previous - SILENCE
            for point in points:
                if point > previous and point - before >= SILENCE:
                    recovered.append(label)
                    break
                before = point
    if not offline and not recovered:
        return None
    parts = [f"Home devices — {now.astimezone(ZONE):%d-%m-%Y %H:%M}"]
    if offline:
        parts += ["", "No reports for 3 hours:", *[f"- {name}" for name in offline]]
    if recovered:
        parts += ["", "Reporting again after an outage since the previous morning:", *[f"- {name}" for name in recovered]]
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print the digest without sending Telegram")
    args = parser.parse_args()
    gatus = docker_info("gatus")
    env = dict(item.split("=", 1) for item in gatus["Config"]["Env"])
    network = gatus["NetworkSettings"]["Networks"]["proxy_net"]
    statuses = json.loads(request(f"http://{network['IPAddress']}:8080/api/v1/endpoints/statuses"))
    devices = {s["name"]: s["group"] for s in statuses if s["group"] in {
        "Temperature sensors", "Shutters", "Lights & fans", "Buttons", "Energy meters"
    }}
    config = Path(__file__).with_name("config.yaml").read_text()
    endpoint_config = config.split("\nendpoints:\n", 1)[1].split("\nexternal-endpoints:", 1)[0]
    expected = set(re.findall(r"^  - name: (\S+)$", endpoint_config, re.MULTILINE))
    if not expected or set(devices) != expected:
        raise RuntimeError("Gatus has not evaluated every configured home device; refusing a partial digest")
    now = datetime.now(timezone.utc)
    previous = datetime.combine(now.astimezone(ZONE).date() - timedelta(days=1), time(8), ZONE).astimezone(timezone.utc)
    start = (previous - SILENCE).isoformat()
    stop = now.isoformat()
    query = f'''from(bucket: {json.dumps(env["INFLUXDB_BUCKET"])})
  |> range(start: time(v: "{start}"), stop: time(v: "{stop}"))
  |> filter(fn: (r) => r._measurement == "zigbee" or r._measurement == "esphome_heartbeat" or r._measurement == "shelly_em")
  |> filter(fn: (r) => contains(value: r.device, set: {json.dumps(list(devices))}))
  |> map(fn: (r) => ({{r with _value: int(v: uint(v: r._time))}}))
  |> keep(columns: ["_start", "_stop", "_time", "device", "_value"])
  |> group(columns: ["device"])
  |> aggregateWindow(every: 5m, fn: max, createEmpty: false)
  |> keep(columns: ["device", "_value"])
'''
    influx_ip = docker_info("influxdb")["NetworkSettings"]["Networks"]["proxy_net"]["IPAddress"]
    body = request(f"http://{influx_ip}:8086/api/v2/query?org={urllib.parse.quote(env['INFLUXDB_ORG'])}", query.encode(), {
        "Authorization": "Token " + env["GATUS_INFLUXDB_TOKEN"],
        "Content-Type": "application/vnd.flux", "Accept": "application/csv",
    })
    reports = {}
    for row in csv.DictReader(io.StringIO(body)):
        if row.get("device") in devices:
            reports.setdefault(row["device"], []).append(datetime.fromtimestamp(int(row["_value"]) / 1_000_000_000, timezone.utc))
    message = summarize(devices, reports, now, previous)
    if args.dry_run:
        print(message or "No issues; no message would be sent.")
    elif message:
        result = json.loads(request(f"https://api.telegram.org/bot{env['GATUS_TELEGRAM_BOT_TOKEN']}/sendMessage", json.dumps({
            "chat_id": env["GATUS_TELEGRAM_CHAT_ID"], "text": message,
        }).encode(), {"Content-Type": "application/json"}))
        if not result.get("ok"):
            raise RuntimeError("Telegram rejected the daily digest")
        print("Daily home-device digest sent")
    else:
        print("No issues; no message sent")


if __name__ == "__main__":
    main()
