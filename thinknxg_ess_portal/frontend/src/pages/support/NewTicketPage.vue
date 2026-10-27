<script setup lang="ts">
import { ref, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useResource } from "@/composables/useResource";
import { useSubmit } from "@/composables/useSubmit";
import { Helpdesk } from "@/services/endpoints";
import { t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import FileUploader from "@/components/ui/FileUploader.vue";

const route = useRoute();
const router = useRouter();
const { data: cats } = useResource<any[]>(() => "ticket:cats", () => Helpdesk.categories(), { staleMs: 600_000 });
const form = ref({ category: (route.query.category as string) || "", subject: (route.query.subject as string) || "", description: "", priority: "Medium" });
const files = ref<string[]>([]);
const { state, error, submit } = useSubmit();
const sla = computed(() => cats.value?.find((c) => c.name === form.value.category));
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
async function send() {
  const r = await submit("helpdesk.create_ticket", { ...form.value, description: esc(form.value.description).replace(/\n/g, "<br>"), attachments: files.value },
    `HR ticket: ${form.value.subject}`, ["tickets", "dashboard"]);
  if (r?.name) router.push(`/support/${r.name}`);
  else if (state.value === "queued") router.push("/support");
}
</script>

<template>
  <div class="page">
    <PageHeader :title="t('New ticket')" back="/support" />
    <form class="panel stack" @submit.prevent="send" style="max-width: 760px">
      <fieldset class="cats"><legend>{{ t("Category") }}</legend>
        <label v-for="c in cats || []" :key="c.name" class="cat" :class="{ on: form.category === c.name }"><input type="radio" class="sr-only" v-model="form.category" :value="c.name" required />
          <span class="ico">{{ c.icon }}</span><span>{{ c.name }}</span></label></fieldset>
      <p v-if="sla" class="small muted">First reply within {{ sla.first_response_hours }} working hours; target resolution {{ sla.resolution_hours }} hours.</p>
      <div class="field"><label for="sb">{{ t("Subject") }}</label><input id="sb" class="input" v-model="form.subject" maxlength="140" required /></div>
      <div class="field"><label for="ds">{{ t("Describe your request") }}</label><textarea id="ds" class="textarea" rows="6" v-model="form.description" required /></div>
      <div class="field"><label for="pr">{{ t("Priority") }}</label><select id="pr" class="select" v-model="form.priority" style="max-width: 220px">
        <option>Low</option><option>Medium</option><option>High</option><option>Urgent</option></select></div>
      <div class="field"><label>Attachments</label><FileUploader v-model="files" /></div>
      <p v-if="error" class="err" role="alert">{{ error }}</p>
      <div><button class="btn primary" :disabled="state === 'submitting' || !form.category">Send to HR</button></div>
    </form>
  </div>
</template>

<style scoped>
.cats { border: 0; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 8px; }
.cats legend { font-size: var(--fs-sm); font-weight: 500; color: var(--ink-2); margin-bottom: 8px; }
.cat { display: flex; align-items: center; gap: 10px; padding: 12px; border: 1px solid var(--line); border-radius: 10px; cursor: pointer; }
.cat.on { border-color: var(--brand); background: var(--brand-soft); }
.cat:focus-within { outline: 2px solid var(--focus); }
.ico { font-size: 20px; }
.err { color: var(--pom); }
</style>
