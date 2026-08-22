import { config } from "./config.js";
import { detailBlock, whenShort, spotsText, escapeHtml } from "./format.js";

// Category display order in the final message.
export const CATEGORY_ORDER = [
  "🆕 New classes",
  "🟢 Spots opened up",
  "🔴 Now full",
  "🔄 Rescheduled",
  "✏️ Renamed",
  "🔢 Spots changed",
  "❌ Removed",
];

// Compare previous and current session maps and return a list of
// { category, block } changes. `block` is an HTML-formatted detail block.
export function diffSessions(prev, curr) {
  const changes = [];
  const prevIds = new Set(Object.keys(prev));
  const currIds = new Set(Object.keys(curr));

  const add = (category, block) => changes.push({ category, block });

  for (const id of currIds) {
    if (!prevIds.has(id)) add("🆕 New classes", detailBlock(curr[id]));
  }

  for (const id of prevIds) {
    if (!currIds.has(id)) {
      const s = prev[id];
      add("❌ Removed", `<b>${escapeHtml(s.title)}</b>\n${escapeHtml(whenShort(s))}`);
    }
  }

  for (const id of currIds) {
    if (!prevIds.has(id)) continue;
    const a = prev[id];
    const b = curr[id];

    if (a.start !== b.start || a.end !== b.end) {
      add("🔄 Rescheduled", detailBlock(b, [`Was: ${whenShort(a)}`]));
    }
    if (a.title !== b.title) {
      add("✏️ Renamed", detailBlock(b, [`Was: ${a.title}`]));
    }

    const wasFull = a.freeSpots <= 0;
    const isFull = b.freeSpots <= 0;
    if (!wasFull && isFull) {
      add("🔴 Now full", detailBlock(b));
    } else if (wasFull && !isFull) {
      add("🟢 Spots opened up", detailBlock(b));
    } else if (config.notifyEverySpotChange && a.freeSpots !== b.freeSpots) {
      add("🔢 Spots changed", detailBlock(b, [`Was: ${spotsText(a)}`]));
    }
  }

  return changes;
}
