<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useResource, invalidate } from "@/composables/useResource";
import { useGeolocation } from "@/composables/useGeolocation";
import { useOnline } from "@/composables/useOnline";
import { Attendance } from "@/services/endpoints";
import { fmtDate, fmtTime, relative, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import ShiftRibbon from "@/components/hr/ShiftRibbon.vue";
import ShiftChip from "@/components/hr/ShiftChip.vue";
import UpcomingRoster from "@/components/hr/UpcomingRoster.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";
import EssIcon from "@/components/ui/EssIcon.vue";

const ui = useUi();
const online = useOnline();
const geo = useGeolocation();
const { data, loading, error, reload } = useResource<any>(() => "attendance:today", () => Attendance.today(), { staleMs: 5_000 });
const { data: history, reload: reloadHistory } = useResource<any[]>(() => "attendance:log", () => Attendance.myLog());
const pre = ref<any>(null);
const result = ref<any>(null);
const busy = ref(false);
let refresh: number | undefined;

const policy = computed(() => data.value?.policy || {});
const next = computed(() => data.value?.next_action || "IN");
const needGps = computed(() => !!policy.value.gps_required);
const accuracyTone = computed(() => {
  const a = geo.fix.value?.accuracy;
  if (a == null) return "muted";
  return a <= (policy.value.max_accuracy || 50) ? "ok" : "warn";
});

async function checkPosition() {
  pre.value = null;
  const f = await geo.locate(policy.value.max_accuracy || 50);
  if (!f) return;
  try { pre.value = await Attendance.precheck({ log_type: next.value, latitude: f.latitude, longitude: f.longitude, accuracy: f.accuracy }); }
  catch { /* precheck is advisory */ }
}

async function punch(kind: "IN" | "OUT") {
  result.value = null;
  busy.value = true;
  try {
    let f = geo.fresh() ? geo.fix.value : null;
    if (needGps.value && !f) f = await geo.locate(policy.value.max_accuracy || 50);
    if (needGps.value && !f) { result.value = { ok: false, message: geo.message.value || "We couldn't get your location." }; return; }
    const payload: Record<string, any> = { client_time: new Date().toISOString() };
    if (f) Object.assign(payload, { latitude: f.latitude, longitude: f.longitude, accuracy: f.accuracy });
    const r: any = kind === "IN" ? await Attendance.checkIn(payload) : await Attendance.checkOut(payload);
    result.value = r;
    if (r.ok) {
      ui.toast(r.message || (kind === "IN" ? "Checked in" : "Checked out"));
      invalidate("attendance"); invalidate("dashboard");
      pre.value = null;
      await reload();
    }
    reloadHistory();
  } catch (e: any) {
    result.value = { ok: false, message: e.message };
  } finally {
    busy.value = false;
  }
}

onMounted(async () => {
  await new Promise((r) => setTimeout(r, 0));
  const wait = window.setInterval(() => {
    if (data.value) { window.clearInterval(wait); if (needGps.value && policy.value.enabled) checkPosition(); }
  }, 150);
  refresh = window.setInterval(() => { if (!document.hidden) reload(); }, 60_000);
});
onBeforeUnmount(() => { window.clearInterval(refresh); geo.stop(); });

const preLine = computed(() => {
  const p = pre.value;
  if (!p) return null;
  const l = p.location || {};
  if (p.ok && l.matched) return { tone: "ok", text: `Inside ${l.matched} · ${Math.round(l.distance)} m from the centre` };
  if (p.ok) return { tone: "ok", text: p.code === "ALLOWED" ? "Ready to punch" : p.message };
  return { tone: p.code === "OUTSIDE_GEOFENCE" || p.code === "LOCATION_INACCURATE" ? "bad" : "warn", text: p.message, hint: p.hint };
});
const windowText = computed(() => {
  const d = data.value;
  if (!d?.window) return null;
  const w = d.window;
  return d.window_open ? `Window open until ${fmtTime(w.close)}` : `Check-in window ${fmtTime(w.open)} – ${fmtTime(w.close)}`;
});
const REASON: Record<string, string> = { ALLOWED: "Accepted", CHECKIN_DISABLED: "Check-in off", OUTSIDE_GEOFENCE: "Outside location", LOCATION_INACCURATE: "Weak GPS",
  LOCATION_REQUIRED: "No location", OUTSIDE_SHIFT_WINDOW: "Outside window", NO_SHIFT: "No shift", ALREADY_CHECKED_IN: "Already in", NOT_CHECKED_IN: "Not in",
  COOLDOWN: "Too soon", HIGH_RISK: "Unverified location", NATIVE_VALIDATION: "HR rule", NO_LOCATIONS_CONFIGURED: "No location set up", INVALID_LOCATION: "Invalid location" };
</script>

<template>
  <div class="page narrow">
    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !data" :lines="6" :height="28" />
    <template v-if="data">
      <section class="card">
        <div class="spread">
          <p class="muted">{{ fmtDate(data.date, { weekday: "long", day: "numeric", month: "long" }) }}</p>
          <StatusBadge :tone="data.status_label === 'On Duty' ? 'ok' : data.window_open ? 'warn' : 'muted'" :label="data.status_label" />
        </div>
        <div class="shift-line" v-if="data.shift">
          <ShiftChip :code="data.shift.code" :color="data.shift.color" />
          <div><h1 class="num">{{ data.shift.start_time.slice(0, 5) }} – {{ data.shift.end_time.slice(0, 5) }}</h1><p class="muted">{{ data.shift.shift_type }}<template v-if="windowText"> · {{ windowText }}</template></p></div>
        </div>
        <div v-else class="shift-line"><div><h1>{{ data.rest_day ? "Rest day" : data.on_leave ? t("On leave") : t("No shift today") }}</h1>
          <p class="muted" v-if="data.next_shift">Next shift: {{ data.next_shift.shift_type }}, {{ fmtDate(data.next_shift.start_dt, { weekday: "long", day: "numeric", month: "short" }) }} at {{ data.next_shift.start }}</p></div></div>

        <ShiftRibbon v-if="data.shift || data.logs.length" :start="data.shift?.start_time" :end="data.shift?.end_time" :logs="data.logs" />

        <div v-if="!data.policy.enabled" class="notice bad" role="status">
          <EssIcon name="shield" :size="18" /><div><strong>Portal check-in is turned off for your account.</strong><br>Use the attendance device at your site, or contact HR if you think this is wrong.</div>
        </div>

        <template v-else>
          <div class="verify">
            <div class="row"><EssIcon name="pin" :size="18" /><strong class="grow">Location verification</strong>
              <button v-if="needGps" class="btn ghost sm" @click="checkPosition" :disabled="geo.state.value === 'locating'">{{ geo.state.value === "locating" ? "Locating…" : "Check my location" }}</button></div>
            <p class="small muted">{{ needGps ? (policy.enforce_geofence ? `GPS verification required by portal settings. Allowed within ${policy.radius} m, accuracy ±${policy.max_accuracy} m or better.` : "Your location is recorded with each punch.") : "GPS verification isn't required for you." }}</p>
            <p v-if="data.locations?.length" class="small muted">Your locations: {{ data.locations.map((l: any) => `${l.name} (${l.radius} m)`).join(", ") }}</p>
            <div v-if="needGps && geo.fix.value" class="fix small">
              <StatusBadge :tone="accuracyTone as any" :label="`±${geo.fix.value.accuracy} m`" />
              <span v-if="preLine" :class="['pl', preLine.tone]">{{ preLine.text }}</span>
            </div>
            <p v-if="preLine?.hint" class="small muted">{{ preLine.hint }}</p>
            <p v-if="geo.message.value" class="small warn" role="alert">{{ geo.message.value }}</p>
          </div>

          <div class="punches">
            <button class="big-btn in" :class="{ primary: next === 'IN' }" :disabled="busy || !online || next !== 'IN'" @click="punch('IN')">
              <EssIcon name="clock" :size="22" /><span>{{ busy && next === "IN" ? (geo.state.value === "locating" ? "Getting location…" : "Recording…") : t("Check in") }}</span></button>
            <button class="big-btn out" :class="{ primary: next === 'OUT' }" :disabled="busy || !online || next !== 'OUT'" @click="punch('OUT')">
              <EssIcon name="logout" :size="22" /><span>{{ busy && next === "OUT" ? "Recording…" : t("Check out") }}</span></button>
          </div>
          <p v-if="!online" class="small warn">Check-in needs a connection so your time is confirmed by the server.</p>

          <div v-if="result && !result.ok" class="notice bad" role="alert">
            <EssIcon name="x" :size="18" /><div><strong>{{ result.message }}</strong><br v-if="result.hint"><span v-if="result.hint">{{ result.hint }}</span>
              <span v-if="result.code" class="code">{{ result.code }}</span></div>
          </div>
          <div v-if="result?.ok" class="notice ok" role="status"><EssIcon name="check" :size="18" /><div><strong>{{ result.message }}</strong>
            <template v-for="wn in result.warnings || []" :key="wn"><br><span>{{ wn }}</span></template></div></div>
        </template>

        <ul class="list log" v-if="data.logs.length">
          <li v-for="(l, i) in data.logs" :key="i"><span class="grow">{{ l.log_type === "IN" ? t("Check in") : l.log_type === "OUT" ? t("Check out") : "Punch" }}<span class="small muted" v-if="l.device && l.device !== 'thinkNXG ESS Portal'"> · {{ l.device }}</span></span><span class="num">{{ fmtTime(l.time) }}</span></li>
        </ul>
        <RouterLink to="/attendance/corrections?new=1" class="small">Forgot to punch? {{ t("Request correction") }}</RouterLink>
      </section>

      <section class="panel tight" v-if="data.upcoming?.length">
        <header><h2>Upcoming roster</h2><RouterLink to="/roster">{{ t("View") }}</RouterLink></header>
        <UpcomingRoster :days="data.upcoming" :limit="5" />
      </section>

      <section class="panel tight" v-if="history?.length">
        <header><h2>Recent attempts</h2></header>
        <ul class="list">
          <li v-for="h in history.slice(0, 6)" :key="h.name">
            <span class="grow"><span class="title">{{ h.log_type === "IN" ? t("Check in") : t("Check out") }}</span>
              <span class="small muted"> · {{ relative(h.server_time) }}<template v-if="h.matched_location"> · {{ h.matched_location }}</template></span>
              <br v-if="h.decision === 'Denied'"><span v-if="h.decision === 'Denied'" class="small muted">{{ h.message }}</span></span>
            <StatusBadge :tone="h.decision === 'Allowed' ? 'ok' : 'bad'" :label="REASON[h.reason_code] || h.reason_code" />
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.narrow { max-width: 680px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); padding: 24px; display: flex; flex-direction: column; gap: 18px; }
.shift-line { display: flex; align-items: center; gap: 14px; }
.shift-line h1 { font-size: var(--fs-2xl); letter-spacing: -0.02em; }
.verify { display: flex; flex-direction: column; gap: 6px; padding: 14px; border-radius: 12px; background: var(--surface-2); }
.fix { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 4px; }
.pl { font-weight: 500; } .pl.ok { color: var(--ok); } .pl.bad { color: var(--pom); } .pl.warn { color: var(--saffron-ink); }
.punches { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.big-btn { display: flex; align-items: center; justify-content: center; gap: 10px; height: 64px; border-radius: 14px; font-size: var(--fs-lg); font-weight: 600; cursor: pointer;
  border: 1px solid var(--line-strong); background: var(--surface); color: var(--ink-2); }
.big-btn.primary.in { background: var(--brand); border-color: var(--brand); color: #fff; }
.big-btn.primary.out { background: var(--ink); border-color: var(--ink); color: var(--paper); }
.big-btn:disabled { cursor: not-allowed; }
.big-btn:disabled:not(.primary) { opacity: .45; }
.big-btn.primary:disabled { opacity: .6; }
.notice { display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border-radius: 12px; font-size: var(--fs-sm); }
.notice.bad { background: var(--pom-soft); color: var(--pom); }
.notice.ok { background: var(--ok-soft); color: var(--ok); }
.notice span { color: var(--ink-2); }
.code { display: inline-block; margin-inline-start: 8px; font-size: 11px; opacity: .7; }
.warn { color: var(--saffron-ink); }
@media (max-width: 640px) { .card { padding: 16px; } .shift-line h1 { font-size: 1.5rem; } .big-btn { height: 58px; } }
</style>
