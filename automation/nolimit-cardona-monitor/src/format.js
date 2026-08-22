import { config } from "./config.js";

const dayFmt = new Intl.DateTimeFormat("en-GB", {
  weekday: "short",
  day: "2-digit",
  month: "short",
  timeZone: config.timezone,
});

const dayHeaderFmt = new Intl.DateTimeFormat("en-GB", {
  weekday: "long",
  day: "2-digit",
  month: "short",
  timeZone: config.timezone,
});

const timeFmt = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: config.timezone,
});

// Trainin returns naive local times ("2026-08-24 06:40:00"), interpreted as
// wall-clock time in the configured timezone.
function toDate(value) {
  if (!value) return null;
  const d = new Date(value.replace(" ", "T"));
  return Number.isNaN(d.getTime()) ? null : d;
}

export function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// "Mon 24 Aug, 18:30-19:30"
export function whenRange(session) {
  const start = toDate(session.start);
  if (!start) return "";
  const day = dayFmt.format(start);
  const startTime = timeFmt.format(start);
  const end = toDate(session.end);
  const endTime = end ? `-${timeFmt.format(end)}` : "";
  return `${day}, ${startTime}${endTime}`;
}

// "Mon 24 Aug, 18:30"
export function whenShort(session) {
  const start = toDate(session.start);
  if (!start) return "";
  return `${dayFmt.format(start)}, ${timeFmt.format(start)}`;
}

// Full weekly listing grouped by day, sorted by start time.
export function formatSchedule(sessions, from, until) {
  const list = Object.values(sessions)
    .filter((s) => s.start)
    .sort((a, b) => a.start.localeCompare(b.start));

  const parts = ["\ud83c\udfcb\ufe0f <b>No Limit Cardona</b>"];
  if (from && until) parts.push(`This week's classes (${from} to ${until})`);

  if (list.length === 0) {
    parts.push("", "No classes scheduled this week.");
    return parts.join("\n");
  }

  let currentDay = null;
  for (const s of list) {
    const start = toDate(s.start);
    const dayKey = s.start.slice(0, 10);
    if (dayKey !== currentDay) {
      currentDay = dayKey;
      parts.push("", `\ud83d\udcc5 <b>${escapeHtml(dayHeaderFmt.format(start))}</b>`);
    }
    const time = timeFmt.format(start);
    const status =
      s.freeSpots <= 0
        ? `\ud83d\udeab 0/${s.max}${s.hasWaitingList ? " (WL)" : ""}`
        : `\u2705 ${s.freeSpots}/${s.max}`;
    parts.push(`${time} <b>${escapeHtml(s.title)}</b> - ${status}`);
  }
  return parts.join("\n");
}

export function spotsText(session) {
  if (session.max <= 0) return "";
  if (session.freeSpots <= 0) {
    const wl = session.hasWaitingList ? " (waiting list)" : "";
    return `🚫 Full - 0/${session.max}${wl}`;
  }
  return `✅ ${session.freeSpots}/${session.max} spots free`;
}

// Multi-line detail block for one class. `lead` overrides the second line
// (used by reschedule / rename to describe the transition instead of spots).
export function detailBlock(session, extraLines = []) {
  const lines = [`<b>${escapeHtml(session.title)}</b>`];
  const when = whenRange(session);
  if (when) lines.push(escapeHtml(when));
  for (const extra of extraLines) lines.push(escapeHtml(extra));
  const spots = spotsText(session);
  if (spots) lines.push(spots);
  return lines.join("\n");
}
