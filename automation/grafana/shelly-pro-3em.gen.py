#!/usr/bin/env python3
"""Generates the Shelly Pro 3EM Grafana dashboard JSON.

Written as a generator rather than by hand because the same three channels
repeat across seven panels; keeping the channel table in one place is what
stops the colours and labels drifting apart between panels.
"""
import json

BUCKET = "zigbee"
DS = {"type": "influxdb", "uid": "influxdb-zigbee"}

# (suffix, label, colour) — the physical CT clamp assignment.
CHANNELS = [
    ("a", "Whole flat", "blue"),
    ("b", "Fireplace fan", "orange"),
    ("c", "Water heater", "green"),
]

_id = [0]
def nid():
    _id[0] += 1
    return _id[0]


def flux(field, measurement="shelly_em", fn="mean", extra=""):
    return (
        f'from(bucket: "{BUCKET}")\n'
        f"  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
        f'  |> filter(fn: (r) => r._measurement == "{measurement}" and r._field == "{field}")\n'
        f"  |> aggregateWindow(every: v.windowPeriod, fn: {fn}, createEmpty: false)\n"
        f"{extra}"
        f'  |> keep(columns: ["_time", "_value"])'
    )


def target(query, name, ref):
    # yield(name:) is what Grafana uses to label the frame — same convention as
    # the existing marcscave dashboard in this folder.
    return {"datasource": DS, "query": query + f'\n  |> yield(name: "{name}")', "refId": ref}


def colour_overrides():
    return [
        {
            "matcher": {"id": "byName", "options": label},
            "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": colour}}],
        }
        for _, label, colour in CHANNELS
    ]


def timeseries(title, field_tmpl, unit, y, h=9, w=24, x=0, include_total=False, desc=None):
    targets = []
    for i, (sfx, label, _) in enumerate(CHANNELS):
        targets.append(target(flux(field_tmpl.format(c=sfx)), label, chr(ord("A") + i)))
    if include_total:
        targets.append(target(flux("total_act_power"), "Total", "D"))
    p = {
        "id": nid(),
        "type": "timeseries",
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": DS,
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "custom": {
                    "drawStyle": "line",
                    "lineWidth": 2,
                    "fillOpacity": 8,
                    "showPoints": "never",
                    "spanNulls": True,
                    "lineInterpolation": "smooth",
                },
            },
            "overrides": colour_overrides()
            + (
                [
                    {
                        "matcher": {"id": "byName", "options": "Total"},
                        "properties": [
                            {"id": "color", "value": {"mode": "fixed", "fixedColor": "text"}},
                            {"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [8, 6]}},
                            {"id": "custom.fillOpacity", "value": 0},
                        ],
                    }
                ]
                if include_total
                else []
            ),
        },
        "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["mean", "max", "lastNotNull"]}, "tooltip": {"mode": "multi", "sort": "desc"}},
        "targets": targets,
    }
    if desc:
        p["description"] = desc
    return p


panels = []

# ---- Row 1: current power at a glance -------------------------------------
stats = [("total_act_power", "Total right now", "text")] + [
    (f"{sfx}_act_power", label, colour) for sfx, label, colour in CHANNELS
]
for i, (field, label, colour) in enumerate(stats):
    panels.append(
        {
            "id": nid(),
            "type": "stat",
            "title": label,
            "gridPos": {"h": 4, "w": 6, "x": i * 6, "y": 0},
            "datasource": DS,
            "fieldConfig": {
                "defaults": {
                    "unit": "watt",
                    "decimals": 0,
                    "color": {"mode": "fixed", "fixedColor": colour},
                },
                "overrides": [],
            },
            "options": {
                "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                "graphMode": "area",
                "colorMode": "value",
                "textMode": "auto",
            },
            "targets": [
                target(
                    f'from(bucket: "{BUCKET}")\n'
                    f"  |> range(start: -5m)\n"
                    f'  |> filter(fn: (r) => r._measurement == "shelly_em" and r._field == "{field}")\n'
                    f"  |> last()\n"
                    f'  |> keep(columns: ["_time", "_value"])',
                    label,
                    "A",
                )
            ],
        }
    )

