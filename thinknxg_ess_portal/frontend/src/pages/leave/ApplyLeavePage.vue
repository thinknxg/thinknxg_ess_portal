<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useLeaveBalance } from "@/composables/hr";
import { useSubmit } from "@/composables/useSubmit";
import { Leave } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import { isoToday } from "@/utils/format";
import PageHeader from "@/components/ui/PageHeader.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";

const route = useRoute();
const router = useRouter();
const { data } = useLeaveBalance();
const form = ref({
  leave_type: (route.query.type as string) || "", from_date: (route.query.from as string) || isoToday(),
  to_date: (route.query.to as string) || isoToday(), half_day: 0, half_day_date: "", reason: (route.query.reason as string) || "",
});
const preview = ref<any>(null);
const previewErr = ref("");
const { state, error, submit, result } = useSubmit();
let seq = 0;

watch(() => data.value?.types, (types) => { if (types?.length && !form.value.leave_type) form.value.leave_type = types[0]; }, { immediate: true });
watch(() => [form.value.leave_type, form.value.from_date, form.value.to_date, form.value.half_day, form.value.half_day_date], async () => {
  if (!form.value.leave_type || !form.value.from_date || !form.value.to_date) return;
  if (form.value.to_date < form.value.from_date) form.value.to_date = form.value.from_date;
  const my = ++seq;
  previewErr.value = "";
  try {
    const p = await Leave.preview({ ...form.value, half_day_date: form.value.half_day ? form.value.half_day_date || form.value.from_date : undefined });
    if (my === seq) preview.value = p;
  } catch (e: any) { if (my === seq) { preview.value = null; previewErr.value = e.message; } }
}, { immediate: true });

const blocked = computed(() => !preview.value || preview.value.overlaps?.length || (!preview.value.sufficient));
async function send() {
  const r = await submit("leave.create_request", { ...form.value, half_day_date: form.value.half_day ? form.value.half_day_date || form.value.from_date : undefined },
    `Leave: ${form.value.leave_type} ${form.value.from_date}`, ["leave", "dashboard", "inbox"]);
  if (r) setTimeout(() => router.push("/leave"), 1600);
}
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Apply for leave')" back="/leave" />
    <div class="cols">
      <form class="panel stack" @submit.prevent="send" novalidate>
        <div class="field"><label for="lt">{{ t("Leave type") }}</label>
          <select id="lt" class="select" v-model="form.leave_type" required>
            <option v-for="lt in data?.types || []" :key="lt" :value="lt">{{ lt }}</option></select></div>
        <div class="form-grid">
          <div class="field"><label for="fd">{{ t("From") }}</label><input id="fd" type="date" class="input" v-model="form.from_date" required /></div>
          <div class="field"><label for="td">{{ t("To") }}</label><input id="td" type="date" class="input" v-model="form.to_date" :min="form.from_date" required /></div>
        </div>
        <label class="check"><input type="checkbox" :checked="!!form.half_day" @change="form.half_day = ($event.target as HTMLInputElement).checked ? 1 : 0" />{{ t("Half day") }}</label>
        <div class="field" v-if="form.half_day && form.from_date !== form.to_date"><label for="hd">Half day on</label>
          <input id="hd" type="date" class="input" v-model="form.half_day_date" :min="form.from_date" :max="form.to_date" /></div>
        <div class="field"><label for="rs">{{ t("Reason") }}</label><textarea id="rs" class="textarea" v-model="form.reason" maxlength="1000" placeholder="Optional, visible to your approver" /></div>
        <p v-if="error" class="err" role="alert">{{ error }}</p>
        <div class="row">
          <button class="btn primary" :disabled="blocked || state === 'submitting' || state === 'confirmed'">{{ state === "submitting" ? "Sending…" : "Send for approval" }}</button>
          <StatusBadge v-if="state === 'queued'" status="Queued" :label="t('Queued')" />
          <StatusBadge v-if="state === 'confirmed'" status="Confirmed" :label="`${t('Submitted')} · ${result?.name || ''}`" />
        </div>
      </form>

      <aside class="panel stack" aria-live="polite">
        <h2>Summary</h2>
        <p v-if="previewErr" class="err">{{ previewErr }}</p>
        <template v-else-if="preview">
          <dl class="sum">
            <div><dt>{{ t("Days") }}</dt><dd class="num">{{ preview.days }}</dd></div>
            <div v-if="preview.balance !== null"><dt>Balance now</dt><dd class="num">{{ preview.balance }}</dd></div>
            <div v-if="preview.balance_after !== null"><dt>{{ t("Balance after") }}</dt><dd class="num" :class="{ neg: preview.balance_after < 0 }">{{ preview.balance_after }}</dd></div>
          </dl>
          <p v-if="preview.is_lwp" class="small warn">This is leave without pay; it will reduce your payable days.</p>
          <p v-if="!preview.sufficient" class="small err">Your balance doesn't cover this request.</p>
          <div v-if="preview.overlaps?.length" class="small err">Overlaps with {{ preview.overlaps.map((o: any) => `${o.leave_type} (${fmtDate(o.from_date)})`).join(", ") }}.</div>
          <div v-if="preview.holidays?.length" class="small muted">Includes {{ preview.holidays.length }} holiday/weekly off day(s), counted per your leave policy.</div>
          <p class="small muted" v-if="preview.approver_name">Approver: {{ preview.approver_name }}</p>
          <p class="small muted">Days and balances are calculated by thinkNXG HR when you change the dates.</p>
        </template>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.sum { margin: 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
dt { font-size: var(--fs-xs); color: var(--ink-3); }
dd { margin: 0; font-size: var(--fs-xl); font-weight: 600; }
.neg { color: var(--pom); }
.err { color: var(--pom); } .warn { color: var(--saffron-ink); }
</style>
