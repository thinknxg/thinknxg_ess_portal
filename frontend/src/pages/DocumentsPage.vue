<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useResource, invalidate } from "@/composables/useResource";
import { Documents, Policies } from "@/services/endpoints";
import { downloadUrl } from "@/services/api";
import { fmtDate, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import AccessibleDialog from "@/components/ui/AccessibleDialog.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";

const route = useRoute();
const ui = useUi();
const tab = ref((route.query.tab as string) || "letters");
const { data, loading, reload } = useResource<any>(() => "documents", () => Documents.overview(), { staleMs: 10_000 });
const reqOpen = ref(!!route.query.request);
const chosen = ref<any>(null);
const form = ref({ purpose: "", addressed_to: "", language: "en" });
const busy = ref(false);
const err = ref("");
const policy = ref<any>(null);

const policiesPending = computed(() => (data.value?.policies || []).filter((p: any) => p.status === "Pending" || p.status === "Overdue").length);
function pick(tpl: any) { chosen.value = tpl; form.value = { purpose: "", addressed_to: "", language: "en" }; err.value = ""; reqOpen.value = true; }
async function request() {
  busy.value = true; err.value = "";
  try {
    const r = await Documents.request({ template: chosen.value.name, ...form.value });
    ui.toast(r.status === "Pending Approval" ? "Request sent to HR for approval" : "Generating your document. We'll notify you when it's ready.");
    reqOpen.value = false; invalidate("documents"); reload();
  } catch (e: any) { err.value = e.message; } finally { busy.value = false; }
}
async function cancel(name: string) { await Documents.cancel(name); invalidate("documents"); reload(); }
async function openPolicy(name: string) { policy.value = await Policies.get(name); }
async function ack() { await Policies.acknowledge(policy.value.name); ui.toast(t("Acknowledged")); policy.value = null; invalidate("documents"); invalidate("inbox"); reload(); }
watch(() => route.query.policy, (p) => p && openPolicy(String(p)), { immediate: true });
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Documents')" subtitle="Request HR letters and read company policies. Files are private to you." />
    <SegmentTabs v-model="tab" :tabs="[{ value: 'letters', label: 'Letters & certificates' }, { value: 'policies', label: t('Policies'), count: policiesPending }]" />
    <SkeletonLoader v-if="loading && !data" :lines="6" />
    <template v-else-if="data && tab === 'letters'">
      <section class="panel">
        <header><h2>{{ t("Request document") }}</h2></header>
        <ul class="list">
          <li v-for="tpl in data.templates" :key="tpl.name">
            <span class="grow"><span class="title">{{ tpl.name }}</span>
              <br><span class="small muted">{{ tpl.description || tpl.document_type }}<template v-if="tpl.requires_approval"> · Needs HR approval</template></span>
              <br v-if="tpl.blocked_reasons.length"><span v-if="tpl.blocked_reasons.length" class="small warn">{{ tpl.blocked_reasons.join(" ") }}</span></span>
            <button class="btn sm" :disabled="tpl.blocked_reasons.length > 0" @click="pick(tpl)">Request</button>
          </li>
        </ul>
      </section>
      <section class="panel">
        <header><h2>My requests</h2></header>
        <ul class="list" v-if="data.requests.length">
          <li v-for="r in data.requests" :key="r.name">
            <span class="grow"><span class="title">{{ r.template }}</span><br><span class="small muted">{{ fmtDate(r.creation) }}<template v-if="r.purpose"> · {{ r.purpose }}</template></span>
              <br v-if="r.rejection_reason"><span v-if="r.rejection_reason" class="small bad">{{ r.rejection_reason }}</span></span>
            <StatusBadge :status="r.status" />
            <a v-if="r.status === 'Generated'" class="btn sm primary" :href="downloadUrl('documents.download', { name: r.name })">{{ t("Download") }}</a>
            <button v-else-if="['Requested', 'Pending Approval'].includes(r.status)" class="btn ghost sm" @click="cancel(r.name)">{{ t("Cancel") }}</button>
          </li>
        </ul>
        <EmptyState v-else title="No documents requested yet" icon="file" />
      </section>
    </template>
    <section class="panel" v-else-if="data && tab === 'policies'">
      <ul class="list" v-if="data.policies.length">
        <li v-for="p in data.policies" :key="p.name">
          <span class="grow"><span class="title">{{ p.policy_title }}</span><br><span class="small muted">v{{ p.version }} · effective {{ fmtDate(p.effective_date) }}<template v-if="p.due_date"> · acknowledge by {{ fmtDate(p.due_date) }}</template></span></span>
          <StatusBadge :status="p.status === 'Info' ? '' : p.status" v-if="p.status !== 'Info'" />
          <button class="btn sm" @click="openPolicy(p.name)">Read</button>
        </li>
      </ul>
      <EmptyState v-else title="No policies published" icon="shield" />
    </section>

    <AccessibleDialog :open="reqOpen && !!chosen" :title="chosen?.name || ''" @close="reqOpen = false">
      <form id="docreq" class="stack" @submit.prevent="request">
        <div class="field"><label for="pp">{{ t("Purpose") }}<span v-if="chosen?.requires_purpose"> *</span></label>
          <input id="pp" class="input" v-model="form.purpose" :required="!!chosen?.requires_purpose" placeholder="Bank account opening" /></div>
        <div class="field"><label for="ad">{{ t("Addressed to") }}<span v-if="chosen?.addressee_required"> *</span></label>
          <input id="ad" class="input" v-model="form.addressed_to" :required="!!chosen?.addressee_required" placeholder="Bank Muscat, Ruwi branch" /></div>
        <div class="field"><label for="lg">{{ t("Language") }}</label><select id="lg" class="select" v-model="form.language"><option value="en">English</option><option value="ar">العربية</option></select></div>
        <p class="small muted">The letter is generated from an HR-approved template with a verification code.</p>
        <p v-if="err" class="small bad" role="alert">{{ err }}</p>
      </form>
      <template #footer><button class="btn" @click="reqOpen = false">{{ t("Cancel") }}</button><button class="btn primary" form="docreq" :disabled="busy">{{ t("Request document") }}</button></template>
    </AccessibleDialog>

    <AccessibleDialog :open="!!policy" :title="policy?.policy_title || ''" wide @close="policy = null">
      <div v-if="policy" class="stack">
        <p class="muted small">Version {{ policy.version }} · effective {{ fmtDate(policy.effective_date) }}</p>
        <div class="policy" v-html="policy.content" />
        <a v-if="policy.attachment" :href="policy.attachment" target="_blank" rel="noopener">Open the full policy document</a>
      </div>
      <template #footer v-if="policy?.requires_acknowledgement">
        <span v-if="policy.acknowledged" class="ok small">{{ t("Acknowledged") }}</span>
        <button v-else class="btn primary" @click="ack">I have read and understood this policy</button>
      </template>
    </AccessibleDialog>
  </div>
</template>

<style scoped>
.warn { color: var(--saffron-ink); } .bad { color: var(--pom); } .ok { color: var(--ok); }
.policy { max-width: 72ch; line-height: 1.65; }
</style>
