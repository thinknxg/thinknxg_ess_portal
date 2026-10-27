<script setup lang="ts">
import { computed, ref } from "vue";
import { useAttendance } from "@/composables/hr";
import { invalidate } from "@/composables/useResource";
import { Attendance } from "@/services/endpoints";
import { useOnline } from "@/composables/useOnline";
import { fmtDate, fmtTime, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import ShiftRibbon from "@/components/hr/ShiftRibbon.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";
import EssIcon from "@/components/ui/EssIcon.vue";

const ui = useUi();
const online = useOnline();
const { data, loading, error, reload } = useAttendance();
const busy = ref(false);
const problem = ref<string | null>(null);
const locState = ref<"idle" | "locating" | "ok" | "denied">("idle");

const next = computed(() => data.value?.next_action || "IN");
const needLocation = computed(() => data.value?.require_geolocation || !!data.value?.geofence);

function locate(): Promise<GeolocationPosition | null> {
  if (!("geolocation" in navigator)) return Promise.resolve(null);
  locState.value = "locating";
  return new Promise((resolve) => navigator.geolocation.getCurrentPosition(
    (p) => { locState.value = "ok"; resolve(p); },
    () => { locState.value = "denied"; resolve(null); },
    { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }));
}

async function punch() {
  problem.value = null;
  busy.value = true;
  try {
    const pos = needLocation.value || data.value?.geofence ? await locate() : null;
    if (needLocation.value && !pos) { problem.value = "We couldn't get your location. Allow location access for this site and try again."; return; }
    const payload = pos ? { latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy } : {};
    const r = next.value === "IN" ? await Attendance.checkIn(payload) : await Attendance.checkOut(payload);
    ui.toast(`${next.value === "IN" ? "Checked in" : "Checked out"} at ${fmtTime(r.time)}`);
    invalidate("attendance"); invalidate("dashboard");
    await reload();
  } catch (e: any) {
    problem.value = e.message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="page narrow">
    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !data" :lines="5" :height="30" />
    <section class="punch-card" v-if="data">
      <p class="muted">{{ fmtDate(data.date, { weekday: "long", day: "numeric", month: "long" }) }}</p>
      <h1 v-if="data.on_leave">You're on leave today</h1>
      <h1 v-else-if="!data.shift">{{ t("No shift today") }}</h1>
      <h1 v-else>{{ data.shift.shift_type }} <span class="muted num">{{ data.shift.start_time?.slice(0, 5) }}–{{ data.shift.end_time?.slice(0, 5) }}</span></h1>

      <ShiftRibbon :start="data.shift?.start_time" :end="data.shift?.end_time" :logs="data.logs" />

      <button class="big-btn" :class="next === 'OUT' ? 'out' : 'in'" :disabled="busy || !online || !data.checkin_enabled" @click="punch">
        <EssIcon name="clock" :size="28" />
        <span>{{ busy ? (locState === "locating" ? "Getting location…" : "Recording…") : next === "IN" ? t("Check in") : t("Check out") }}</span>
      </button>
      <p v-if="!online" class="note warn">Check-in needs a connection so your time is confirmed by the server.</p>
      <p v-if="problem" class="note bad" role="alert">{{ problem }}</p>
      <p v-if="data.geofence" class="note"><EssIcon name="pin" :size="16" /> Allowed within {{ data.geofence.radius }} m of {{ data.geofence.name }}.</p>
      <p v-else-if="needLocation" class="note"><EssIcon name="pin" :size="16" /> Your location is recorded with each punch.</p>

      <ul class="list log" v-if="data.logs.length">
        <li v-for="(l, i) in data.logs" :key="i"><span class="grow">{{ l.log_type === "IN" ? t("Check in") : t("Check out") }}</span><span class="num">{{ fmtTime(l.time) }}</span></li>
      </ul>
      <RouterLink to="/attendance/corrections?new=1" class="small">Forgot to punch? {{ t("Request correction") }}</RouterLink>
    </section>
  </div>
</template>

<style scoped>
.narrow { max-width: 640px; }
.punch-card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); padding: 28px; display: flex; flex-direction: column; gap: 18px; }
.punch-card h1 { font-size: var(--fs-xl); }
.big-btn { display: flex; align-items: center; justify-content: center; gap: 12px; height: 72px; border: 0; border-radius: 16px; font-size: var(--fs-lg); font-weight: 600; cursor: pointer; color: #fff; background: var(--brand); }
.big-btn.out { background: var(--ink); color: var(--paper); }
.big-btn:disabled { opacity: .5; cursor: not-allowed; }
.note { display: flex; align-items: center; gap: 6px; font-size: var(--fs-sm); color: var(--ink-2); }
.note.warn { color: var(--saffron-ink); } .note.bad { color: var(--pom); }
@media (max-width: 640px) { .punch-card { padding: 18px; } }
</style>
