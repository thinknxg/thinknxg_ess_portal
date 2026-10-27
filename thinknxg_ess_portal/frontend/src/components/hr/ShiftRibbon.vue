<script setup lang="ts">
/**
 * The day as a band: shift window, punches as markers, a live "now" needle.
 * Purely presentational; the server decides what counts as attendance.
 */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { minutesOf } from "@/utils/format";
import { fmtTime, lang } from "@/i18n";

const props = defineProps<{ start?: string | null; end?: string | null; logs: { time: string; log_type: string }[]; compact?: boolean }>();
const now = ref(new Date());
let timer: number | undefined;
onMounted(() => (timer = window.setInterval(() => (now.value = new Date()), 30_000)));
onBeforeUnmount(() => window.clearInterval(timer));

const s = computed(() => minutesOf(props.start));
const e = computed(() => {
  const v = minutesOf(props.end);
  return v !== null && s.value !== null && v <= s.value ? v + 1440 : v;
});
const range = computed(() => {
  const pts = [s.value, e.value, ...props.logs.map((l) => minutesOf(l.time))].filter((x): x is number => x !== null);
  const nowM = now.value.getHours() * 60 + now.value.getMinutes();
  pts.push(nowM);
  const lo = Math.max(0, Math.floor((Math.min(...pts) - 60) / 60) * 60);
  const hi = Math.min(1440 + 360, Math.ceil((Math.max(...pts) + 60) / 60) * 60);
  return { lo, hi: Math.max(hi, lo + 360) };
});
const pct = (m: number) => ((m - range.value.lo) / (range.value.hi - range.value.lo)) * 100;
const nowM = computed(() => now.value.getHours() * 60 + now.value.getMinutes());
const nowLabel = computed(() => now.value.toLocaleTimeString(lang.value === "ar" ? "ar-OM" : "en-GB", { hour: "2-digit", minute: "2-digit" }));
const hours = computed(() => {
  const out: number[] = [];
  const step = range.value.hi - range.value.lo > 720 ? 180 : 120;
  for (let m = range.value.lo; m <= range.value.hi; m += step) out.push(m);
  return out;
});
const segments = computed(() => {
  const segs: { a: number; b: number; open: boolean }[] = [];
  let open: number | null = null;
  for (const l of props.logs) {
    const m = minutesOf(l.time);
    if (m === null) continue;
    if (l.log_type === "IN") open = m;
    else if (open !== null) { segs.push({ a: open, b: m, open: false }); open = null; }
  }
  if (open !== null) segs.push({ a: open, b: Math.max(open, nowM.value), open: true });
  return segs;
});
const label = (m: number) => `${String(Math.floor((m % 1440) / 60)).padStart(2, "0")}:00`;
const summary = computed(() => {
  const worked = segments.value.reduce((a, x) => a + (x.b - x.a), 0);
  return `${Math.floor(worked / 60)}h ${String(worked % 60).padStart(2, "0")}m`;
});
</script>

<template>
  <figure class="ribbon" :class="{ compact }">
    <figcaption class="sr-only">
      Shift {{ start || "not set" }} to {{ end || "not set" }}. Punches: {{ logs.map((l) => `${l.log_type} ${fmtTime(l.time)}`).join(", ") || "none" }}.
      Time recorded today {{ summary }}.
    </figcaption>
    <div class="track" aria-hidden="true">
      <div v-if="s !== null && e !== null" class="shift" :style="{ insetInlineStart: pct(s) + '%', width: pct(e) - pct(s) + '%' }" />
      <div v-for="(g, i) in segments" :key="i" class="worked" :class="{ live: g.open }"
           :style="{ insetInlineStart: pct(g.a) + '%', width: Math.max(pct(g.b) - pct(g.a), 0.6) + '%' }" />
      <span v-for="(l, i) in logs" :key="'p' + i" class="punch" :class="l.log_type.toLowerCase()"
            :style="{ insetInlineStart: pct(minutesOf(l.time) || 0) + '%' }" />
      <span class="now" :style="{ insetInlineStart: pct(nowM) + '%' }"><span class="now-l num">{{ nowLabel }}</span></span>
    </div>
    <div class="scale num" aria-hidden="true">
      <span v-for="h in hours" :key="h" :style="{ insetInlineStart: pct(h) + '%' }">{{ label(h) }}</span>
    </div>
    <div v-if="!compact" class="legend small">
      <span><i class="k shift-k" />Shift {{ start?.slice(0, 5) || "—" }}–{{ end?.slice(0, 5) || "—" }}</span>
      <span><i class="k work-k" />Recorded {{ summary }}</span>
    </div>
  </figure>
</template>

<style scoped>
.ribbon { margin: 0; padding-top: 22px; }
.track { position: relative; height: 44px; border-radius: 12px; background: repeating-linear-gradient(90deg, var(--surface-2) 0 1px, transparent 1px 100%), var(--surface-2); background-size: calc(100% / 12) 100%; overflow: visible; }
.compact .track { height: 30px; border-radius: 8px; }
.shift { position: absolute; top: 0; bottom: 0; border-radius: 12px; background: var(--brand-soft); outline: 1.5px dashed color-mix(in srgb, var(--brand) 55%, transparent); outline-offset: -1.5px; }
.worked { position: absolute; top: 12px; bottom: 12px; border-radius: 10px; background: var(--brand); }
.compact .worked { top: 8px; bottom: 8px; }
.worked.live { background: repeating-linear-gradient(-45deg, var(--brand) 0 8px, color-mix(in srgb, var(--brand) 75%, white) 8px 16px); }
.punch { position: absolute; top: 50%; width: 14px; height: 14px; margin-inline-start: -7px; transform: translateY(-50%); border-radius: 50%; background: var(--surface); border: 3px solid var(--brand); }
.punch.out { border-color: var(--ink-2); }
.now { position: absolute; top: -18px; bottom: -6px; width: 2px; margin-inline-start: -1px; background: var(--saffron); }
.now-l { position: absolute; top: -2px; inset-inline-start: 6px; font-size: 11px; font-weight: 600; color: var(--saffron-ink); white-space: nowrap; }
.scale { position: relative; height: 18px; margin-top: 6px; font-size: 11px; color: var(--ink-3); }
.scale span { position: absolute; transform: translateX(-50%); }
[dir="rtl"] .scale span { transform: translateX(50%); }
.scale span:first-child { transform: none; }
.scale span:last-child { transform: translateX(-100%); }
[dir="rtl"] .scale span:last-child { transform: translateX(100%); }
.legend { display: flex; gap: 18px; margin-top: 8px; color: var(--ink-2); flex-wrap: wrap; }
.k { display: inline-block; width: 14px; height: 8px; border-radius: 4px; margin-inline-end: 6px; vertical-align: middle; }
.shift-k { background: var(--brand-soft); outline: 1px dashed var(--brand); }
.work-k { background: var(--brand); }
</style>
