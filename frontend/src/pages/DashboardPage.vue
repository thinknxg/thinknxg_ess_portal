<script setup lang="ts">
import { computed } from "vue";
import { useResource } from "@/composables/useResource";
import { Dashboard } from "@/services/endpoints";
import { useSession } from "@/stores/session";
import { fmtDate, fmtMoney, fmtTime, relative, t } from "@/i18n";
import ShiftRibbon from "@/components/hr/ShiftRibbon.vue";
import ShiftChip from "@/components/hr/ShiftChip.vue";
import UpcomingRoster from "@/components/hr/UpcomingRoster.vue";
import Meter from "@/components/hr/Meter.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";
import Avatar from "@/components/ui/Avatar.vue";
import EssIcon from "@/components/ui/EssIcon.vue";
import EmptyState from "@/components/ui/EmptyState.vue";

const s = useSession();
const { data, loading, error, reload } = useResource<any>(() => "dashboard", () => Dashboard.summary(), { staleMs: 20_000 });

const greeting = computed(() => {
  const h = new Date().getHours();
  return t(h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening");
});
const att = computed(() => data.value?.attendance);
const STATUS_TONE: Record<string, any> = { "On Duty": "ok", "Shift Window Open": "warn", "Checked In": "ok", "On Leave": "info", "Rest Day": "muted", Holiday: "info", Scheduled: "muted", "Off Duty": "muted" };
const attendanceLine = computed(() => {
  const a = att.value;
  if (!a) return { title: "", sub: "" };
  if (a.next_action === "OUT") return { title: t("Checked in"), sub: `Since ${fmtTime(a.last_log?.time || a.first_in)}` };
  const outs = (a.logs || []).filter((l: any) => l.log_type === "OUT");
  if (outs.length) return { title: t("Checked out"), sub: `At ${fmtTime(outs[outs.length - 1].time)}` };
  if (a.on_leave) return { title: t("On leave"), sub: "No punch needed today" };
  if (a.rest_day) return { title: "Rest day", sub: "No punch needed today" };
  return { title: t("Not checked in"), sub: "Awaiting first punch" };
});
const verifyLine = computed(() => {
  const p = att.value?.policy;
  if (!p) return "";
  if (!p.enabled) return "Portal check-in is off for your account";
  if (!p.gps_required) return "GPS verification not required for you";
  return p.enforce_geofence ? `GPS verification required by portal settings · within ${p.radius} m` : "Your location is recorded with each punch";
});
const pending = computed(() => {
  const p = data.value?.pending_requests || {};
  return [
    { label: "Leave requests", n: p.leave, to: "/leave" },
    { label: "Expense drafts", n: p.expense, to: "/finances/expenses" },
    { label: "Open tickets", n: p.tickets, to: "/support" },
    { label: "Document requests", n: p.documents, to: "/documents" },
  ].filter((x) => x.n);
});
</script>

<template>
  <div class="page">
    <section class="hello">
      <div>
        <p class="muted">{{ fmtDate(data?.date || s.boot?.server_date, { weekday: "long", day: "numeric", month: "long" }) }}</p>
        <h1>{{ greeting }}, {{ s.employee?.first_name || s.user.full_name.split(" ")[0] }}</h1>
      </div>
      <div class="acts" v-if="s.employee">
        <RouterLink v-if="s.module('attendance')" to="/attendance/check-in" class="btn primary">{{ att?.next_action === "OUT" ? t("Check out") : t("Check in") }}</RouterLink>
        <RouterLink v-if="s.module('leave')" to="/leave/apply" class="btn">{{ t("Apply for leave") }}</RouterLink>
        <RouterLink v-if="s.module('roster')" to="/roster" class="btn">{{ t("My roster") }}</RouterLink>
        <RouterLink v-if="s.module('assistant')" to="/assistant" class="btn ghost"><EssIcon name="spark" :size="18" />{{ t("HR assistant") }}</RouterLink>
      </div>
    </section>

    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !data" :lines="6" />

    <section v-if="att" class="today" aria-label="Today">
      <div class="today-head">
        <StatusBadge :tone="STATUS_TONE[att.status_label] || 'muted'" :label="att.status_label" />
        <span v-if="att.holiday && !att.holiday.weekly_off" class="small muted">{{ att.holiday.description }}</span>
      </div>
      <div class="facts">
        <div class="fact">
          <span class="k">Today's shift</span>
          <template v-if="att.shift">
            <span class="v num">{{ att.shift.start_time.slice(0, 5) }} – {{ att.shift.end_time.slice(0, 5) }}</span>
            <span class="s"><ShiftChip :code="att.shift.code" :color="att.shift.color" size="sm" /> {{ att.shift.shift_type }}<template v-if="att.shifts_today.length > 1"> + {{ att.shifts_today.length - 1 }} more</template></span>
          </template>
          <template v-else><span class="v">{{ att.rest_day ? "Rest day" : t("No shift today") }}</span>
            <span class="s" v-if="att.next_shift">Next: {{ att.next_shift.shift_type }}, {{ fmtDate(att.next_shift.start_dt, { weekday: "short", day: "numeric", month: "short" }) }} {{ att.next_shift.start }}</span></template>
        </div>
        <div class="fact">
          <span class="k">{{ t("Attendance") }}</span>
          <span class="v">{{ attendanceLine.title }}</span>
          <span class="s">{{ attendanceLine.sub }}</span>
        </div>
        <div class="fact">
          <span class="k">Location verification</span>
          <span class="v small-v">{{ verifyLine }}</span>
          <span class="s" v-if="att.locations?.length">{{ att.locations.map((l: any) => l.name).slice(0, 2).join(", ") }}</span>
        </div>
      </div>
      <ShiftRibbon v-if="att.shift || att.logs?.length" :start="att.shift?.start_time" :end="att.shift?.end_time" :logs="att.logs" compact />
    </section>

    <div class="cols" v-if="data">
      <div class="stack">
        <section class="panel" v-if="data.inbox_count || data.team">
          <header><h2>Needs your attention</h2><RouterLink to="/inbox">{{ t("Inbox") }}</RouterLink></header>
          <div class="attn">
            <RouterLink to="/inbox" class="attn-item"><span class="big num">{{ data.inbox_count }}</span><span>items in your inbox</span></RouterLink>
            <RouterLink v-if="data.team" to="/team/approvals" class="attn-item warn"><span class="big num">{{ data.team.pending_approvals }}</span><span>approvals from your team of {{ data.team.size }}</span></RouterLink>
          </div>
        </section>

        <section class="panel" v-if="data.leave_balances">
          <header><h2>{{ t("Leave balance") }}</h2><RouterLink to="/leave">{{ t("View") }}</RouterLink></header>
          <div class="stack" v-if="data.leave_balances.length">
            <Meter v-for="b in data.leave_balances" :key="b.leave_type" :label="b.leave_type" :value="b.remaining" :max="b.allocated"
                   :detail="`${b.remaining} / ${b.allocated} ${t('days left')}`" />
          </div>
          <EmptyState v-else title="No leave allocated yet" text="Your HR team allocates leave at the start of each period." icon="sun" />
        </section>

        <section class="panel" v-if="pending.length">
          <header><h2>Your open requests</h2></header>
          <ul class="list">
            <li v-for="p in pending" :key="p.label"><RouterLink :to="p.to" class="rowlink"><span class="grow title">{{ p.label }}</span><span class="num">{{ p.n }}</span><EssIcon name="chevron" :size="16" /></RouterLink></li>
          </ul>
        </section>

        <section class="panel" v-if="data.announcements?.length">
          <header><h2>{{ t("Announcements") }}</h2></header>
          <article v-for="a in data.announcements" :key="a.name" class="ann" :class="{ unread: !a.is_read, urgent: a.category === 'Urgent' }">
            <div class="spread"><h3>{{ a.title }}</h3><StatusBadge v-if="a.is_pinned" status="Pinned" tone="info" /></div>
            <div class="body" v-html="a.body" />
          </article>
        </section>
      </div>

      <div class="stack">
        <section class="panel tight" v-if="att?.upcoming?.length && s.module('roster')">
          <header><h2>Upcoming roster</h2><RouterLink to="/roster">{{ t("View") }}</RouterLink></header>
          <UpcomingRoster :days="att.upcoming" :limit="4" />
        </section>

        <section class="panel tight" v-if="data.latest_payslip">
          <header><h2>{{ t("Latest payslip") }}</h2><RouterLink :to="`/finances/payslips/${data.latest_payslip.name}`">{{ t("View") }}</RouterLink></header>
          <p class="muted small">{{ fmtDate(data.latest_payslip.start_date) }} – {{ fmtDate(data.latest_payslip.end_date) }}</p>
          <details class="reveal"><summary>Show net pay</summary><p class="pay num">{{ fmtMoney(data.latest_payslip.net_pay, data.latest_payslip.currency) }}</p></details>
        </section>

        <section class="panel tight" v-if="data.expiring_documents?.length">
          <header><h2>{{ t("Expiring soon") }}</h2></header>
          <ul class="list">
            <li v-for="d in data.expiring_documents" :key="d.name"><span class="grow">{{ d.document_type }}</span><StatusBadge status="Expiring" tone="warn" :label="fmtDate(d.expiry_date)" /></li>
          </ul>
          <RouterLink to="/profile?tab=documents" class="btn sm">Upload renewed copy</RouterLink>
        </section>

        <section class="panel tight" v-if="data.holidays?.length">
          <header><h2>{{ t("Upcoming holidays") }}</h2><RouterLink to="/holidays">{{ t("View") }}</RouterLink></header>
          <ul class="list">
            <li v-for="h in data.holidays" :key="h.holiday_date"><span class="date num">{{ fmtDate(h.holiday_date, { day: "numeric", month: "short" }) }}</span><span class="grow">{{ h.description }}</span></li>
          </ul>
        </section>

        <section class="panel tight" v-if="data.celebrations?.length">
          <header><h2>{{ t("Celebrations this week") }}</h2></header>
          <ul class="list">
            <li v-for="c in data.celebrations" :key="c.employee_name + c.type"><Avatar :name="c.employee_name" :image="c.image" :size="30" />
              <span class="grow"><span class="title">{{ c.employee_name }}</span><br><span class="muted small">{{ c.type === "birthday" ? t("Birthday") : `${c.years} year${c.years > 1 ? "s" : ""} with us` }}</span></span></li>
          </ul>
        </section>

        <section class="panel tight" v-if="data.recognition?.length">
          <header><h2>{{ t("Recognition") }}</h2><RouterLink to="/recognition">{{ t("View") }}</RouterLink></header>
          <blockquote v-for="r in data.recognition" :key="r.name" class="kudo">
            <p>“{{ r.message }}”</p>
            <footer class="small muted">{{ r.sender_name }} to {{ r.recipient_name }} · {{ r.category }}</footer>
          </blockquote>
        </section>

        <section class="panel tight" v-if="data.activity?.length">
          <header><h2>Recent activity</h2><RouterLink to="/notifications">{{ t("View") }}</RouterLink></header>
          <ul class="list">
            <li v-for="n in data.activity.slice(0, 5)" :key="n.name"><span class="grow small" :class="{ strong: !n.read }">{{ n.subject }}</span><span class="muted small">{{ relative(n.creation) }}</span></li>
          </ul>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hello { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.hello h1 { font-size: var(--fs-2xl); letter-spacing: -0.025em; margin-top: 2px; }
.acts { display: flex; gap: 8px; flex-wrap: wrap; }
.today { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); padding: 18px 22px 14px; display: flex; flex-direction: column; gap: 14px; }
.today-head { display: flex; align-items: center; gap: 12px; }
.facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0; }
.fact { display: flex; flex-direction: column; gap: 3px; padding-inline: 0 20px; }
.fact + .fact { border-inline-start: 1px solid var(--line); padding-inline-start: 20px; }
.k { font-size: var(--fs-sm); color: var(--ink-3); }
.v { font-size: var(--fs-xl); font-weight: 600; letter-spacing: -0.02em; line-height: 1.2; }
.v.small-v { font-size: var(--fs-md); letter-spacing: 0; line-height: 1.4; }
.s { font-size: var(--fs-sm); color: var(--ink-2); display: inline-flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.attn { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.attn-item { display: flex; align-items: baseline; gap: 10px; padding: 14px; border-radius: 12px; background: var(--surface-2); color: var(--ink); text-decoration: none; }
.attn-item.warn { background: var(--saffron-soft); color: var(--saffron-ink); }
.big { font-size: var(--fs-xl); font-weight: 600; }
.ann { padding: 12px 0; border-top: 1px solid var(--line); }
.ann:first-of-type { border-top: 0; padding-top: 0; }
.ann.unread h3::before { content: ""; display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--brand); margin-inline-end: 8px; vertical-align: 2px; }
.ann.urgent { border-inline-start: 3px solid var(--pom); padding-inline-start: 12px; }
.ann .body { color: var(--ink-2); margin-top: 6px; font-size: var(--fs-sm); max-width: 70ch; }
.reveal summary { cursor: pointer; color: var(--brand); font-size: var(--fs-sm); }
.pay { font-size: var(--fs-xl); font-weight: 600; margin-top: 6px; }
.date { min-width: 56px; font-weight: 600; color: var(--brand); }
.kudo { margin: 0 0 12px; padding-inline-start: 12px; border-inline-start: 2px solid var(--saffron); }
.strong { font-weight: 600; }
@media (max-width: 960px) { .hello h1 { font-size: 1.6rem; } .attn { grid-template-columns: 1fr; } }
@media (max-width: 760px) {
  .facts { grid-template-columns: 1fr; gap: 12px; }
  .fact + .fact { border-inline-start: 0; padding-inline-start: 0; border-top: 1px solid var(--line); padding-top: 12px; }
}
</style>
