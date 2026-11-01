<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useResource, invalidate } from "@/composables/useResource";
import { Roster } from "@/services/endpoints";
import { fmtDate, fmtTime, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import { addDays, isoToday } from "@/utils/format";
import PageHeader from "@/components/ui/PageHeader.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import MonthCalendar, { type DayCell } from "@/components/hr/MonthCalendar.vue";
import ShiftChip from "@/components/hr/ShiftChip.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import AccessibleDialog from "@/components/ui/AccessibleDialog.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";
import EmptyState from "@/components/ui/EmptyState.vue";

const route = useRoute();
const ui = useUi();
const view = ref(window.innerWidth < 760 ? "week" : "month");
const now = new Date();
const y = ref(now.getFullYear());
const m = ref(now.getMonth() + 1);
const weekStart = ref(isoToday());
const range = computed(() => {
  if (view.value !== "month") return { from: weekStart.value, to: addDays(weekStart.value, 6) };
  const mm = String(m.value).padStart(2, "0");
  return { from: `${y.value}-${mm}-01`, to: `${y.value}-${mm}-${String(new Date(y.value, m.value, 0).getDate()).padStart(2, "0")}` };
});
const { data, loading, error, reload } = useResource<any>(() => `roster:mine:${range.value.from}:${range.value.to}`,
  () => Roster.mySchedule(range.value.from, range.value.to), { watch: [range] });
const selected = ref<string | null>(null);
const byDate = computed<Record<string, any>>(() => Object.fromEntries((data.value?.days || []).map((d: any) => [d.date, d])));
const cells = computed<Record<string, DayCell>>(() => {
  const out: Record<string, DayCell> = {};
  for (const d of data.value?.days || []) {
    const s = d.shifts[0];
    out[d.date] = s ? { date: d.date, color: s.color, label: `${s.code} ${s.start}–${s.end}` }
      : d.leave ? { date: d.date, tone: "info", label: d.leave.leave_type }
      : d.holiday && !d.holiday.weekly_off ? { date: d.date, tone: "warn", label: d.holiday.description }
      : { date: d.date, label: d.rest_day || d.holiday ? "Rest" : "", muted: true };
  }
  return out;
});
const day = computed(() => (selected.value ? byDate.value[selected.value] : null));
function shiftMonth(n: number) { const d = new Date(y.value, m.value - 1 + n, 1); y.value = d.getFullYear(); m.value = d.getMonth() + 1; selected.value = null; }

// change requests
const open = ref(false);
const form = ref<any>({ request_type: "Change shift", from_date: "", to_date: "", requested_shift_type: "", swap_with: "", reason: "" });
const candidates = ref<any[]>([]);
const err = ref("");
const busy = ref(false);
const earliest = computed(() => {
  const h = data.value?.notice_hours || 0;
  return new Date(Date.now() + h * 3600_000).toISOString().slice(0, 10);
});
function startRequest(d?: string) {
  const date = d || selected.value || addDays(isoToday(), 1);
  form.value = { request_type: "Change shift", from_date: date, to_date: date, requested_shift_type: "", swap_with: "", reason: "" };
  err.value = ""; candidates.value = []; open.value = true;
}
watch(() => [form.value.request_type, form.value.from_date, form.value.to_date], async () => {
  if (open.value && form.value.request_type === "Swap with colleague" && form.value.from_date && form.value.to_date) {
    try { candidates.value = await Roster.swapCandidates(form.value.from_date, form.value.to_date); } catch { candidates.value = []; }
  }
});
async function submit() {
  busy.value = true; err.value = "";
  try {
    const r: any = await Roster.requestChange(form.value);
    ui.toast(r.status === "Pending Colleague" ? "Swap request sent to your colleague" : "Request sent to your manager");
    open.value = false; invalidate("roster:mine"); invalidate("inbox"); reload();
  } catch (e: any) { err.value = e.message; } finally { busy.value = false; }
}
async function respond(name: string, accept: boolean) {
  try { await Roster.respondSwap(name, accept); ui.toast(accept ? "Swap accepted. Your manager will review it." : "Swap declined"); invalidate("inbox"); reload(); }
  catch (e: any) { ui.toast(e.message, "error"); }
}
async function cancel(name: string) { await Roster.cancelRequest(name); reload(); }
const icsUrl = computed(() => Roster.icsUrl(isoToday(), addDays(isoToday(), 90)));
const highlight = computed(() => route.query.swap as string | undefined);
const canRequest = (d: any) => data.value?.allow_requests && d && d.date >= earliest.value;
</script>

<template>
  <div class="page">
    <PageHeader :title="t('My roster')" subtitle="Your published shifts, rest days, holidays and leave.">
      <a class="btn" :href="icsUrl">Add to calendar (.ics)</a>
      <RouterLink to="/holidays" class="btn">{{ t("Holidays") }}</RouterLink>
      <button v-if="data?.allow_requests" class="btn primary" @click="startRequest()">Request a change</button>
    </PageHeader>

    <section class="panel" v-if="data?.incoming_swaps?.length">
      <header><h2>Swap requests for you</h2></header>
      <ul class="list">
        <li v-for="r in data.incoming_swaps" :key="r.name" :class="{ hl: highlight === r.name }">
          <span class="grow"><span class="title">{{ r.employee_name }}</span> wants to swap {{ fmtDate(r.from_date) }}<template v-if="r.to_date !== r.from_date"> – {{ fmtDate(r.to_date) }}</template>
            <br><span class="small muted">“{{ r.reason }}”</span></span>
          <button class="btn sm" @click="respond(r.name, false)">Decline</button>
          <button class="btn sm primary" @click="respond(r.name, true)">Accept</button>
        </li>
      </ul>
    </section>

    <div class="spread wrap">
      <SegmentTabs v-model="view" :tabs="[{ value: 'week', label: 'Week' }, { value: 'month', label: 'Month' }]" />
      <div class="row" v-if="view === 'week'">
        <button class="btn sm" @click="weekStart = addDays(weekStart, -7)" aria-label="Previous week">‹</button>
        <span class="small num">{{ fmtDate(range.from, { day: "numeric", month: "short" }) }} – {{ fmtDate(range.to, { day: "numeric", month: "short" }) }}</span>
        <button class="btn sm" @click="weekStart = addDays(weekStart, 7)" aria-label="Next week">›</button>
        <button class="btn sm ghost" @click="weekStart = isoToday()">{{ t("Today") }}</button>
      </div>
    </div>
    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !data" :lines="7" :height="30" />

    <div class="cols" v-else-if="data">
      <section class="panel">
        <MonthCalendar v-if="view === 'month'" :year="y" :month="m" :cells="cells" :selected="selected" @select="selected = $event" @prev="shiftMonth(-1)" @next="shiftMonth(1)" />
        <ul v-else class="week">
          <li v-for="d in data.days" :key="d.date" :class="{ today: d.date === isoToday(), sel: selected === d.date }">
            <button class="wrow" @click="selected = d.date">
              <span class="when"><span class="wd">{{ fmtDate(d.date, { weekday: "long" }) }}</span><span class="dn num">{{ fmtDate(d.date, { day: "numeric", month: "short" }) }}</span></span>
              <span class="grow">
                <span v-for="s in d.shifts" :key="s.start_dt" class="sh"><ShiftChip :code="s.code" :color="s.color" :label="s.shift_type" /> <span class="num muted">{{ s.start }}–{{ s.end }}</span></span>
                <span v-if="!d.shifts.length && d.leave">{{ d.leave.leave_type }} <StatusBadge :status="d.leave.status" /></span>
                <span v-else-if="!d.shifts.length && d.holiday && !d.holiday.weekly_off" class="hol">{{ d.holiday.description }}</span>
                <span v-else-if="!d.shifts.length" class="muted">{{ d.rest_day || d.holiday ? "Rest day" : "No shift" }}</span>
              </span>
            </button>
          </li>
        </ul>
      </section>

      <aside class="stack">
        <section class="panel">
          <template v-if="day">
            <header><h2>{{ fmtDate(day.date, { weekday: "long", day: "numeric", month: "long" }) }}</h2></header>
            <div v-for="s in day.shifts" :key="s.start_dt" class="detail">
              <ShiftChip :code="s.code" :color="s.color" :label="s.shift_type" />
              <dl><div><dt>Shift</dt><dd class="num">{{ s.start }} – {{ s.end }}<template v-if="s.overnight"> (next day)</template></dd></div>
                <div><dt>Check-in window</dt><dd class="num">{{ fmtTime(s.open) }} – {{ fmtTime(s.close) }}</dd></div>
                <div v-if="s.location"><dt>Location</dt><dd>{{ s.location }}</dd></div>
                <div><dt>Source</dt><dd>{{ s.source === "roster" ? "Published roster" : s.source === "default" ? "Default shift" : "Shift assignment" }}</dd></div></dl>
            </div>
            <p v-if="!day.shifts.length" class="muted">{{ day.leave ? `${day.leave.leave_type} (${day.leave.status})` : day.holiday ? day.holiday.description : day.rest_day ? "Rest day" : "No shift scheduled." }}</p>
            <button v-if="canRequest(day)" class="btn sm" @click="startRequest(day.date)">Request a change for this day</button>
            <p v-else-if="data.allow_requests && day.date >= isoToday()" class="small muted">Changes need {{ data.notice_hours }} hours' notice. Contact your manager for urgent changes.</p>
          </template>
          <p v-else class="muted">Select a day to see shift times and check-in window.</p>
        </section>
        <section class="panel" v-if="data.requests.length">
          <header><h2>My requests</h2></header>
          <ul class="list">
            <li v-for="r in data.requests" :key="r.name"><span class="grow"><span class="title">{{ r.request_type }}</span>
              <br><span class="small muted">{{ fmtDate(r.from_date) }}<template v-if="r.to_date !== r.from_date"> – {{ fmtDate(r.to_date) }}</template>
                <template v-if="r.swap_with_name"> · with {{ r.swap_with_name }}</template><template v-if="r.requested_shift_type"> · {{ r.requested_shift_type }}</template></span>
              <br v-if="r.review_comment"><span v-if="r.review_comment" class="small">{{ r.review_comment }}</span></span>
              <StatusBadge :status="r.status" />
              <button v-if="['Pending Colleague', 'Pending Approval'].includes(r.status)" class="btn ghost sm" @click="cancel(r.name)">{{ t("Cancel") }}</button></li>
          </ul>
        </section>
        <EmptyState v-if="!data.days.some((d: any) => d.shifts.length)" title="No shifts in this period" text="Shifts appear here once your manager publishes a roster or HR assigns a shift." icon="calendar" />
      </aside>
    </div>

    <AccessibleDialog :open="open" title="Request a roster change" @close="open = false">
      <form id="rcr" class="stack" @submit.prevent="submit">
        <fieldset class="types"><legend class="small muted">What do you need?</legend>
          <label v-for="o in ['Change shift', 'Request rest day', ...(data?.allow_swaps ? ['Swap with colleague'] : [])]" :key="o" class="opt" :class="{ on: form.request_type === o }">
            <input type="radio" class="sr-only" v-model="form.request_type" :value="o" />{{ o }}</label></fieldset>
        <div class="form-grid">
          <div class="field"><label for="rf">{{ t("From") }}</label><input id="rf" type="date" class="input" v-model="form.from_date" :min="earliest" required /></div>
          <div class="field"><label for="rt">{{ t("To") }}</label><input id="rt" type="date" class="input" v-model="form.to_date" :min="form.from_date" required /></div>
        </div>
        <div class="field" v-if="form.request_type === 'Change shift'"><label for="rs">Shift you'd like</label>
          <select id="rs" class="select" v-model="form.requested_shift_type" required><option value="" disabled>Choose</option>
            <option v-for="s in data?.shift_types || []" :key="s.name" :value="s.name">{{ s.name }} ({{ s.start }}–{{ s.end }})</option></select></div>
        <div class="field" v-if="form.request_type === 'Swap with colleague'"><label>Swap with</label>
          <p v-if="!candidates.length" class="small muted">No colleague on your roster covers all of these dates.</p>
          <label v-for="c in candidates" :key="c.employee" class="opt wide" :class="{ on: form.swap_with === c.employee }"><input type="radio" class="sr-only" v-model="form.swap_with" :value="c.employee" />
            <span class="grow">{{ c.employee_name }}</span><span class="small muted">their shifts: {{ c.shifts.join(", ") }}</span></label></div>
        <div class="field"><label for="rr">{{ t("Reason") }}</label><textarea id="rr" class="textarea" v-model="form.reason" required maxlength="500" /></div>
        <p class="small muted">{{ form.request_type === "Swap with colleague" ? "Your colleague accepts first, then your manager approves." : "Your manager approves the change; your roster updates once it's approved." }}</p>
        <p v-if="err" class="small bad" role="alert">{{ err }}</p>
      </form>
      <template #footer><button class="btn" @click="open = false">{{ t("Cancel") }}</button><button class="btn primary" form="rcr" :disabled="busy">Send request</button></template>
    </AccessibleDialog>
  </div>
</template>

<style scoped>
.week { list-style: none; margin: 0; padding: 0; }
.week li { border-top: 1px solid var(--line); }
.week li:first-child { border-top: 0; }
.wrow { width: 100%; display: flex; align-items: center; gap: 14px; padding: 12px 6px; border: 0; background: none; text-align: start; cursor: pointer; border-radius: 8px; }
.week li.sel .wrow, .wrow:hover { background: var(--surface-2); }
.week li.today .dn { color: var(--brand); }
.when { display: flex; flex-direction: column; min-width: 110px; line-height: 1.25; }
.wd { font-size: var(--fs-sm); color: var(--ink-2); }
.dn { font-weight: 600; }
.sh { display: inline-flex; align-items: center; gap: 8px; margin-inline-end: 12px; }
.hol { color: var(--saffron-ink); font-weight: 500; }
.detail { display: flex; flex-direction: column; gap: 10px; padding-bottom: 12px; margin-bottom: 12px; border-bottom: 1px solid var(--line); }
dl { margin: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
dt { font-size: var(--fs-xs); color: var(--ink-3); } dd { margin: 0; }
.hl { background: var(--saffron-soft); border-radius: 8px; padding-inline: 8px; }
.types { border: 0; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
.types legend { margin-bottom: 6px; }
.opt { padding: 8px 12px; border: 1px solid var(--line); border-radius: 10px; cursor: pointer; font-size: var(--fs-sm); display: flex; align-items: center; gap: 8px; }
.opt.wide { width: 100%; }
.opt.on { border-color: var(--brand); background: var(--brand-soft); }
.opt:focus-within { outline: 2px solid var(--focus); }
.bad { color: var(--pom); }
@media (max-width: 640px) { .when { min-width: 86px; } }
</style>
