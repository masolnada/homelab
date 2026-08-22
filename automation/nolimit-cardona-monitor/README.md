# nolimit-cardona-monitor (vendored)

Telegram bot that monitors the No Limit Cardona (Trainin) class schedule and
notifies subscribed chats when classes change. Built locally by the
`automation` stack (`build: ./nolimit-cardona-monitor`), no registry.

Canonical source: https://github.com/masolnada/nolimit-cardona-monitor
Update this copy from there, then commit and rebuild:

```sh
docker compose -f automation/docker-compose.yml up -d --build nolimit-cardona-monitor
```

Commands: `/gym` (this week's classes), `/gym_tracker_status` (tracker status).
Config via the `automation` stack `.env` (`NOLIMIT_TELEGRAM_BOT_TOKEN`,
`NOLIMIT_TELEGRAM_CHAT_ID`). State persists in the `nolimit_cardona_data` volume.
