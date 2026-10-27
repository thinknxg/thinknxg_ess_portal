/**
 * Offline queue for low-risk submissions (leave requests, HR tickets, recognition).
 * Check-in/out and approvals are never queued: they need live server confirmation.
 * Each entry keeps its client request id, so replaying is idempotent on the server.
 * Only the minimum payload is stored, in this browser only, and removed once confirmed.
 */
import { reactive } from "vue";
import { post, requestId, ApiError } from "./api";

export type QueueState = "queued" | "sending" | "failed";
export interface QueuedAction {
  id: string; method: string; label: string; params: Record<string, any>; state: QueueState;
  created: string; error?: string;
}

const KEY = "ess_offline_queue_v1";
const QUEUEABLE = new Set(["leave.create_request", "helpdesk.create_ticket", "recognition.give"]);

function load(): QueuedAction[] {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}

export const queue = reactive<{ items: QueuedAction[] }>({ items: load() });

function persist() {
  try { localStorage.setItem(KEY, JSON.stringify(queue.items)); } catch { /* storage unavailable */ }
}

export function canQueue(method: string) { return QUEUEABLE.has(method); }

export function enqueue(method: string, params: Record<string, any>, label: string): QueuedAction {
  if (!canQueue(method)) throw new ApiError("This action needs a connection.", 0, "Offline");
  const item: QueuedAction = {
    id: params.client_request_id || requestId(), method, label,
    params: { ...params, client_request_id: params.client_request_id || requestId() },
    state: "queued", created: new Date().toISOString(),
  };
  queue.items.push(item);
  persist();
  return item;
}

export function discard(id: string) {
  queue.items = queue.items.filter((i) => i.id !== id);
  persist();
}

let flushing = false;
export async function flush(onDone?: (item: QueuedAction, result: any) => void) {
  if (flushing || !navigator.onLine) return;
  flushing = true;
  try {
    for (const item of [...queue.items]) {
      item.state = "sending";
      try {
        const result = await post(item.method, item.params);
        discard(item.id);
        onDone?.(item, result);
      } catch (e: any) {
        item.state = "failed";
        item.error = e?.message || "Could not send";
        persist();
        if (e instanceof ApiError && e.isOffline) break;
      }
    }
  } finally {
    flushing = false;
  }
}

export function clearQueueOnLogout() {
  queue.items = [];
  try { localStorage.removeItem(KEY); } catch { /* ignore */ }
}
