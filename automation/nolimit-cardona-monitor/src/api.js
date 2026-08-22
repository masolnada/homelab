import { config } from "./config.js";

// Fetch the current-week schedule from the public Trainin endpoint and
// return a map of normalized sessions keyed by session id.
export async function fetchSessions() {
  const res = await fetch(config.scheduleUrl, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Schedule request failed: ${res.status} ${res.statusText}`);
  }
  const body = await res.json();

  const bookableById = new Map(
    (body.items ?? []).map((item) => [String(item.session_id), Boolean(item.bookable)])
  );

  const sessions = {};
  for (const entry of body.data ?? []) {
    const a = entry.attributes ?? {};
    const id = String(entry.id);
    sessions[id] = {
      id,
      title: a.title ?? a.name ?? "(untitled)",
      start: a.start ?? null,
      end: a.end ?? null,
      instructors: Array.isArray(a.instructor_names) ? a.instructor_names.join(", ") : "",
      location: a.location_name ?? "",
      freeSpots: a.free_spots ?? 0,
      reserved: a.group_size_reserved ?? 0,
      max: a.group_size_max ?? 0,
      hasWaitingList: Boolean(a.has_waiting_list),
      hasActiveWaitingList: Boolean(a.has_active_waiting_list),
      bookable: bookableById.get(id) ?? false,
    };
  }
  return { sessions, from: body.from, until: body.until };
}
