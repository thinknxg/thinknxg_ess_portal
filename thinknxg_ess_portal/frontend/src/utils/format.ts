export function initials(name?: string | null) {
  return (name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
}

export function toneFor(status?: string | null): "ok" | "warn" | "bad" | "info" | "muted" {
  const s = (status || "").toLowerCase();
  if (["approved", "present", "resolved", "closed", "generated", "acknowledged", "confirmed", "paid", "on track", "checked in", "completed"].includes(s)) return "ok";
  if (["rejected", "absent", "breached", "failed", "overdue", "cancelled", "missing"].includes(s)) return "bad";
  if (["pending", "open", "draft", "at risk", "waiting for employee", "pending approval", "queued", "late", "requested", "unmarked", "not checked in"].includes(s)) return "warn";
  if (["in progress", "assigned", "on leave", "half day", "work from home", "approved" ].includes(s)) return "info";
  return "muted";
}

export function isoToday() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function addDays(iso: string, n: number) {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Minutes since midnight from "HH:MM[:SS]" or a datetime string. */
export function minutesOf(t?: string | null) {
  if (!t) return null;
  const m = t.match(/(\d{1,2}):(\d{2})/);
  return m ? +m[1] * 60 + +m[2] : null;
}
