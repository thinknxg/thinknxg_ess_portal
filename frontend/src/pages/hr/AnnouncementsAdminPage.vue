<script setup lang="ts">
import { ref } from "vue";
import { useResource } from "@/composables/useResource";
import { Announcements } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import AccessibleDialog from "@/components/ui/AccessibleDialog.vue";
import EmptyState from "@/components/ui/EmptyState.vue";

const ui = useUi();
const { data, reload } = useResource<any[]>(() => "ann:admin", () => Announcements.adminList());
const open = ref(false);
const blank = () => ({ title: "", body: "", category: "General", audience: "All Employees", company: "", department: "", branch: "", designation: "", publish_from: "", publish_until: "", is_pinned: 0, is_published: 0 });
const form = ref<any>(blank());
function edit(a?: any) { form.value = a ? { ...blank(), ...a } : blank(); open.value = true; }
async function save(publish: boolean) {
  try {
    const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const body = form.value.body.includes("<") ? form.value.body : esc(form.value.body).split(/\n{2,}/).map((p: string) => `<p>${p.replace(/\n/g, "<br>")}</p>`).join("");
    await Announcements.save({ ...form.value, body, is_published: publish ? 1 : 0 });
    ui.toast(publish ? "Announcement published" : "Saved as draft"); open.value = false; reload();
  } catch (e: any) { ui.toast(e.message, "error"); }
}
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Announcements')" subtitle="Targeted to everyone, a company, department, branch or designation.">
      <button class="btn primary" @click="edit()">New announcement</button>
    </PageHeader>
    <section class="panel">
      <ul class="list" v-if="data?.length">
        <li v-for="a in data" :key="a.name"><span class="grow"><span class="title">{{ a.title }}</span><br><span class="small muted">{{ a.category }} · {{ a.audience }} · read by {{ a.reads }}</span></span>
          <StatusBadge :tone="a.is_published ? 'ok' : 'muted'" :label="a.is_published ? 'Published' : 'Draft'" /><span class="small muted">{{ fmtDate(a.modified) }}</span>
          <button class="btn ghost sm" @click="edit(a)">Edit</button></li>
      </ul>
      <EmptyState v-else title="No announcements yet" icon="megaphone" />
    </section>
    <AccessibleDialog :open="open" title="Announcement" wide @close="open = false">
      <form class="stack" @submit.prevent>
        <div class="field"><label for="at">Title</label><input id="at" class="input" v-model="form.title" required /></div>
        <div class="field"><label for="ab">Message</label><textarea id="ab" class="textarea" rows="7" v-model="form.body" /></div>
        <div class="form-grid">
          <div class="field"><label for="ac">{{ t("Category") }}</label><select id="ac" class="select" v-model="form.category"><option v-for="c in ['General', 'HR', 'Event', 'Policy', 'Celebration', 'Urgent']" :key="c">{{ c }}</option></select></div>
          <div class="field"><label for="aa">Audience</label><select id="aa" class="select" v-model="form.audience"><option v-for="c in ['All Employees', 'Company', 'Department', 'Branch', 'Designation']" :key="c">{{ c }}</option></select></div>
          <div class="field" v-if="form.audience !== 'All Employees'"><label for="av">{{ form.audience }} name</label>
            <input id="av" class="input" v-model="form[form.audience.toLowerCase()]" /></div>
          <div class="field"><label for="pf">Show from</label><input id="pf" type="datetime-local" class="input" v-model="form.publish_from" /></div>
          <div class="field"><label for="pu">Show until</label><input id="pu" type="datetime-local" class="input" v-model="form.publish_until" /></div>
        </div>
        <label class="check"><input type="checkbox" v-model="form.is_pinned" :true-value="1" :false-value="0" />Pin to the top of the dashboard</label>
      </form>
      <template #footer><button class="btn" @click="save(false)">Save draft</button><button class="btn primary" @click="save(true)" :disabled="!form.title">Publish</button></template>
    </AccessibleDialog>
  </div>
</template>
