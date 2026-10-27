import { ref } from "vue";
import { useUi } from "@/stores/ui";
import { canQueue, enqueue } from "@/services/offlineQueue";
import { post, requestId } from "@/services/api";
import { invalidate } from "./useResource";

/**
 * Submit with an explicit lifecycle: draft -> (queued when offline) -> submitted -> confirmed.
 * "Confirmed" is shown only after the server replies; nothing is optimistic for HR transactions.
 */
export function useSubmit() {
  const state = ref<"draft" | "queued" | "submitting" | "confirmed" | "error">("draft");
  const error = ref<string | null>(null);
  const result = ref<any>(null);
  const ui = useUi();

  async function submit(method: string, params: Record<string, any>, label: string, invalidates: string[] = []) {
    const cid = params.client_request_id || requestId();
    const payload = { ...params, client_request_id: cid };
    error.value = null;
    if (!navigator.onLine) {
      if (canQueue(method)) {
        enqueue(method, payload, label);
        state.value = "queued";
        ui.toast("Saved offline. It will send when you reconnect.", "info");
        return null;
      }
      state.value = "error";
      error.value = "You're offline. This action needs a connection.";
      return null;
    }
    state.value = "submitting";
    try {
      result.value = await post(method, payload);
      state.value = "confirmed";
      invalidates.forEach(invalidate);
      return result.value;
    } catch (e: any) {
      state.value = "error";
      error.value = e?.message || "Something went wrong";
      return null;
    }
  }
  return { state, error, result, submit, reset: () => { state.value = "draft"; error.value = null; } };
}
