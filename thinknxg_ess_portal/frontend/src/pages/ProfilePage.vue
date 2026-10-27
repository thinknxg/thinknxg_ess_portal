<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { useResource, invalidate } from "@/composables/useResource";
import { Profile } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import Avatar from "@/components/ui/Avatar.vue";
import AccessibleDialog from "@/components/ui/AccessibleDialog.vue";
import FileUploader from "@/components/ui/FileUploader.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import EmptyState from "@/components/ui/EmptyState.vue";

const route = useRoute();
const ui = useUi();
const tab = ref((route.query.tab as string) || "details");
const { data, loading, reload } = useResource<any>(() => "profile", () => Profile.get());
const p = computed(() => data.value?.profile);
const editOpen = ref(false);
const changes = ref<Record<string, string>>({});
const reason = ref("");
const proof = ref<string[]>([]);
const docOpen = ref(false);
const doc = ref<any>({ document_type: "Passport" });
const docFiles = ref<string[]>([]);
const pending = computed(() => data.value?.change_requests?.some((r: any) => r.status === "Pending"));

function startEdit() { changes.value = {}; reason.value = ""; proof.value = []; editOpen.value = true; }
async function sendChange() {
  const diff = Object.fromEntries(Object.entries(changes.value).filter(([, v]) => v !== undefined && v !== ""));
  try {
    await Profile.requestChange({ changes: diff, reason: reason.value, attachment: proof.value[0] });
    ui.toast("Change request sent to HR"); editOpen.value = false; invalidate("profile"); reload();
  } catch (e: any) { ui.toast(e.message, "error"); }
}
function editDoc(d?: any) { doc.value = d ? { ...d } : { document_type: "Passport" }; docFiles.value = []; docOpen.value = true; }
async function saveDoc() {
  try {
    await Profile.saveDocument({ ...doc.value, attachment: docFiles.value[0], name: doc.value.name });
    ui.toast("Document saved. HR will verify it."); docOpen.value = false; invalidate("profile"); reload();
  } catch (e: any) { ui.toast(e.message, "error"); }
}
const FIELDS = [["designation", "Designation"], ["department", "Department"], ["branch", "Branch"], ["reports_to_name", "Reports to"],
  ["date_of_joining", "Joined"], ["employment_type", "Employment type"], ["company_email", "Work email"], ["nationality", "Nationality"]];
</script>

