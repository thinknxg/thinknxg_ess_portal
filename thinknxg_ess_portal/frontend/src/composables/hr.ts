import { computed } from "vue";
import { useSession } from "@/stores/session";
import { useResource } from "./useResource";
import { Attendance, Leave, Approvals } from "@/services/endpoints";
import type { ApprovalItem, LeaveBalance } from "@/types";

export function useCurrentEmployee() {
  const s = useSession();
  return { employee: computed(() => s.employee), caps: computed(() => s.caps), user: computed(() => s.user) };
}

export function useAttendance() {
  return useResource<any>(() => "attendance:today", () => Attendance.today(), { staleMs: 10_000 });
}

export function useLeaveBalance() {
  const r = useResource<any>(() => "leave:overview", () => Leave.overview());
  const balances = computed<LeaveBalance[]>(() => r.data.value?.balances || []);
  return { ...r, balances };
}

export function useApprovalQueue() {
  const r = useResource<{ items: ApprovalItem[]; counts: Record<string, number> }>(() => "approvals:pending",
    () => Approvals.pending(), { staleMs: 15_000 });
  const items = computed(() => r.data.value?.items || []);
  return { ...r, items };
}
