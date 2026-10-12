# Home device monitoring and morning digest

Gatus checks 20 home devices every 5 minutes through InfluxDB, grouped as
Temperature sensors (6), Shutters (9), Lights & fans (3), Buttons (1), and
Energy meters (1):

- Six Zigbee temperature sensors: Dormitori, Menjador, Acollida, Bany,
  Marc's Cave and filament box 1.
- All nine shutters (`persiana-*`).
- Three light/fan controllers (`llum-ventilador-*`).
- Entrance button (`entrance-button`), using periodic numeric reports rather
  than requiring anyone to press it.
- Shelly Pro 3EM (`shellypro3em-34987a44fb48`), using `shelly_em` readings.

A device is healthy if a numeric Zigbee report, an ESPHome Wi-Fi signal
report, or a Shelly energy-meter report reached InfluxDB in the last 3 hours.
Unchanged values count as reports. Telegraf collects ESPHome reports as
`esphome_heartbeat` and Shelly instantaneous readings as `shelly_em`.

## Notifications

Individual home-device outage/recovery notifications are disabled in Gatus.
`digest.py` sends at most one aggregated Telegram message at **08:00
Europe/Madrid**, using the existing Gatus bot. It lists devices currently
silent for 3 hours and currently healthy devices that recovered after a
3-hour reporting gap since the previous morning. Healthy days stay silent.
An ongoing outage appears in each morning's digest, not as repeated instant
alerts. Milverds notifications remain independent and unchanged.

The digest gets the device inventory/groups from Gatus and reconstructs
reporting gaps from existing InfluxDB history. It uses no new persistent
storage. History is reduced to the latest real report timestamp per 5-minute
window, so recovery detection near the 3-hour boundary has up to 5 minutes
of uncertainty. An outage that remains entirely within a gap in collection
cannot be distinguished from device failure. Retained MQTT reports replayed
by Telegraf can temporarily appear fresh.

Set `GATUS_INFLUXDB_TOKEN` in `automation/.env` to a token with read-only access
to `INFLUXDB_BUCKET`; Gatus also receives `INFLUXDB_ORG` and `INFLUXDB_BUCKET`.
The digest reads these credentials and the Telegram notifier from the live
Gatus container, without printing them. Never commit tokens.

## Installation and validation

On the homelab server, after deploying the Gatus configuration:

```sh
sudo cp systemd/home-device-digest.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now home-device-digest.timer
systemctl list-timers home-device-digest.timer
sudo python3 automation/gatus/digest.py --dry-run
python3 -m unittest discover -s automation/gatus -p 'test_*.py'
```

The timer does not catch up after downtime: if the server is off at 08:00,
that day's message is skipped. No automatic retry is used, avoiding duplicate
messages after an ambiguous Telegram timeout. Check failures using
`journalctl -u home-device-digest.service`.

Confirm 20 checks are loaded; disconnected devices should remain unhealthy
on the Gatus page without sending individual notifications. Test the Flux
check with a nonexistent device: it must return no `home_device_reporting`
marker, while a recently reporting device returns it. The dry-run checks the
live Gatus inventory and InfluxDB query without sending a Telegram message.

These checks monitor reporting, not motor operation or sensor accuracy.
An unavailable Gatus or InfluxDB makes the digest fail rather than falsely
claiming all devices are healthy; it logs the failure but cannot send a
normal device digest that morning.
