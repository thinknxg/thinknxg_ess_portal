<script setup lang="ts">
import { ref, watch } from "vue";
import { useResource } from "@/composables/useResource";
import { HR } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import AccessibleDialog from "@/components/ui/AccessibleDialog.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";

const ui = useUi();
const tab = ref("modules");
const { data, reload } = useResource<any>(() => "hr:settings", () => HR.settings());
const { data: audit } = useResource<any[]>(() => "hr:audit", () => HR.audit());
const { data: aiq } = useResource<any>(() => "hr:aiq", () => HR.aiQuality());
const form = ref<any>({});
const apiKey = ref("");
watch(data, (d) => { if (d) form.value = { ...d }; }, { immediate: true });
const MODULES = ["attendance", "checkin", "leave", "payroll", "expenses", "helpdesk", "documents", "recognition", "assistant", "goals", "analytics"];
const ks = ref<any>(null);

async function save() {
  const { knowledge_sources, ai_api_key_set, ...values } = form.value;
  try { const r: any = await HR.saveSettings(values, apiKey.value || undefined); apiKey.value = ""; ui.toast(r.changed.length ? `Saved ${r.changed.length} change(s). Reload to see module changes.` : "No changes"); reload(); }
  catch (e: any) { ui.toast(e.message, "error"); }
}
async function saveKs() {
  try { await HR.saveKnowledge(ks.value); ui.toast("Saved. Indexing runs in the background."); ks.value = null; reload(); }
  catch (e: any) { ui.toast(e.message, "error"); }
}
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Portal settings')" subtitle="Changes are recorded in the audit trail.">
      <button class="btn primary" @click="save">{{ t("Save") }}</button>
    </PageHeader>
    <SegmentTabs v-model="tab" :tabs="[{ value: 'modules', label: 'Modules' }, { value: 'rules', label: 'Rules' }, { value: 'ai', label: 'AI assistant' }, { value: 'audit', label: 'Audit trail' }]" />
    <SkeletonLoader v-if="!data" :lines="8" />
    <template v-else>
      <section v-if="tab === 'modules'" class="panel stack">
        <div class="form-grid">
          <div class="field"><label for="pt">Portal title</label><input id="pt" class="input" v-model="form.portal_title" /></div>
          <div class="field"><label for="bc">Brand colour</label><input id="bc" type="color" class="input" v-model="form.brand_color" style="padding: 4px; height: 42px" /></div>
          <div class="field"><label for="dl">Default language</label><select id="dl" class="select" v-model="form.default_language"><option value="en">English</option><option value="ar">العربية</option></select></div>
          <div class="field"><label for="se">Support email</label><input id="se" class="input" v-model="form.support_email" /></div>
        </div>
        <h2>Modules</h2>
        <div class="mods"><label v-for="m in MODULES" :key="m" class="check"><input type="checkbox" v-model="form[`enable_${m}`]" :true-value="1" :false-value="0" />{{ m }}</label></div>
      </section>
      <section v-else-if="tab === 'rules'" class="panel stack">
        <h2>Attendance</h2>
        <div class="row wrap"><label class="check"><input type="checkbox" v-model="form.require_geolocation" :true-value="1" :false-value="0" />Require location for check-in</label>
          <label class="check"><input type="checkbox" v-model="form.allow_checkin_without_shift" :true-value="1" :false-value="0" />Allow check-in without a shift</label></div>
        <div class="form-grid"><div class="field"><label for="cd">Minutes between punches</label><input id="cd" type="number" class="input" v-model.number="form.checkin_cooldown_minutes" /></div></div>
        <h2>Helpdesk & documents</h2>
        <div class="form-grid">
          <div class="field"><label for="rd">Reopen window (days)</label><input id="rd" type="number" class="input" v-model.number="form.allow_reopen_days" /></div>
          <div class="field"><label for="ac">Auto-close resolved after (days)</label><input id="ac" type="number" class="input" v-model.number="form.auto_close_resolved_days" /></div>
          <div class="field"><label for="dr">Document requests per day</label><input id="dr" type="number" class="input" v-model.number="form.document_rate_limit_per_day" /></div>
          <div class="field"><label for="ea">Expiry alert (days ahead)</label><input id="ea" type="number" class="input" v-model.number="form.document_expiry_alert_days" /></div>
        </div>
        <label class="check"><input type="checkbox" v-model="form.public_verification" :true-value="1" :false-value="0" />Allow third parties to verify letters by code</label>
        <h2>Recognition & analytics</h2>
        <div class="form-grid">
          <div class="field"><label for="pb">Monthly points per person</label><input id="pb" type="number" class="input" v-model.number="form.monthly_points_budget" /></div>
          <div class="field"><label for="mg">Smallest group shown in analytics</label><input id="mg" type="number" min="3" class="input" v-model.number="form.min_group_size" /></div>
        </div>
        <div class="row wrap"><label class="check"><input type="checkbox" v-model="form.recognition_requires_approval" :true-value="1" :false-value="0" />HR approves recognition before it's visible</label>
          <label class="check"><input type="checkbox" v-model="form.allow_public_recognition" :true-value="1" :false-value="0" />Allow company-wide recognition</label></div>
      </section>
      <section v-else-if="tab === 'ai'" class="stack">
        <div class="panel stack">
          <div class="form-grid">
            <div class="field"><label for="ap">Provider</label><select id="ap" class="select" v-model="form.ai_provider"><option>Disabled</option><option>Anthropic</option><option>OpenAI Compatible</option></select>
              <span class="hint">When disabled, the assistant answers from the policy library and simple self-service lookups only.</span></div>
            <div class="field"><label for="am">Model</label><input id="am" class="input" v-model="form.ai_model" /></div>
            <div class="field" v-if="form.ai_provider === 'OpenAI Compatible'"><label for="au">Base URL</label><input id="au" class="input" v-model="form.ai_base_url" /></div>
            <div class="field"><label for="ak">API key</label><input id="ak" type="password" class="input" v-model="apiKey" :placeholder="data.ai_api_key_set ? 'Stored — enter to replace' : 'Not set'" autocomplete="off" /><span class="hint">Kept server-side; never sent to browsers.</span></div>
            <div class="field"><label for="ar">Requests per person per hour</label><input id="ar" type="number" class="input" v-model.number="form.ai_max_requests_per_hour" /></div>
            <div class="field"><label for="at">Keep audit metadata for (days)</label><input id="at" type="number" class="input" v-model.number="form.ai_retention_days" /></div>
          </div>
          <label class="check"><input type="checkbox" v-model="form.ai_allow_salary_answers" :true-value="1" :false-value="0" />Let the assistant state the employee's own pay amounts</label>
          <div class="field"><label for="an">Notice shown under the assistant</label><textarea id="an" class="textarea" v-model="form.ai_system_notice" /></div>
          <p v-if="aiq" class="small muted">Last 30 days: {{ aiq.by_outcome.map((o: any) => `${o.outcome} ${o.n}`).join(", ") || "no usage" }}<template v-if="aiq.avg_latency_ms"> · average {{ Math.round(aiq.avg_latency_ms) }} ms</template></p>
        </div>
        <div class="panel">
          <header><h2>Knowledge sources</h2><button class="btn sm" @click="ks = { title: '', content: '', source_type: 'Policy', audience: 'All Employees', is_active: 1 }">Add source</button></header>
          <ul class="list"><li v-for="k in data.knowledge_sources" :key="k.name"><span class="grow"><span class="title">{{ k.title }}</span><br><span class="small muted">{{ k.source_type }} · {{ k.audience }} · {{ k.chunk_count || 0 }} passages · indexed {{ fmtDate(k.last_indexed_on) }}</span></span>
            <StatusBadge :tone="k.is_active ? 'ok' : 'muted'" :label="k.is_active ? 'Active' : 'Off'" /><a class="btn ghost sm" :href="`/app/ess-knowledge-source/${k.name}`">Edit</a></li></ul>
        </div>
      </section>
      <section v-else class="panel">
        <div class="table-wrap"><table class="data"><thead><tr><th>When</th><th>Event</th><th>User</th><th>Record</th><th>Details</th></tr></thead>
          <tbody><tr v-for="(a, i) in audit || []" :key="i"><td class="small">{{ fmtDate(a.creation) }}</td><td>{{ a.event_type }}</td><td class="small">{{ a.user }}</td><td class="small">{{ a.reference_doctype }} {{ a.reference_name }}</td><td class="small">{{ a.details }}</td></tr></tbody></table></div>
      </section>
    </template>

    <AccessibleDialog :open="!!ks" title="Knowledge source" wide @close="ks = null">
      <form v-if="ks" id="ksf" class="stack" @submit.prevent="saveKs">
        <div class="field"><label for="kt">Title</label><input id="kt" class="input" v-model="ks.title" required /></div>
        <div class="form-grid"><div class="field"><label for="ky">Type</label><select id="ky" class="select" v-model="ks.source_type"><option>Policy</option><option>FAQ</option><option>Handbook</option><option>Procedure</option></select></div>
          <div class="field"><label for="ka">Who can retrieve it</label><select id="ka" class="select" v-model="ks.audience"><option>All Employees</option><option>Managers</option><option>HR Only</option></select></div></div>
        <div class="field"><label for="kc">Content</label><textarea id="kc" class="textarea" rows="10" v-model="ks.content" /><span class="hint">Paste the approved policy text. Text is treated as reference material, never as instructions to the assistant.</span></div>
      </form>
      <template #footer><button class="btn" @click="ks = null">{{ t("Cancel") }}</button><button class="btn primary" form="ksf">{{ t("Save") }}</button></template>
    </AccessibleDialog>
  </div>
</template>

<style scoped>.mods { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 4px 12px; text-transform: capitalize; }</style>
