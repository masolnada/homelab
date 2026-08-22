import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";
import { config } from "./config.js";

// In-memory set of chat ids (strings), persisted to disk.
let subs = null;

async function ensureLoaded() {
  if (subs) return;
  try {
    const raw = await readFile(config.subscribersFile, "utf8");
    subs = new Set((JSON.parse(raw) ?? []).map(String));
  } catch (err) {
    if (err.code !== "ENOENT") throw err;
    subs = new Set();
  }
}

async function persist() {
  await mkdir(dirname(config.subscribersFile), { recursive: true });
  await writeFile(config.subscribersFile, JSON.stringify([...subs], null, 2));
}

export async function addSubscriber(chatId) {
  await ensureLoaded();
  const id = String(chatId);
  if (subs.has(id)) return false;
  subs.add(id);
  await persist();
  return true;
}

export async function removeSubscriber(chatId) {
  await ensureLoaded();
  const id = String(chatId);
  if (!subs.has(id)) return false;
  subs.delete(id);
  await persist();
  return true;
}

export async function getSubscribers() {
  await ensureLoaded();
  return new Set(subs);
}
