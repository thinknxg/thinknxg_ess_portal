<script setup lang="ts">
import { computed } from "vue";
import { useResource } from "@/composables/useResource";
import { Dashboard } from "@/services/endpoints";
import { useSession } from "@/stores/session";
import { fmtDate, fmtMoney, fmtTime, relative, t } from "@/i18n";
import ShiftRibbon from "@/components/hr/ShiftRibbon.vue";
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
const punchLabel = computed(() => (att.value?.next_action === "OUT" ? t("Check out") : t("Check in")));
const dayLine = computed(() => {
  const a = att.value;
  if (!a) return "";
  if (a.on_leave) return "You're on leave today.";
  if (!a.shift) return t("No shift today");
  if (!a.logs.length) return `Shift starts ${a.shift.start_time?.slice(0, 5)}. You haven't checked in yet.`;
  const last = a.logs[a.logs.length - 1];
  return last.log_type === "IN" ? `Checked in since ${fmtTime(a.first_in || last.time)}.` : `Checked out at ${fmtTime(last.time)}.`;
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
    <section class="today">
      <div class="hello">
        <p class="muted">{{ fmtDate(data?.date || s.boot?.server_date, { weekday: "long", day: "numeric", month: "long" }) }}</p>
        <h1>{{ greeting }}, {{ s.employee?.first_name || s.user.full_name.split(" ")[0] }}</h1>
        <p class="line">{{ dayLine }}</p>
      </div>
      <div class="ribbon-wrap" v-if="att?.shift || att?.logs?.length">
        <ShiftRibbon :start="att.shift?.start_time" :end="att.shift?.end_time" :logs="att.logs" />
      </div>
      <div class="acts" v-if="s.employee">
        <RouterLink v-if="s.module('checkin') && !att?.on_leave" to="/attendance/check-in" class="btn primary">{{ punchLabel }}</RouterLink>
        <RouterLink v-if="s.module('leave')" to="/leave/apply" class="btn">{{ t("Apply for leave") }}</RouterLink>
        <RouterLink v-if="s.module('expenses')" to="/finances/expenses/new" class="btn">{{ t("New claim") }}</RouterLink>
        <RouterLink v-if="s.module('assistant')" to="/assistant" class="btn ghost"><EssIcon name="spark" :size="18" />{{ t("HR assistant") }}</RouterLink>
      </div>
    </section>

    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !data" :lines="6" />

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
          <header><h2>{{ t("Upcoming holidays") }}</h2></header>
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
.today { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.25fr); gap: 20px 40px; align-items: end; padding: 8px 0 4px; }
.hello h1 { font-size: var(--fs-2xl); letter-spacing: -0.025em; margin: 2px 0 6px; }
.line { color: var(--ink-2); }
.ribbon-wrap { min-width: 0; }
.acts { grid-column: 1 / -1; display: flex; gap: 8px; flex-wrap: wrap; }
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
@media (max-width: 960px) { .today { grid-template-columns: minmax(0, 1fr); } .hello h1 { font-size: 1.6rem; } .attn { grid-template-columns: 1fr; } }
</style>
