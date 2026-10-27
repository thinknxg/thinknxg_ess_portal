<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useResource } from "@/composables/useResource";
import { Helpdesk } from "@/services/endpoints";
import { fmtDate, relative, t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import DataTable from "@/components/ui/DataTable.vue";
import MetricCard from "@/components/ui/MetricCard.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";

const router = useRouter();
const assigned = ref("me");
const f = ref({ status: "open", category: "", priority: "", sla: "", q: "" });
const params = computed(() => ({ ...f.value, assigned: assigned.value === "all" ? undefined : assigned.value }));
const { data, loading, error, reload } = useResource<any>(() => `queue:${JSON.stringify(params.value)}`, () => Helpdesk.queue(params.value), { watch: [params], staleMs: 10_000 });
const { data: cats } = useResource<any[]>(() => "ticket:cats", () => Helpdesk.categories(), { staleMs: 600_000 });
const stat = (k: string, v?: string) => (data.value?.stats || []).filter((s: any) => (k === "sla" ? s.sla_status === v : s.status === v)).reduce((a: number, s: any) => a + s.n, 0);
const PRI: Record<string, string> = { Urgent: "bad", High: "warn", Medium: "muted", Low: "muted" };
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Service desk')" subtitle="Tickets are ordered by priority and how soon they're due." />
    <div class="metrics" v-if="data">
      <MetricCard :label="t('Open')" :value="stat('s', 'Open') + stat('s', 'Assigned')" />
      <MetricCard :label="t('In Progress')" :value="stat('s', 'In Progress')" />
      <MetricCard :label="t('Waiting for Employee')" :value="stat('s', 'Waiting for Employee')" />
      <MetricCard label="At risk" :value="stat('sla', 'At Risk')" tone="warn" />
      <MetricCard label="Breached" :value="stat('sla', 'Breached')" tone="bad" />
    </div>
    <SegmentTabs v-model="assigned" :tabs="[{ value: 'me', label: t('Assigned to me') }, { value: 'unassigned', label: t('Unassigned') }, { value: 'all', label: t('All') }]" />
    <div class="filters">
      <input class="input" v-model.lazy="f.q" placeholder="Search subject, ticket or employee" aria-label="Search tickets" />
      <select class="select" v-model="f.status" aria-label="Status"><option value="open">All open</option><option value="">Any status</option>
        <option v-for="s in ['Open', 'Assigned', 'In Progress', 'Waiting for Employee', 'Resolved', 'Closed']" :key="s" :value="s">{{ t(s) }}</option></select>
      <select class="select" v-model="f.category" aria-label="Category"><option value="">All categories</option><option v-for="c in cats || []" :key="c.name">{{ c.name }}</option></select>
      <select class="select" v-model="f.priority" aria-label="Priority"><option value="">Any priority</option><option>Urgent</option><option>High</option><option>Medium</option><option>Low</option></select>
      <select class="select" v-model="f.sla" aria-label="Service level"><option value="">Any SLA</option><option>On Track</option><option>At Risk</option><option>Breached</option></select>
    </div>
    <ErrorState :error="error" @retry="reload" />
    <section class="panel">
      <SkeletonLoader v-if="loading && !data" :lines="8" />
      <DataTable v-else :rows="data?.tickets || []" row-key="name" clickable empty="No tickets match these filters" @row="(r: any) => router.push(`/hr/tickets/${r.name}`)"
        :columns="[{ key: 'subject', label: t('Subject') }, { key: 'employee_name', label: 'Employee' }, { key: 'priority', label: t('Priority') }, { key: 'status', label: t('Status') }, { key: 'resolution_due', label: 'Due' }]">
        <template #subject="{ row }"><strong>{{ row.subject }}</strong><br><span class="small muted">{{ row.name }} · {{ row.category }}<template v-if="row.is_confidential"> · confidential</template></span></template>
        <template #employee_name="{ row }">{{ row.employee_name }}<br><span class="small muted">{{ row.department }}</span></template>
        <template #priority="{ row }"><StatusBadge :tone="PRI[row.priority] as any" :label="row.priority" /></template>
        <template #status="{ row }"><StatusBadge :status="row.status" /><br><span class="small muted">{{ relative(row.modified) }}</span></template>
        <template #resolution_due="{ row }"><StatusBadge :status="row.sla_status" :label="fmtDate(row.resolution_due, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })" />
          <span v-if="row.escalation_level" class="small bad"> L{{ row.escalation_level }}</span></template>
      </DataTable>
    </section>
  </div>
</template>

<style scoped>
.metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); padding: 6px; }
.filters { display: grid; grid-template-columns: 2fr repeat(4, 1fr); gap: 8px; }
.bad { color: var(--pom); font-weight: 600; }
@media (max-width: 900px) { .filters { grid-template-columns: 1fr 1fr; } .filters .input { grid-column: 1 / -1; } .metrics { grid-template-columns: repeat(2, 1fr); } }
</style>