# ---- Row 2: the main power chart ------------------------------------------
panels.append(
    timeseries(
        "Active power by channel",
        "{c}_act_power",
        "watt",
        y=4,
        h=10,
        include_total=True,
        desc="Real power drawn per CT clamp. 'Total' is the meter's own sum of the three channels.",
    )
)

# ---- Row 3: energy per hour ------------------------------------------------
energy_targets = []
for i, (sfx, label, _) in enumerate(CHANNELS):
    q = (
        f'from(bucket: "{BUCKET}")\n'
        f"  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n"
        f'  |> filter(fn: (r) => r._measurement == "shelly_emdata" and r._field == "{sfx}_total_act_energy")\n'
        f"  |> aggregateWindow(every: 1h, fn: last, createEmpty: false)\n"
        # These are monotonic lifetime counters in Wh; the per-hour consumption
        # is the difference between consecutive readings. nonNegative guards
        # against the counter resetting if the meter is ever re-flashed.
        f"  |> difference(nonNegative: true)\n"
        f"  |> map(fn: (r) => ({{r with _value: r._value / 1000.0}}))\n"
        f'  |> keep(columns: ["_time", "_value"])'
    )
    energy_targets.append(target(q, label, chr(ord("A") + i)))

panels.append(
    {
        "id": nid(),
        "type": "barchart",
        "title": "Energy per hour",
        "description": "Derived from the meter's lifetime Wh counters, so it survives Telegraf restarts and gaps — unlike integrating the power series.",
        "gridPos": {"h": 9, "w": 12, "x": 0, "y": 14},
        "datasource": DS,
        "fieldConfig": {
            "defaults": {"unit": "kwatth", "decimals": 2, "custom": {"fillOpacity": 85, "lineWidth": 0}},
            "overrides": colour_overrides(),
        },
        "options": {
            "stacking": "normal",
            "xTickLabelRotation": -45,
            "legend": {"displayMode": "list", "placement": "bottom"},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        "targets": energy_targets,
    }
)

# ---- Row 3b: power factor --------------------------------------------------
panels.append(
    timeseries(
        "Power factor",
        "{c}_pf",
        "none",
        y=14,
        h=9,
        w=12,
        x=12,
        desc="1.0 is a purely resistive load (a heater element). Motors and switch-mode supplies sit lower.",
    )
)

# ---- Row 4: diagnostics ----------------------------------------------------
panels.append(
    timeseries(
        "Voltage by channel",
        "{c}_voltage",
        "volt",
        y=23,
        h=8,
        w=12,
        x=0,
        desc="Mains should sit near 230 V on every channel that has its voltage terminal wired. A channel reading near zero cannot report power, however its CT clamp is fitted.",
    )
)
panels.append(
    timeseries(
        "Current by channel", "{c}_current", "amp", y=23, h=8, w=12, x=12,
        desc="A channel pinned at a few tens of milliamps is reading the clamp's noise floor, i.e. it is not sensing a conductor.",
    )
)

dashboard = {
    "id": None,
    "uid": "shelly-pro-3em",
    "title": "Energy — Shelly Pro 3EM",
    "description": (
        "Three-phase CT meter on Mosquitto (shellypro3em-34987a44fb48). "
        "Channels: A = whole flat, B = fireplace fan, C = water heater. "
        "Bucket name is hard-coded in the queries below and must match INFLUXDB_BUCKET in automation/.env."
    ),
    "tags": ["energy", "shelly"],
    "timezone": "browser",
    "editable": True,
    "schemaVersion": 39,
    "version": 1,
    "refresh": "30s",
    "time": {"from": "now-24h", "to": "now"},
    "panels": panels,
}

print(json.dumps(dashboard, indent=2))
