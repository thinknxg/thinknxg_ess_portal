<script setup lang="ts">
import { ref } from "vue";
import { useRoute } from "vue-router";
import { useResource, invalidate } from "@/composables/useResource";
import { Attendance } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import { isoToday } from "@/utils/format";
import PageHeader from "@/components/ui/PageHeader.vue";
import AccessibleDialog from "@/components/ui/AccessibleDialog.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";

const route = useRoute();
const ui = useUi();
const { data, loading, reload } = useResource<any[]>(() => "attendance:corrections", () => Attendance.corrections());
const open = ref(!!route.query.new);
const d0 = (route.query.date as string) || isoToday();
const form = ref({ from_date: d0, to_date: d0, reason: "On Duty", explanation: "", half_day: 0 });
const busy = ref(false);
const err = ref("");

async function submit() {
  busy.value = true; err.value = "";
  try {
    await Attendance.requestCorrection(form.value);
    ui.toast("Correction request sent to your manager");
    open.value = false;
    invalidate("attendance"); reload();
  } catch (e: any) { err.value = e.message; } finally { busy.value = false; }
}
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Corrections')" subtitle="Ask your manager to correct days you worked on duty, from home, or forgot to punch." back="/attendance">
      <button class="btn primary" @click="open = true">{{ t("Request correction") }}</button>
    </PageHeader>
    <section class="panel">
      <SkeletonLoader v-if="loading && !data" />
      <ul class="list" v-else-if="data?.length">
        <li v-for="r in data" :key="r.name">
          <span class="grow"><span class="title">{{ fmtDate(r.from_date) }}<template v-if="r.to_date !== r.from_date"> – {{ fmtDate(r.to_date) }}</template></span>
            <br><span class="small muted">{{ r.reason }} · {{ r.explanation }}</span>
            <br v-if="r.ess_review_comment"><span v-if="r.ess_review_comment" class="small bad">{{ r.ess_review_comment }}</span></span>
          <StatusBadge :status="r.status" />
        </li>
      </ul>
      <EmptyState v-else title="No corrections requested" icon="clock" />
    </section>

    <AccessibleDialog :open="open" :title="t('Request correction')" @close="open = false">
      <form class="stack" @submit.prevent="submit" id="corr">
        <div class="form-grid">
          <div class="field"><label for="cf">{{ t("From") }}</label><input id="cf" type="date" class="input" v-model="form.from_date" required /></div>
          <div class="field"><label for="ct">{{ t("To") }}</label><input id="ct" type="date" class="input" v-model="form.to_date" :min="form.from_date" required /></div>
        </div>
        <div class="field"><label for="cr">{{ t("Reason") }}</label>
          <select id="cr" class="select" v-model="form.reason"><option value="On Duty">{{ t("On duty") }}</option><option value="Work From Home">{{ t("Work from home") }}</option></select></div>
        <div class="field"><label for="ce">{{ t("Explanation") }} *</label><textarea id="ce" class="textarea" v-model="form.explanation" required placeholder="For example: client site visit, badge reader was down" /></div>
        <p v-if="err" class="small bad" role="alert">{{ err }}</p>
      </form>
      <template #footer>
        <button class="btn" @click="open = false">{{ t("Cancel") }}</button>
        <button class="btn primary" form="corr" :disabled="busy">Send for approval</button>
      </template>
    </AccessibleDialog>
  </div>
</template>

<style scoped>.bad { color: var(--pom); }</style>
