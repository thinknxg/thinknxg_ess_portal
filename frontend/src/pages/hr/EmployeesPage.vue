<script setup lang="ts">
import { ref, watch } from "vue";
import { HR } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import Avatar from "@/components/ui/Avatar.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import AccessibleDialog from "@/components/ui/AccessibleDialog.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import { useResource } from "@/composables/useResource";

const ui = useUi();
const tab = ref("search");
const q = ref("");
const rows = ref<any[]>([]);
const busy = ref(false);
const detail = ref<any>(null);
const { data: expiring, reload: reloadExp } = useResource<any[]>(() => "hr:exp", () => HR.expiring(60));
let tm: number | undefined;
watch(q, () => { window.clearTimeout(tm); tm = window.setTimeout(search, 300); });
async function search() { busy.value = true; try { rows.value = await HR.search(q.value); } finally { busy.value = false; } }
search();
async function open(e: string) { detail.value = await HR.employee(e); }
async function verify(name: string) { await HR.verifyDocument(name, 1); ui.toast("Marked as verified"); reloadExp(); if (detail.value) open(detail.value.name); }
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Employees')" subtitle="Lookups are limited to your HR scope and recorded in the audit trail." />
    <SegmentTabs v-model="tab" :tabs="[{ value: 'search', label: 'Directory' }, { value: 'expiry', label: 'Document expiry', count: expiring?.length }]" />
    <section class="panel" v-if="tab === 'search'">
      <input class="input" v-model="q" :placeholder="t('Search employees')" :aria-label="t('Search employees')" />
      <ul class="list" v-if="rows.length" style="margin-top: 12px">
        <li v-for="r in rows" :key="r.name"><button class="rowlink plain" @click="open(r.name)">
          <Avatar :name="r.employee_name" :image="r.image" :size="34" />
          <span class="grow"><span class="title">{{ r.employee_name }}</span><br><span class="small muted">{{ r.name }} · {{ r.designation }} · {{ r.department }}</span></span>
          <span class="small muted">{{ fmtDate(r.date_of_joining) }}</span></button></li>
      </ul>
      <EmptyState v-else-if="!busy" :title="t('No results')" icon="search" />
    </section>
    <section class="panel" v-else>
      <table class="data" v-if="expiring?.length">
        <thead><tr><th>Employee</th><th>Document</th><th>Expires</th><th>Verified</th><th /></tr></thead>
        <tbody><tr v-for="d in expiring" :key="d.name"><td>{{ d.employee_name }}</td><td>{{ d.document_type }} <span class="muted small">{{ d.document_number }}</span></td>
          <td><StatusBadge :status="d.expiry_date < new Date().toISOString().slice(0, 10) ? 'Overdue' : 'Pending'" :label="fmtDate(d.expiry_date)" /></td>
          <td>{{ d.verified ? "Yes" : "No" }}</td><td><button v-if="!d.verified" class="btn sm" @click="verify(d.name)">Verify</button></td></tr></tbody>
      </table>
      <EmptyState v-else title="Nothing expiring in the next 60 days" icon="file" />
    </section>

    <AccessibleDialog :open="!!detail" :title="detail?.employee_name || ''" wide @close="detail = null">
      <div v-if="detail" class="stack">
        <dl class="kv"><div v-for="k in ['name', 'designation', 'department', 'branch', 'company', 'employment_type', 'company_email', 'cell_number', 'nationality']" :key="k"><dt>{{ k.replace('_', ' ') }}</dt><dd>{{ detail[k] || "—" }}</dd></div>
          <div><dt>joined</dt><dd>{{ fmtDate(detail.date_of_joining) }}</dd></div><div><dt>open tickets</dt><dd>{{ detail.open_tickets }}</dd></div></dl>
        <h3>Documents</h3>
        <ul class="list"><li v-for="d in detail.documents" :key="d.name"><span class="grow">{{ d.document_type }} <span class="small muted">{{ d.document_number }}</span></span><span class="small">{{ fmtDate(d.expiry_date) }}</span>
          <StatusBadge :status="d.verified ? 'Verified' : 'Pending'" :tone="d.verified ? 'ok' : 'warn'" :label="d.verified ? 'Verified' : 'Unverified'" /><button v-if="!d.verified" class="btn sm" @click="verify(d.name)">Verify</button></li></ul>
        <h3>{{ t("Leave balance") }}</h3>
        <ul class="list"><li v-for="b in detail.balances" :key="b.leave_type"><span class="grow">{{ b.leave_type }}</span><span class="num">{{ b.remaining }} / {{ b.allocated }}</span></li></ul>
        <p v-if="detail.pending_changes.length" class="small">Pending profile updates: {{ detail.pending_changes.join(", ") }} — review them in <RouterLink to="/team/approvals" @click="detail = null">Approvals</RouterLink>.</p>
        <a :href="`/app/employee/${detail.name}`" class="small">Open full record in Desk</a>
      </div>
    </AccessibleDialog>
  </div>
</template>

<style scoped>
.plain { border: 0; background: none; cursor: pointer; text-align: start; padding: 0; }
.kv { margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 10px; }
dt { font-size: var(--fs-xs); color: var(--ink-3); text-transform: capitalize; } dd { margin: 0; overflow-wrap: anywhere; }
</style>
