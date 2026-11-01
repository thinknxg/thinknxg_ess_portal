/**
 * Central thinkNXG request wrapper. Same-origin session auth + CSRF token; no API keys in the browser.
 */
export class ApiError extends Error {
  status: number;
  type: string;
  constructor(message: string, status = 0, type = "Error") {
    super(message);
    this.status = status;
    this.type = type;
  }
  get isPermission() { return this.status === 403 || this.type === "PermissionError"; }
  get isNotFound() { return this.status === 404 || this.type === "DoesNotExistError"; }
  get isAuth() { return this.status === 401 || this.type === "AuthenticationError" || this.type === "SessionExpired"; }
  get isOffline() { return this.type === "Offline"; }
}

const PREFIX = "thinknxg_ess_portal.api.";

function stripHtml(s: string) {
  const d = document.createElement("div");
  d.innerHTML = s;
  return (d.textContent || "").trim();
}

function extractMessage(body: any, fallback: string): string {
  try {
    if (body?._server_messages) {
      const msgs = JSON.parse(body._server_messages).map((m: string) => {
        try { return JSON.parse(m).message; } catch { return m; }
      });
      if (msgs.length) return stripHtml(msgs.join("\n"));
    }
    if (body?.exception) return stripHtml(String(body.exception).split(":").slice(1).join(":") || body.exception);
    if (body?.message && typeof body.message === "string") return stripHtml(body.message);
  } catch { /* fallthrough */ }
  return fallback;
}

function encodeParams(params?: Record<string, any>) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params || {})) {
    if (v === undefined || v === null) continue;
    q.set(k, typeof v === "object" ? JSON.stringify(v) : String(v));
  }
  return q.toString();
}

async function handle<T>(res: Response): Promise<T> {
  let body: any = null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) body = await res.json();
  if (!res.ok) {
    const type = body?.exc_type || (res.status === 403 ? "PermissionError" : res.status === 404 ? "DoesNotExistError" : "Error");
    const message = extractMessage(body, res.status === 403 ? "You don't have access to this." : `Request failed (${res.status})`);
    if (res.status === 401 || type === "SessionExpired") {
      window.dispatchEvent(new CustomEvent("ess:session-expired"));
    }
    throw new ApiError(message, res.status, type);
  }
  return (body?.message ?? body) as T;
}

export async function get<T = any>(method: string, params?: Record<string, any>): Promise<T> {
  if (!navigator.onLine) throw new ApiError("You're offline. Reconnect to load this.", 0, "Offline");
  const qs = encodeParams(params);
  const res = await fetch(`/api/method/${PREFIX}${method}${qs ? `?${qs}` : ""}`, {
    headers: { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token || "" },
    credentials: "same-origin",
  });
  return handle<T>(res);
}

export async function post<T = any>(method: string, params?: Record<string, any>): Promise<T> {
  if (!navigator.onLine) throw new ApiError("You're offline. Your request was not sent.", 0, "Offline");
  const body: Record<string, any> = {};
  for (const [k, v] of Object.entries(params || {})) if (v !== undefined) body[k] = typeof v === "object" && v !== null ? JSON.stringify(v) : v;
  const res = await fetch(`/api/method/${PREFIX}${method}`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json", "X-Frappe-CSRF-Token": window.csrf_token || "" },
    credentials: "same-origin",
    body: JSON.stringify(body),
  });
  return handle<T>(res);
}

export function requestId(): string {
  if (crypto && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

/** Upload a private file via thinkNXG's upload_file; returns the file_url to attach server-side. */
export async function uploadPrivate(file: File): Promise<string> {
  if (file.size > 10 * 1024 * 1024) throw new ApiError("Files must be 10 MB or smaller.");
  const fd = new FormData();
  fd.append("file", file, file.name);
  fd.append("is_private", "1");
  fd.append("folder", "Home/Attachments");
  const res = await fetch("/api/method/upload_file", {
    method: "POST", body: fd, credentials: "same-origin",
    headers: { "X-Frappe-CSRF-Token": window.csrf_token || "", Accept: "application/json" },
  });
  const data = await handle<{ file_url: string }>(res);
  return data.file_url;
}

export function downloadUrl(method: string, params: Record<string, any>) {
  return `/api/method/${PREFIX}${method}?${encodeParams(params)}`;
}
