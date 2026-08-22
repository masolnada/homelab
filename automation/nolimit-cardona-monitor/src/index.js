import { config } from "./config.js";
import { fetchSessions } from "./api.js";
import { loadState, saveState } from "./state.js";
import { diffSessions, CATEGORY_ORDER } from "./diff.js";
import { sendMessage, getUpdates, setMyCommands } from "./telegram.js";
import { formatSchedule } from "./format.js";
import { addSubscriber, removeSubscriber, getSubscribers } from "./subscribers.js";

// Build a grouped, easy-to-read HTML message from the change list.
function buildMessage(changes, count) {
  const byCategory = new Map();
  for (const { category, block } of changes) {
    if (!byCategory.has(category)) byCategory.set(category, []);
    byCategory.get(category).push(block);
  }

  const noun = changes.length === 1 ? "change" : "changes";
  const parts = [`🏋️ <b>No Limit Cardona</b>`, `${changes.length} ${noun} - ${count} classes tracked`];

  for (const category of CATEGORY_ORDER) {
    const blocks = byCategory.get(category);
    if (!blocks || blocks.length === 0) continue;
    parts.push("");
    parts.push(`<b>${category}</b>`);
    parts.push(blocks.join("\n\n"));
  }
  return parts.join("\n");
}

const runOnce = process.argv.includes("--once");

function log(...args) {
  console.log(new Date().toISOString(), ...args);
}

// Send a message to every subscribed chat, pruning chats that block or remove
// the bot (403 forbidden / 400 chat not found).
async function broadcast(text) {
  const subs = await getSubscribers();
  if (subs.size === 0) log("No subscribers yet; message not delivered.");
  for (const chatId of subs) {
    try {
      await sendMessage(text, chatId);
    } catch (err) {
      if (err.status === 403 || err.status === 400) {
        await removeSubscriber(chatId);
        log(`Removed unreachable chat ${chatId} (${err.status}).`);
      } else {
        log(`Send to ${chatId} failed:`, err.message);
      }
    }
  }
}

async function poll() {
  const prev = await loadState();
  const { sessions, from, until } = await fetchSessions();
  const count = Object.keys(sessions).length;

  if (prev === null) {
    // First run: establish baseline silently, do not spam every class as "new".
    await saveState(sessions);
    log(`Baseline stored: ${count} classes for week ${from} to ${until}.`);
    return;
  }

  const changes = diffSessions(prev, sessions);
  if (changes.length > 0) {
    log(`${changes.length} change(s) detected.`);
    await broadcast(buildMessage(changes, count));
  } else {
    log(`No changes. ${count} classes tracked.`);
  }
  await saveState(sessions);
}

// Current hour (0-23) in the configured timezone.
function currentHour() {
  const h = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    hourCycle: "h23",
    timeZone: config.timezone,
  }).format(new Date());
  return Number(h);
}

function withinActiveHours() {
  const h = currentHour();
  return h >= config.activeStartHour && h < config.activeEndHour;
}

async function pollLoop() {
  for (;;) {
    if (withinActiveHours()) {
      try {
        await poll();
      } catch (err) {
        log("Poll failed:", err.message);
      }
    } else {
      log(`Outside active hours (${config.activeStartHour}:00-${config.activeEndHour}:00). Skipping poll.`);
    }
    await new Promise((r) => setTimeout(r, config.pollIntervalMs));
  }
}

async function handleCommand(text, chatId) {
  const command = text.trim().split(/\s+/)[0].split("@")[0].toLowerCase();
  if (command === "/gym") {
    const { sessions, from, until } = await fetchSessions();
    await sendMessage(formatSchedule(sessions, from, until), chatId);
  } else if (command === "/gym_tracker_status") {
    const { sessions, from, until } = await fetchSessions();
    const count = Object.keys(sessions).length;
    await sendMessage(
      `🏋️ <b>No Limit Cardona</b>\nTracker running - tracking ${count} classes for the week ${from} to ${until}.`,
      chatId
    );
  } else if (command === "/start") {
    await sendMessage(
      "🏋️ <b>No Limit Cardona</b>\nYou are subscribed. I will notify this chat about class changes. Send /gym to see this week's classes.",
      chatId
    );
  }
}

// Handle bot being added to or removed from a chat.
async function handleMembership(update) {
  const chat = update.my_chat_member.chat;
  const status = update.my_chat_member.new_chat_member?.status;
  if (["member", "administrator", "creator"].includes(status)) {
    if (await addSubscriber(chat.id)) log(`Subscribed chat ${chat.id} (${chat.type}).`);
  } else if (["left", "kicked"].includes(status)) {
    if (await removeSubscriber(chat.id)) log(`Unsubscribed chat ${chat.id} (${chat.type}).`);
  }
}

// Long-poll for commands and membership changes. Responds in every chat that
// interacts with the bot and auto-subscribes them.
async function commandLoop() {
  await setMyCommands([
    { command: "gym", description: "Show this week's classes" },
    { command: "gym_tracker_status", description: "Show tracker status" },
  ]);
  let offset;
  for (;;) {
    try {
      const updates = await getUpdates(offset);
      for (const update of updates) {
        offset = update.update_id + 1;
        if (update.my_chat_member) {
          await handleMembership(update);
          continue;
        }
        const msg = update.message;
        if (!msg || !msg.text) continue;
        if (await addSubscriber(msg.chat.id)) log(`Subscribed chat ${msg.chat.id} (${msg.chat.type}).`);
        await handleCommand(msg.text, msg.chat.id);
      }
    } catch (err) {
      log("Command loop error:", err.message);
      await new Promise((r) => setTimeout(r, 5000));
    }
  }
}

async function main() {
  log(`Monitor starting. Endpoint: ${config.scheduleUrl}`);
  if (config.telegramChatId) await addSubscriber(config.telegramChatId);
  if (runOnce) {
    await poll();
    return;
  }
  await Promise.all([pollLoop(), commandLoop()]);
}

main().catch((err) => {
  log("Fatal:", err.message);
  process.exit(1);
});
