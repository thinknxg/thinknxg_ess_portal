<script setup lang="ts">
import { computed } from "vue";
import { useResource } from "@/composables/useResource";
import { Analytics } from "@/services/endpoints";
import { fmtNum, t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import MetricCard from "@/components/ui/MetricCard.vue";
import BarChart from "@/components/hr/BarChart.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";

const { data: d, loading, error, reload } = useResource<any>(() => "an:hr", () => Analytics.hr());
const backlog = computed(() => (d.value?.tickets_by_status || []).filter((r: any) => !["Resolved", "Closed"].includes(r.status)).reduce((a: number, r: any) => a + r.n, 0));
</script>

<template>
  <div class="page">
    <PageHeader :title="t('HR analytics')" subtitle="Last 90 days, within your HR scope. Groups smaller than the privacy threshold are hidden." />
    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !d" :lines="8" />
    <template v-if="d">
      <div class="metrics">
        <MetricCard label="Ticket backlog" :value="backlog" :tone="backlog > 20 ? 'warn' : undefined" />
        <MetricCard label="SLA compliance" :value="d.sla_compliance === null ? '—' : `${d.sla_compliance}%`" :tone="d.sla_compliance !== null && d.sla_compliance < 90 ? 'bad' : 'ok'" />
        <MetricCard label="Open attendance corrections" :value="d.open_attendance_corrections" />
        <MetricCard label="Documents expiring (60 days)" :value="d.expiring_documents.reduce((a: number, r: any) => a + r.n, 0)" tone="warn" />
      </div>
      <div class="cols-2">
        <section class="panel"><header><h2>Service by category</h2></header>
          <div class="table-wrap"><table class="data"><thead><tr><th>{{ t("Category") }}</th><th class="n">Tickets</th><th class="n">Breached</th><th class="n">First reply (h)</th><th class="n">Resolve (h)</th><th class="n">Rating</th></tr></thead>
            <tbody><tr v-for="c in d.by_category" :key="c.category"><td>{{ c.category }}</td><td class="n">{{ c.n }}</td><td class="n">{{ c.breached || 0 }}</td>
              <td class="n">{{ fmtNum(c.frt) }}</td><td class="n">{{ fmtNum(c.rt) }}</td><td class="n">{{ c.csat ? fmtNum(c.csat) + " / 5" : "—" }}</td></tr></tbody></table></div></section>
        <section class="panel"><header><h2>Portal adoption, last 30 days</h2></header>
          <BarChart title="Daily active employees" :labels="d.adoption.map((a: any) => String(a.d).slice(8))" :series="[{ name: 'Active employees', values: d.adoption.map((a: any) => a.n), color: 'var(--brand)' }]" /></section>
        <section class="panel"><header><h2>Document requests</h2></header>
          <ul class="list"><li v-for="r in d.documents_by_status" :key="r.status"><span class="grow">{{ r.status }}</span><span class="num">{{ r.n }}</span></li></ul></section>
        <section class="panel"><header><h2>Expiring employee documents</h2></header>
          <ul class="list"><li v-for="r in d.expiring_documents" :key="r.document_type"><span class="grow">{{ r.document_type }}</span><span class="num">{{ r.n }}</span></li></ul>
          <RouterLink to="/hr/employees" class="small">See the list</RouterLink></section>
        <section class="panel"><header><h2>Headcount by department</h2></header>
          <ul class="list"><li v-for="r in d.headcount" :key="r.department || 'none'"><span class="grow">{{ r.department || "No department" }}</span><span class="num">{{ r.suppressed ? "fewer than threshold" : r.n }}</span></li></ul></section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); padding: 6px; }
@media (max-width: 760px) { .metrics { grid-template-columns: repeat(2, 1fr); } }
</style>
