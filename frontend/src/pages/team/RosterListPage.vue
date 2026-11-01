<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useResource } from "@/composables/useResource";
import { Roster } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import { addDays } from "@/utils/format";
import PageHeader from "@/components/ui/PageHeader.vue";
import DataTable from "@/components/ui/DataTable.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import AccessibleDialog from "@/components/ui/AccessibleDialog.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";

const router = useRouter();
const ui = useUi();
const { data, loading, error, reload } = useResource<any[]>(() => "rosters", () => Roster.list());
const { data: team } = useResource<any[]>(() => "roster:team", () => Roster.teamMembers());
const open = ref(false);
const busy = ref(false);
function nextSunday() { const d = new Date(); d.setDate(d.getDate() + ((7 - d.getDay()) % 7 || 7)); return d.toISOString().slice(0, 10); }
const form = ref<any>({ title: "", from_date: "", to_date: "", employees: [] as string[], prefill: "current" });
function start() {
  const s = nextSunday();
  form.value = { title: `Roster ${fmtDate(s, { day: "numeric", month: "short" })}`, from_date: s, to_date: addDays(s, 13), employees: (team.value || []).map((x) => x.name), prefill: "current" };
  open.value = true;
}
const allChecked = computed(() => team.value && form.value.employees.length === team.value.length);
function toggleAll() { form.value.employees = allChecked.value ? [] : (team.value || []).map((x) => x.name); }
async function create() {
  busy.value = true;
  try { const r: any = await Roster.create(form.value); router.push(`/team/roster/${r.name}`); }
  catch (e: any) { ui.toast(e.message, "error"); } finally { busy.value = false; }
}
</script>

<template>
  <div class="page">
    <PageHeader title="Roster planner" subtitle="Plan shifts and rest days, check coverage and working-time rules, then publish to Frappe HR.">
      <button class="btn primary" @click="start">New roster</button>
    </PageHeader>
    <ErrorState :error="error" @retry="reload" />
    <section class="panel">
      <SkeletonLoader v-if="loading && !data" :lines="5" />
      <DataTable v-else :rows="data || []" row-key="name" clickable empty="No rosters yet. Create one to start planning." @row="(r: any) => router.push(`/team/roster/${r.name}`)"
        :columns="[{ key: 'title', label: 'Roster' }, { key: 'period', label: 'Period' }, { key: 'employees', label: 'People', numeric: true }, { key: 'status', label: t('Status') }, { key: 'pending_requests', label: 'Change requests', numeric: true }]">
        <template #title="{ row }"><strong>{{ row.title }}</strong><br><span class="small muted">{{ row.name }}<template v-if="row.department"> · {{ row.department }}</template></span></template>
        <template #period="{ row }">{{ fmtDate(row.from_date, { day: "numeric", month: "short" }) }} – {{ fmtDate(row.to_date) }}</template>
        <template #status="{ row }"><StatusBadge :status="row.status === 'Published' ? 'Approved' : row.status === 'Draft' ? 'Draft' : 'Closed'" :label="row.status" />
          <span v-if="row.has_unpublished_changes" class="small warn"> · unpublished changes</span></template>
      </DataTable>
    </section>

    <AccessibleDialog :open="open" title="New roster" wide @close="open = false">
      <form id="nr" class="stack" @submit.prevent="create">
        <div class="field"><label for="rt">Name</label><input id="rt" class="input" v-model="form.title" required /></div>
        <div class="form-grid">
          <div class="field"><label for="rf">{{ t("From") }}</label><input id="rf" type="date" class="input" v-model="form.from_date" required /></div>
          <div class="field"><label for="rto">{{ t("To") }}</label><input id="rto" type="date" class="input" v-model="form.to_date" :min="form.from_date" required /><span class="hint">Up to 9 weeks.</span></div>
        </div>
        <div class="field"><label for="pf">Start from</label>
          <select id="pf" class="select" v-model="form.prefill">
            <option value="current">Current shift assignments and weekly offs</option><option value="empty">An empty grid</option>
            <option v-for="r in (data || []).filter((x) => x.status !== 'Archived')" :key="r.name" :value="`copy:${r.name}`">Copy {{ r.title }} (repeats its weeks)</option></select></div>
        <div class="field"><span class="spread"><label>People</label><button type="button" class="btn ghost sm" @click="toggleAll">{{ allChecked ? "Clear all" : "Select all" }}</button></span>
          <div class="people"><label v-for="e in team || []" :key="e.name" class="check"><input type="checkbox" :value="e.name" v-model="form.employees" />{{ e.employee_name }} <span class="small muted">{{ e.designation }}</span></label></div></div>
      </form>
      <template #footer><button class="btn" @click="open = false">{{ t("Cancel") }}</button><button class="btn primary" form="nr" :disabled="busy || !form.employees.length">Create and plan</button></template>
    </AccessibleDialog>
  </div>
</template>

<style scoped>
.people { max-height: 260px; overflow-y: auto; border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
.warn { color: var(--saffron-ink); }
</style>
