<script setup lang="ts">
import { computed } from "vue";
import { useResource } from "@/composables/useResource";
import { Analytics, Recognition } from "@/services/endpoints";
import { useSession } from "@/stores/session";
import { t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import MetricCard from "@/components/ui/MetricCard.vue";
import BarChart from "@/components/hr/BarChart.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";

const s = useSession();
const { data: d, loading, error, reload } = useResource<any>(() => "an:mgr", () => Analytics.manager());
const { data: rec } = s.module("recognition") ? useResource<any>(() => "rec:team", () => Recognition.team()) : { data: { value: null } as any };
const labels = computed(() => (d.value?.trend || []).map((r: any) => r.month.slice(5)));
const ageSeries = computed(() => [{ name: "Approvals waiting", values: Object.values(d.value?.approval_age || {}) as number[], color: "var(--saffron)" }]);
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Team analytics')" subtitle="Team-level trends to help you plan. Individual rankings are intentionally not shown." />
    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !d" :lines="8" />
    <template v-if="d">
      <p v-if="d.suppressed" class="note small">Your team is small, so some trends could identify individuals. Treat them with care.</p>
      <div class="metrics">
        <MetricCard label="Team size" :value="d.team_size" />
        <MetricCard label="Checked in today" :value="d.checked_in_today" tone="ok" />
        <MetricCard label="On leave today" :value="d.on_leave_today" />
        <MetricCard label="Not yet checked in" :value="d.not_checked_in" :tone="d.not_checked_in ? 'warn' : undefined" />
        <MetricCard label="Waiting for you" :value="d.pending_approvals" :tone="d.pending_approvals ? 'warn' : undefined" />
      </div>
      <div class="cols-2">
        <section class="panel"><header><h2>Late arrivals and absences</h2></header>
          <BarChart title="Late arrivals and absences by month" :labels="labels" :series="[{ name: t('Late'), values: d.trend.map((r: any) => r.late), color: 'var(--saffron)' }, { name: t('Absent'), values: d.trend.map((r: any) => r.absent), color: 'var(--pom)' }]" /></section>
        <section class="panel"><header><h2>How long approvals wait</h2></header>
          <BarChart title="Pending approvals by age" :labels="Object.keys(d.approval_age)" :series="ageSeries" /></section>
        <section class="panel" v-if="Object.keys(d.goals).length"><header><h2>Goal status</h2></header>
          <ul class="list"><li v-for="(n, k) in d.goals" :key="k"><span class="grow">{{ k }}</span><span class="num">{{ n }}</span></li></ul></section>
        <section class="panel" v-if="d.overtime?.length"><header><h2>Overtime hours</h2></header>
          <BarChart title="Overtime hours by month" :labels="d.overtime.map((o: any) => o.m.slice(5))" :series="[{ name: 'Hours', values: d.overtime.map((o: any) => Math.round(o.hours)), color: 'var(--info)' }]" /></section>
        <section class="panel" v-if="rec"><header><h2>Recognition in the last 90 days</h2></header>
          <ul class="list"><li v-for="r in rec.by_category" :key="r.category"><span class="grow">{{ r.category }}</span><span class="num">{{ r.n }}</span></li></ul>
          <p class="small muted" v-if="rec.not_recognised_90d">{{ rec.not_recognised_90d }} of {{ rec.team_size }} people haven't been recognised recently.</p></section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); padding: 6px; }
.note { padding: 10px 14px; border-radius: 10px; background: var(--saffron-soft); color: var(--saffron-ink); }
@media (max-width: 760px) { .metrics { grid-template-columns: repeat(2, 1fr); } }
</style>
