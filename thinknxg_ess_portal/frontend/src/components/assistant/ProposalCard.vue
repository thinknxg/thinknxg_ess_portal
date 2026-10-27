<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import type { Proposal } from "@/types";
import { Assistant } from "@/services/endpoints";
import { fmtDate, t } from "@/i18n";
import { invalidate } from "@/composables/useResource";

const props = defineProps<{ proposal: Proposal }>();
const state = ref<"draft" | "sending" | "confirmed" | "error">("draft");
const msg = ref("");
const ref_ = ref<string | null>(null);
const router = useRouter();

async function confirm() {
  state.value = "sending";
  try {
    const r = await Assistant.confirm(props.proposal.token);
    ref_.value = r.name || null;
    state.value = "confirmed";
    invalidate("leave"); invalidate("inbox");
  } catch (e: any) {
    state.value = "error";
    msg.value = e?.message || "Could not submit";
  }
}
function edit() {
  const p = props.proposal.payload;
  if (props.proposal.type === "leave_request") router.push({ path: "/leave/apply", query: { type: p.leave_type, from: p.from_date, to: p.to_date, reason: p.reason } });
  else router.push({ path: "/support/new", query: { subject: p.subject, category: p.category } });
}
</script>

<template>
  <div class="prop" :class="state">
    <p class="h">{{ proposal.type === "leave_request" ? "Leave request ready to submit" : "HR ticket ready to submit" }}</p>
    <dl v-if="proposal.type === 'leave_request'">
      <div><dt>{{ t("Leave type") }}</dt><dd>{{ proposal.payload.leave_type }}</dd></div>
      <div><dt>{{ t("Date") }}</dt><dd>{{ fmtDate(proposal.payload.from_date) }} – {{ fmtDate(proposal.payload.to_date) }}</dd></div>
      <div v-if="proposal.preview"><dt>{{ t("Days") }}</dt><dd class="num">{{ proposal.preview.days }}</dd></div>
      <div v-if="proposal.preview?.balance_after !== null && proposal.preview?.balance_after !== undefined"><dt>{{ t("Balance after") }}</dt><dd class="num">{{ proposal.preview.balance_after }}</dd></div>
    </dl>
    <dl v-else>
      <div><dt>{{ t("Category") }}</dt><dd>{{ proposal.payload.category }}</dd></div>
      <div><dt>{{ t("Subject") }}</dt><dd>{{ proposal.payload.subject }}</dd></div>
    </dl>
    <p v-if="proposal.preview && proposal.preview.sufficient === false" class="warn small">Your balance doesn't cover this request.</p>
    <div class="row" v-if="state === 'draft' || state === 'error'">
      <button class="btn primary sm" @click="confirm">{{ t("Confirm and submit") }}</button>
      <button class="btn sm" @click="edit">Edit first</button>
    </div>
    <p v-if="state === 'sending'" class="small muted">Submitting…</p>
    <p v-if="state === 'confirmed'" class="ok small">Submitted{{ ref_ ? ` as ${ref_}` : "" }}. You'll be notified when it's reviewed.</p>
    <p v-if="state === 'error'" class="err small">{{ msg }}</p>
  </div>
</template>

<style scoped>
.prop { border: 1px solid var(--line-strong); border-radius: 12px; padding: 14px; display: flex; flex-direction: column; gap: 10px; background: var(--surface); }
.prop.confirmed { border-color: var(--ok); }
.h { font-weight: 600; }
dl { margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; }
dt { font-size: var(--fs-xs); color: var(--ink-3); }
dd { margin: 0; font-weight: 500; }
.ok { color: var(--ok); } .err { color: var(--pom); } .warn { color: var(--saffron-ink); }
</style>
