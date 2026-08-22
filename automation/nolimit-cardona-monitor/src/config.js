function required(name) {
  const value = process.env[name];
  if (!value) {
    console.error(`Missing required environment variable: ${name}`);
    process.exit(1);
  }
  return value;
}

function optional(name, fallback) {
  const value = process.env[name];
  return value === undefined || value === "" ? fallback : value;
}

const businessHid = optional("BUSINESS_HID", "A3OAY");
const baseUrl = optional("BASE_URL", "https://nolimitcardona.trainin.app").replace(/\/$/, "");

export const config = {
  baseUrl,
  businessHid,
  scheduleUrl: `${baseUrl}/api/v2/${businessHid}/client/schedule`,
  telegramToken: required("TELEGRAM_BOT_TOKEN"),
  // Optional seed chat. The bot also auto-subscribes any chat it joins or that
  // sends /start or /gym, and broadcasts to all of them.
  telegramChatId: optional("TELEGRAM_CHAT_ID", ""),
  pollIntervalMs: Number(optional("POLL_INTERVAL_SECONDS", "600")) * 1000,
  // Only poll within this hour window (in `timezone`). Default 08:00 to 24:00.
  activeStartHour: Number(optional("ACTIVE_START_HOUR", "8")),
  activeEndHour: Number(optional("ACTIVE_END_HOUR", "24")),
  stateFile: optional("STATE_FILE", "/data/state.json"),
  subscribersFile: optional("SUBSCRIBERS_FILE", "/data/subscribers.json"),
  // Notify on every free-spot change, not only full <-> available transitions.
  notifyEverySpotChange: optional("NOTIFY_EVERY_SPOT_CHANGE", "false") === "true",
  timezone: optional("TZ", "Europe/Madrid"),
};