<template>
  <div class="page">
    <SkeletonLoader v-if="loading && !data" :lines="8" />
    <template v-if="p">
      <section class="hero">
        <Avatar :name="p.employee_name" :image="p.image" :size="72" />
        <div class="grow"><h1>{{ p.employee_name }}</h1><p class="muted">{{ p.designation }} · {{ p.name }}</p></div>
        <button class="btn" @click="startEdit" :disabled="pending">{{ pending ? "Change pending review" : t("Request a change") }}</button>
      </section>
      <SegmentTabs v-model="tab" :tabs="[{ value: 'details', label: t('Personal details') }, { value: 'documents', label: t('My documents'), count: data.documents.length }, { value: 'badges', label: t('Badges'), count: data.badges.length }]" />
      <div v-if="tab === 'details'" class="cols">
        <section class="panel">
          <header><h2>Employment</h2></header>
          <dl class="kv"><div v-for="[k, l] in FIELDS" :key="k"><dt>{{ l }}</dt><dd>{{ k === "date_of_joining" ? fmtDate(p[k]) : p[k] || "—" }}</dd></div></dl>
          <header style="margin-top: 20px"><h2>Contact & personal</h2></header>
          <dl class="kv"><div v-for="f in data.editable" :key="f.field"><dt>{{ f.label }}</dt><dd>{{ f.value || "—" }}</dd></div></dl>
        </section>
        <section class="panel">
          <header><h2>Change requests</h2></header>
          <ul class="list" v-if="data.change_requests.length">
            <li v-for="r in data.change_requests" :key="r.name"><span class="grow small">{{ fmtDate(r.creation) }}<br><span class="muted" v-if="r.review_comment">{{ r.review_comment }}</span></span><StatusBadge :status="r.status" /></li>
          </ul>
          <p v-else class="muted small">Changes to your details are reviewed by HR before they apply. Bank details always need HR approval.</p>
        </section>
      </div>
      <section v-else-if="tab === 'documents'" class="panel">
        <header><h2>{{ t("My documents") }}</h2><button class="btn sm primary" @click="editDoc()">Add document</button></header>
        <ul class="list" v-if="data.documents.length">
          <li v-for="d in data.documents" :key="d.name">
            <span class="grow"><span class="title">{{ d.document_type }}</span><br><span class="small muted">{{ d.document_number || "—" }} · expires {{ fmtDate(d.expiry_date) }}</span></span>
            <StatusBadge :status="d.verified ? 'Verified' : 'Pending'" :tone="d.verified ? 'ok' : 'warn'" :label="d.verified ? 'Verified' : 'Awaiting HR check'" />
            <button class="btn ghost sm" @click="editDoc(d)">Renew</button>
          </li>
        </ul>
        <EmptyState v-else title="No documents on file" text="Add your passport, resident card and other IDs so HR can remind you before they expire." icon="file" />
      </section>
      <section v-else class="panel">
        <div class="badges" v-if="data.badges.length">
          <div v-for="b in data.badges" :key="b.badge" class="badge-tile" :style="{ '--c': b.color }"><span class="ico">{{ b.icon }}</span><strong>{{ b.badge }}</strong><span class="small muted">{{ fmtDate(b.awarded_on) }}</span></div>
        </div>
        <EmptyState v-else title="No badges yet" text="Badges come from milestones like work anniversaries, learning and recognition." icon="star" />
      </section>
    </template>

    <AccessibleDialog :open="editOpen" :title="t('Request a change')" wide @close="editOpen = false">
      <form id="pchg" class="stack" @submit.prevent="sendChange">
        <p class="small muted">Fill in only what changed. HR reviews the request before your record is updated.</p>
        <div class="form-grid">
          <div v-for="f in data?.editable || []" :key="f.field" class="field">
            <label :for="`f-${f.field}`">{{ f.label }}<span v-if="f.sensitive" class="muted small"> (HR approval)</span></label>
            <select v-if="f.fieldtype === 'Select'" :id="`f-${f.field}`" class="select" v-model="changes[f.field]">
              <option value="">No change</option><option v-for="o in (f.options || '').split('\n').filter(Boolean)" :key="o" :value="o">{{ o }}</option></select>
            <textarea v-else-if="f.fieldtype.includes('Text')" :id="`f-${f.field}`" class="textarea" v-model="changes[f.field]" :placeholder="f.sensitive ? '' : f.value" />
            <input v-else :id="`f-${f.field}`" class="input" v-model="changes[f.field]" :placeholder="f.sensitive ? 'Enter new value' : f.value" autocomplete="off" />
          </div>
        </div>
        <div class="field"><label for="prs">{{ t("Reason") }}</label><input id="prs" class="input" v-model="reason" /></div>
        <div class="field"><label>Supporting document</label><FileUploader v-model="proof" :max="1" label="Attach proof (optional)" /></div>
      </form>
      <template #footer><button class="btn" @click="editOpen = false">{{ t("Cancel") }}</button><button class="btn primary" form="pchg">Send to HR</button></template>
    </AccessibleDialog>

    <AccessibleDialog :open="docOpen" :title="doc.name ? 'Renew document' : 'Add document'" @close="docOpen = false">
      <form id="edoc" class="stack" @submit.prevent="saveDoc">
        <div class="field"><label for="dt">Type</label><select id="dt" class="select" v-model="doc.document_type">
          <option v-for="o in ['Passport', 'Resident Card', 'Visa', 'Labour Card', 'Driving Licence', 'Medical Fitness', 'Professional License', 'Other']" :key="o">{{ o }}</option></select></div>
        <div class="field"><label for="dn">Number</label><input id="dn" class="input" v-model="doc.document_number" autocomplete="off" /></div>
        <div class="form-grid"><div class="field"><label for="di">Issued</label><input id="di" type="date" class="input" v-model="doc.issue_date" /></div>
          <div class="field"><label for="de">Expires</label><input id="de" type="date" class="input" v-model="doc.expiry_date" /></div></div>
        <div class="field"><label>Scan</label><FileUploader v-model="docFiles" :max="1" capture label="Photo or PDF of the document" /></div>
      </form>
      <template #footer><button class="btn" @click="docOpen = false">{{ t("Cancel") }}</button><button class="btn primary" form="edoc">{{ t("Save") }}</button></template>
    </AccessibleDialog>
  </div>
</template>

<style scoped>
.hero { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.kv { margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px 20px; }
dt { font-size: var(--fs-xs); color: var(--ink-3); } dd { margin: 2px 0 0; overflow-wrap: anywhere; }
.badges { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
.badge-tile { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 16px 10px; border-radius: 14px; border: 1px solid var(--line); text-align: center; background: color-mix(in srgb, var(--c) 8%, var(--surface)); }
.ico { font-size: 32px; }
</style>
