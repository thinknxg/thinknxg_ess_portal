<script setup lang="ts">
import { computed, ref } from "vue";
import { useResource } from "@/composables/useResource";
import { Roster } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import { isoToday } from "@/utils/format";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import EmptyState from "@/components/ui/EmptyState.vue";

const year = ref(new Date().getFullYear());
const { data, loading } = useResource<any>(() => `holidays:${year.value}`, () => Roster.holidays(year.value), { watch: [year] });
const nextHoliday = computed(() => (data.value?.holidays || []).find((h: any) => h.holiday_date >= isoToday()));
const daysUntil = computed(() => nextHoliday.value ? Math.round((+new Date(`${nextHoliday.value.holiday_date}T00:00:00`) - +new Date(`${isoToday()}T00:00:00`)) / 86400000) : null);
const months = computed(() => {
  const out: Record<string, any[]> = {};
  for (const h of data.value?.holidays || []) (out[h.holiday_date.slice(0, 7)] ||= []).push(h);
  return out;
});
const ics = computed(() => Roster.icsUrl(`${year.value}-01-01`, `${year.value}-12-31`));
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Holidays')" :subtitle="data?.holiday_list ? `From the ${data.holiday_list} holiday list` : undefined">
      <select class="select" v-model.number="year" aria-label="Year" style="width: auto"><option v-for="y in data?.years || [year]" :key="y" :value="y">{{ y }}</option></select>
      <a class="btn" :href="ics">Add to calendar (.ics)</a>
    </PageHeader>
    <SkeletonLoader v-if="loading && !data" :lines="8" />
    <template v-else-if="data">
      <section class="next" v-if="nextHoliday">
        <div class="dbox"><span class="m">{{ fmtDate(nextHoliday.holiday_date, { month: "short" }) }}</span><span class="d num">{{ fmtDate(nextHoliday.holiday_date, { day: "numeric" }) }}</span></div>
        <div><p class="muted small">Next holiday</p><h2>{{ nextHoliday.description }}</h2><p class="muted">{{ fmtDate(nextHoliday.holiday_date, { weekday: "long" }) }} · {{ daysUntil === 0 ? "today" : daysUntil === 1 ? "tomorrow" : `in ${daysUntil} days` }}</p></div>
      </section>
      <div class="cols">
        <section class="panel">
          <header><h2>Public and company holidays, {{ data.year }}</h2></header>
          <template v-if="data.holidays.length">
            <div v-for="(rows, mo) in months" :key="mo" class="month">
              <h3>{{ fmtDate(`${mo}-01`, { month: "long" }) }}</h3>
              <ul class="list">
                <li v-for="h in rows" :key="h.holiday_date" :class="{ past: h.holiday_date < isoToday() }">
                  <span class="date num">{{ fmtDate(h.holiday_date, { weekday: "short", day: "numeric" }) }}</span><span class="grow">{{ h.description }}</span></li>
              </ul>
            </div>
          </template>
          <EmptyState v-else title="No holidays listed for this year" text="Ask HR to publish the holiday list." icon="calendar" />
        </section>
        <aside class="panel">
          <header><h2>Days off</h2></header>
          <dl class="kv">
            <div><dt>Holidays</dt><dd class="num">{{ data.holidays.length }}</dd></div>
            <div><dt>Weekly offs</dt><dd class="num">{{ data.weekly_off_count }}</dd></div>
            <div v-if="data.roster_rest_days"><dt>Roster rest days</dt><dd class="num">{{ data.roster_rest_days }}</dd></div>
          </dl>
          <p class="small muted" v-if="Object.keys(data.weekly_offs).length">Weekly off on {{ Object.keys(data.weekly_offs).join(" and ") }}.</p>
          <p class="small muted">If you work shifts, your roster decides your working days. <RouterLink to="/roster">{{ t("My roster") }}</RouterLink></p>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.next { display: flex; align-items: center; gap: 18px; padding: 18px 20px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); }
.dbox { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 72px; height: 76px; border-radius: 14px; background: var(--saffron-soft); color: var(--saffron-ink); }
.dbox .m { font-size: var(--fs-sm); font-weight: 600; } .dbox .d { font-size: 28px; font-weight: 700; line-height: 1; }
.month + .month { margin-top: 16px; }
.month h3 { font-size: var(--fs-sm); color: var(--ink-3); font-weight: 500; margin-bottom: 4px; }
.date { min-width: 76px; font-weight: 600; color: var(--brand); }
.past { opacity: .55; }
.kv { margin: 0 0 12px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
dt { font-size: var(--fs-xs); color: var(--ink-3); } dd { margin: 0; font-size: var(--fs-xl); font-weight: 600; }
</style>
