<script setup lang="ts">
import { ref } from "vue";
import { useResource } from "@/composables/useResource";
import { Documents } from "@/services/endpoints";
import { downloadUrl } from "@/services/api";
import { fmtDate, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import DataTable from "@/components/ui/DataTable.vue";

const ui = useUi();
const status = ref("");
const tab = ref("requests");
const { data, reload } = useResource<any>(() => `docadmin:${status.value}`, () => Documents.admin(status.value || undefined), { watch: [status] });
async function regen(name: string) { await Documents.regenerate(name); ui.toast("Regeneration queued"); reload(); }
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Document admin')" subtitle="Generated letters, their template versions and approvals. Edit templates in Desk.">
      <a href="/app/ess-document-template" class="btn">Edit templates</a>
    </PageHeader>
    <SegmentTabs v-model="tab" :tabs="[{ value: 'requests', label: 'Requests' }, { value: 'templates', label: 'Templates', count: data?.templates.length }]" />
    <section class="panel" v-if="tab === 'requests'">
      <div class="row" style="margin-bottom: 12px"><label for="st" class="small muted">{{ t("Status") }}</label>
        <select id="st" class="select" v-model="status" style="max-width: 220px"><option value="">All</option>
          <option v-for="s in ['Requested', 'Pending Approval', 'Approved', 'Generated', 'Rejected', 'Cancelled']" :key="s">{{ s }}</option></select></div>
      <DataTable :rows="data?.requests || []" row-key="name" empty="No requests"
        :columns="[{ key: 'employee_name', label: 'Employee' }, { key: 'template', label: 'Document' }, { key: 'status', label: t('Status') }, { key: 'creation', label: 'Requested' }, { key: 'verification_code', label: 'Code' }, { key: 'act', label: '' }]">
        <template #template="{ row }">{{ row.template }} <span class="small muted">v{{ row.template_version }}</span><br><span class="small muted">{{ row.purpose }}</span></template>
        <template #status="{ row }"><StatusBadge :status="row.status" /></template>
        <template #creation="{ row }">{{ fmtDate(row.creation) }}</template>
        <template #act="{ row }">
          <a v-if="row.status === 'Generated'" class="btn ghost sm" :href="downloadUrl('documents.download', { name: row.name })">{{ t("Download") }}</a>
          <button v-if="['Generated', 'Approved'].includes(row.status)" class="btn ghost sm" @click="regen(row.name)">Regenerate</button>
        </template>
      </DataTable>
    </section>
    <section class="panel" v-else>
      <DataTable :rows="data?.templates || []" row-key="name"
        :columns="[{ key: 'name', label: 'Template' }, { key: 'document_type', label: 'Type' }, { key: 'version', label: 'Version', numeric: true }, { key: 'flags', label: 'Rules' }, { key: 'modified', label: 'Last changed' }]">
        <template #name="{ row }"><a :href="`/app/ess-document-template/${encodeURIComponent(row.name)}`">{{ row.name }}</a></template>
        <template #flags="{ row }"><StatusBadge :tone="row.is_active ? 'ok' : 'muted'" :label="row.is_active ? 'Active' : 'Inactive'" />
          <StatusBadge v-if="row.requires_approval" tone="info" label="Approval" /> <StatusBadge v-if="row.include_salary" tone="warn" label="Shows salary" /></template>
        <template #modified="{ row }">{{ fmtDate(row.modified) }}</template>
      </DataTable>
    </section>
  </div>
</template>
