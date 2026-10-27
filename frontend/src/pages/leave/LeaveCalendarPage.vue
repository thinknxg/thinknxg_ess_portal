<script setup lang="ts">
import { computed, ref } from "vue";
import { useResource } from "@/composables/useResource";
import { Leave } from "@/services/endpoints";
import { useSession } from "@/stores/session";
import { fmtDate, t } from "@/i18n";
import { addDays } from "@/utils/format";
import PageHeader from "@/components/ui/PageHeader.vue";
import MonthCalendar, { type DayCell } from "@/components/hr/MonthCalendar.vue";

const props = defineProps<{ team?: boolean }>();
const s = useSession();
const now = new Date();
const y = ref(now.getFullYear());
const m = ref(now.getMonth() + 1);
const showTeam = ref(props.team ? 1 : 0);
const selected = ref<string | null>(null);
const { data } = useResource<any>(() => `leave:cal:${y.value}-${m.value}:${showTeam.value}`, () => Leave.calendar(y.value, m.value, showTeam.value), { watch: [y, m, showTeam] });

const byDay = computed(() => {
  const out: Record<string, any[]> = {};
  for (const e of data.value?.events || []) {
    for (let d = e.start; d <= e.end; d = addDays(d, 1)) (out[d] ||= []).push(e);
  }
  return out;
});
const TONE: Record<string, string> = { mine: "brand", holiday: "warn", team: "info", weekly_off: "" };
const cells = computed<Record<string, DayCell>>(() => {
  const out: Record<string, DayCell> = {};
  for (const [d, evs] of Object.entries(byDay.value)) {
    const mine = evs.find((e) => e.kind === "mine");
    const hol = evs.find((e) => e.kind === "holiday");
    out[d] = { date: d, tone: TONE[(mine || hol || evs[0]).kind], label: (mine || hol)?.title,
      marks: evs.filter((e) => e.kind === "team").map((e) => ({ tone: "info", text: e.title })) };
  }
  return out;
});
function shift(n: number) { const d = new Date(y.value, m.value - 1 + n, 1); y.value = d.getFullYear(); m.value = d.getMonth() + 1; }
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Leave calendar')" :back="props.team ? '/team' : '/leave'">
      <label v-if="s.can('manager')" class="check"><input type="checkbox" :checked="!!showTeam" @change="showTeam = ($event.target as HTMLInputElement).checked ? 1 : 0" />Show my team</label>
    </PageHeader>
    <div class="cols">
      <section class="panel">
        <MonthCalendar :year="y" :month="m" :cells="cells" :selected="selected" @select="selected = $event" @prev="shift(-1)" @next="shift(1)" />
        <p class="legend small"><span><i class="brand" />My leave</span><span><i class="warn" />{{ t("Holiday") }}</span><span v-if="showTeam"><i class="info" />Team</span></p>
      </section>
      <section class="panel">
        <template v-if="selected">
          <header><h2>{{ fmtDate(selected, { weekday: "long", day: "numeric", month: "long" }) }}</h2></header>
          <ul class="list" v-if="byDay[selected]?.length">
            <li v-for="(e, i) in byDay[selected]" :key="i"><span class="grow">{{ e.title }}</span><span class="small muted">{{ e.status || (e.kind === "holiday" ? t("Holiday") : "") }}</span></li>
          </ul>
          <p v-else class="muted">Nothing scheduled.</p>
        </template>
        <p v-else class="muted">Select a day to see who's away and which holidays apply.</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.legend { display: flex; gap: 16px; margin-top: 12px; color: var(--ink-2); }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-inline-end: 6px; }
.legend .brand { background: var(--brand); } .legend .warn { background: var(--saffron); } .legend .info { background: var(--info); }
</style>
