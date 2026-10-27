<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useResource, invalidate } from "@/composables/useResource";
import { Expenses } from "@/services/endpoints";
import { fmtDate, fmtMoney, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import DataTable from "@/components/ui/DataTable.vue";
import AccessibleDialog from "@/components/ui/AccessibleDialog.vue";
import MetricCard from "@/components/ui/MetricCard.vue";
import ApprovalTimeline from "@/components/hr/ApprovalTimeline.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";

const route = useRoute();
const ui = useUi();
const tab = ref("claims");
const { data, loading, reload } = useResource<any>(() => "expenses", () => Expenses.overview());
const claim = ref<any>(null);
const advOpen = ref(false);
const adv = ref({ purpose: "", advance_amount: 0 });

async function open(name: string) { claim.value = await Expenses.detail(name); }
watch(() => route.query.claim, (c) => c && open(String(c)), { immediate: true });
async function requestAdvance() {
  try { await Expenses.advance(adv.value); ui.toast("Advance request sent"); advOpen.value = false; invalidate("expenses"); reload(); }
  catch (e: any) { ui.toast(e.message, "error"); }
}
function steps(c: any) {
  return [
    { label: "Submitted", when: c.posting_date, state: "done" as const },
    { label: c.approval_status === "Rejected" ? "Rejected" : "Approval", who: c.expense_approver, state: c.approval_status === "Approved" ? "done" as const : c.approval_status === "Rejected" ? "rejected" as const : "current" as const },
    { label: "Paid", state: c.status === "Paid" ? "done" as const : "todo" as const },
  ];
}
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Expenses')">
      <button class="btn" @click="advOpen = true">Request advance</button>
      <RouterLink to="/finances/expenses/new" class="btn primary">{{ t("New claim") }}</RouterLink>
    </PageHeader>
    <div class="metrics" v-if="data">
      <MetricCard label="Waiting for approval" :value="fmtMoney(data.totals.pending, data.currency)" tone="warn" />
      <MetricCard label="Approved, not yet paid" :value="fmtMoney(data.totals.approved_unpaid, data.currency)" tone="ok" />
    </div>
    <SegmentTabs v-model="tab" :tabs="[{ value: 'claims', label: 'Claims', count: data?.claims.length }, { value: 'advances', label: 'Advances', count: data?.advances.length }]" />
    <section class="panel">
      <SkeletonLoader v-if="loading && !data" />
      <DataTable v-else-if="tab === 'claims'" :rows="data?.claims || []" row-key="name" clickable @row="(r: any) => open(r.name)" empty="No claims yet"
        :columns="[{ key: 'name', label: 'Claim' }, { key: 'posting_date', label: t('Date') }, { key: 'total_claimed_amount', label: 'Claimed', numeric: true }, { key: 'total_sanctioned_amount', label: 'Approved', numeric: true }, { key: 'approval_status', label: t('Status') }]">
        <template #posting_date="{ row }">{{ fmtDate(row.posting_date) }}</template>
        <template #total_claimed_amount="{ row }">{{ fmtMoney(row.total_claimed_amount, row.currency) }}</template>
        <template #total_sanctioned_amount="{ row }">{{ row.total_sanctioned_amount ? fmtMoney(row.total_sanctioned_amount, row.currency) : "—" }}</template>
        <template #approval_status="{ row }"><StatusBadge :status="row.status === 'Paid' ? 'Paid' : row.approval_status === 'Draft' ? 'Pending' : row.approval_status" /></template>
      </DataTable>
      <DataTable v-else :rows="data?.advances || []" row-key="name" empty="No advances requested"
        :columns="[{ key: 'purpose', label: 'Purpose' }, { key: 'posting_date', label: t('Date') }, { key: 'advance_amount', label: t('Amount'), numeric: true }, { key: 'claimed_amount', label: 'Settled', numeric: true }, { key: 'status', label: t('Status') }]">
        <template #posting_date="{ row }">{{ fmtDate(row.posting_date) }}</template>
        <template #advance_amount="{ row }">{{ fmtMoney(row.advance_amount, row.currency) }}</template>
        <template #claimed_amount="{ row }">{{ fmtMoney(row.claimed_amount || 0, row.currency) }}</template>
        <template #status="{ row }"><StatusBadge :status="row.status" /></template>
      </DataTable>
    </section>

    <AccessibleDialog :open="!!claim" :title="claim ? `Claim ${claim.name}` : ''" wide @close="claim = null">
      <div v-if="claim" class="stack">
        <ApprovalTimeline :steps="steps(claim)" />
        <table class="data"><thead><tr><th>{{ t("Date") }}</th><th>Type</th><th>{{ t("Description") }}</th><th class="n">{{ t("Amount") }}</th><th class="n">Approved</th></tr></thead>
          <tbody><tr v-for="(l, i) in claim.expenses" :key="i"><td>{{ fmtDate(l.expense_date) }}</td><td>{{ l.expense_type }}</td><td>{{ l.description }}</td>
            <td class="n">{{ fmtMoney(l.amount, claim.currency) }}</td><td class="n">{{ l.sanctioned_amount ? fmtMoney(l.sanctioned_amount, claim.currency) : "—" }}</td></tr></tbody></table>
        <div v-if="claim.attachments.length"><h3>{{ t("Receipts") }}</h3>
          <ul><li v-for="a in claim.attachments" :key="a.file_url"><a :href="a.file_url" target="_blank" rel="noopener">{{ a.file_name }}</a></li></ul></div>
        <div v-if="claim.timeline.length"><h3>Comments</h3><p v-for="(c, i) in claim.timeline" :key="i" class="small" v-html="c.content" /></div>
      </div>
    </AccessibleDialog>

    <AccessibleDialog :open="advOpen" title="Request an advance" @close="advOpen = false">
      <form id="adv" class="stack" @submit.prevent="requestAdvance">
        <div class="field"><label for="ap">{{ t("Purpose") }}</label><input id="ap" class="input" v-model="adv.purpose" required /></div>
        <div class="field"><label for="aa">{{ t("Amount") }} ({{ data?.currency }})</label><input id="aa" class="input" type="number" min="0" step="0.001" v-model.number="adv.advance_amount" required /></div>
      </form>
      <template #footer><button class="btn" @click="advOpen = false">{{ t("Cancel") }}</button><button class="btn primary" form="adv">Send request</button></template>
    </AccessibleDialog>
  </div>
</template>

<style scoped>.metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 260px)); gap: 8px; }</style>
