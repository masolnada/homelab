import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";
import { config } from "./config.js";

export async function loadState() {
  try {
    const raw = await readFile(config.stateFile, "utf8");
    const parsed = JSON.parse(raw);
    return parsed.sessions ?? {};
  } catch (err) {
    if (err.code === "ENOENT") return null; // first run
    throw err;
  }
}

export async function saveState(sessions) {
  await mkdir(dirname(config.stateFile), { recursive: true });
  const payload = { updatedAt: new Date().toISOString(), sessions };
  await writeFile(config.stateFile, JSON.stringify(payload, null, 2));
}
