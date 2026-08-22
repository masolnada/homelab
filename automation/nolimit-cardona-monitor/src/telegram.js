import { config } from "./config.js";

const BASE = `https://api.telegram.org/bot${config.telegramToken}`;
const MAX_LEN = 4000; // Telegram hard limit is 4096; leave margin.

async function sendChunk(text, chatId) {
  const res = await fetch(`${BASE}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: "HTML",
      disable_web_page_preview: true,
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    const err = new Error(`Telegram sendMessage failed: ${res.status} ${detail}`);
    err.status = res.status;
    throw err;
  }
}

// Send a message, splitting on line boundaries if it exceeds the limit.
export async function sendMessage(text, chatId = config.telegramChatId) {
  if (text.length <= MAX_LEN) {
    await sendChunk(text, chatId);
    return;
  }
  const lines = text.split("\n");
  let buffer = "";
  for (const line of lines) {
    if ((buffer + "\n" + line).length > MAX_LEN) {
      await sendChunk(buffer, chatId);
      buffer = line;
    } else {
      buffer = buffer ? `${buffer}\n${line}` : line;
    }
  }
  if (buffer) await sendChunk(buffer, chatId);
}

// Long-poll for incoming updates. Returns an array of updates.
export async function getUpdates(offset, timeoutSec = 30) {
  const res = await fetch(`${BASE}/getUpdates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      offset,
      timeout: timeoutSec,
      allowed_updates: ["message", "my_chat_member"],
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Telegram getUpdates failed: ${res.status} ${detail}`);
  }
  const data = await res.json();
  return data.result ?? [];
}

// Register the bot command menu shown in Telegram clients.
export async function setMyCommands(commands) {
  await fetch(`${BASE}/setMyCommands`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ commands }),
  }).catch(() => {});
}
