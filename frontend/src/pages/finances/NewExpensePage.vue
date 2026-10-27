<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useResource, invalidate } from "@/composables/useResource";
import { Expenses } from "@/services/endpoints";
import { fmtMoney, t } from "@/i18n";
import { isoToday } from "@/utils/format";
import { useUi } from "@/stores/ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import FileUploader from "@/components/ui/FileUploader.vue";

const router = useRouter();
const ui = useUi();
const { data } = useResource<any>(() => "expenses", () => Expenses.overview());
const lines = ref([{ expense_date: isoToday(), expense_type: "", description: "", amount: 0 }]);
const remark = ref("");
const files = ref<string[]>([]);
const busy = ref(false);
const err = ref("");
const total = computed(() => lines.value.reduce((a, l) => a + (Number(l.amount) || 0), 0));
const add = () => lines.value.push({ expense_date: isoToday(), expense_type: data.value?.types?.[0] || "", description: "", amount: 0 });

async function submit() {
  err.value = "";
  if (lines.value.some((l) => !l.expense_type || !(Number(l.amount) > 0))) { err.value = "Each line needs a type and an amount above zero."; return; }
  busy.value = true;
  try {
    const r = await Expenses.create({ expenses: lines.value, remark: remark.value, attachments: files.value });
    ui.toast(`Claim ${r.name} sent for approval`);
    invalidate("expenses"); invalidate("dashboard");
    router.push("/finances/expenses");
  } catch (e: any) { err.value = e.message; } finally { busy.value = false; }
}
</script>

<template>
  <div class="page">
    <PageHeader :title="t('New claim')" subtitle="Add each expense as a line. Receipts are stored privately with the claim." back="/finances/expenses" />
    <form class="panel stack" @submit.prevent="submit">
      <fieldset v-for="(l, i) in lines" :key="i" class="line">
        <legend class="sr-only">Expense line {{ i + 1 }}</legend>
        <div class="field"><label :for="`d${i}`">{{ t("Date") }}</label><input :id="`d${i}`" type="date" class="input" v-model="l.expense_date" :max="isoToday()" required /></div>
        <div class="field"><label :for="`t${i}`">Type</label><select :id="`t${i}`" class="select" v-model="l.expense_type" required>
          <option value="" disabled>Choose</option><option v-for="ty in data?.types || []" :key="ty" :value="ty">{{ ty }}</option></select></div>
        <div class="field wide"><label :for="`s${i}`">{{ t("Description") }}</label><input :id="`s${i}`" class="input" v-model="l.description" placeholder="Taxi to client office" /></div>
        <div class="field"><label :for="`a${i}`">{{ t("Amount") }} ({{ data?.currency }})</label><input :id="`a${i}`" type="number" step="0.001" min="0" class="input num" v-model.number="l.amount" required /></div>
        <button type="button" class="btn ghost sm rm" v-if="lines.length > 1" @click="lines.splice(i, 1)" :aria-label="`Remove line ${i + 1}`">Remove</button>
      </fieldset>
      <div><button type="button" class="btn sm" @click="add">{{ t("Add line") }}</button></div>
      <div class="field"><label>{{ t("Receipts") }}</label><FileUploader v-model="files" :max="10" capture label="Take a photo or attach receipts" /></div>
      <div class="field"><label for="rm">Note for your approver</label><textarea id="rm" class="textarea" v-model="remark" maxlength="1000" /></div>
      <div class="spread">
        <p class="tot">{{ t("Total") }} <span class="num">{{ fmtMoney(total, data?.currency || "OMR") }}</span></p>
        <button class="btn primary" :disabled="busy">{{ busy ? "Sending…" : "Send for approval" }}</button>
      </div>
      <p v-if="err" class="err" role="alert">{{ err }}</p>
    </form>
  </div>
</template>

<style scoped>
.line { border: 0; padding: 0 0 16px; margin: 0; border-bottom: 1px solid var(--line); display: grid; grid-template-columns: 150px 1fr 2fr 150px auto; gap: 12px; align-items: end; }
.tot { font-size: var(--fs-lg); } .tot .num { font-weight: 600; margin-inline-start: 8px; }
.err { color: var(--pom); }
@media (max-width: 760px) { .line { grid-template-columns: 1fr 1fr; } .wide { grid-column: 1 / -1; } }
</style>
