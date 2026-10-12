# Home device alerts

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
Unchanged values count as reports. Telegraf collects the ESPHome reports as
`esphome_heartbeat` and Shelly instantaneous readings as `shelly_em`.

Each outage sends one Telegram notification using the existing Gatus bot.
Reminders are disabled; recovery sends one notification and re-arms the
alert. Detection and recovery can take up to 5 minutes after the threshold
or a new report, plus Telegraf's flush delay.

Set `GATUS_INFLUXDB_TOKEN` in `automation/.env` to an InfluxDB token with
read-only access to `INFLUXDB_BUCKET`. Gatus also receives `INFLUXDB_ORG`
and `INFLUXDB_BUCKET` from that file. Never commit the token.

No persistent storage or maintenance controls are used. Restarting Gatus
can repeat an outage alert or lose a pending recovery notification. MQTT
retained reports can temporarily make an offline ESPHome device look
healthy after Telegraf reconnects; the next 3-hour silence reveals it again.
An InfluxDB/query failure can fail all device checks at once. These checks
monitor reporting, not motor operation or sensor accuracy.

## Validation

After deploying, confirm all 20 device checks across the five groups show
`success=true` in Gatus logs. Test the same Flux query with a nonexistent device name:
it must return no `home_device_reporting` marker, while a recently reporting
device must return that marker. This checks missing-device detection without
turning off equipment or sending a synthetic Telegram outage.

The existing Milverds heartbeat check and its notification settings remain
independent and unchanged.
