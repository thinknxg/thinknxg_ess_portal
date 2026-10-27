<script setup lang="ts">
import { nextTick, ref } from "vue";
import { Assistant } from "@/services/endpoints";
import { lang, t } from "@/i18n";
import { renderMarkdown } from "@/utils/markdown";
import type { AssistantReply } from "@/types";
import SourceCitation from "./SourceCitation.vue";
import FeedbackControl from "./FeedbackControl.vue";
import ProposalCard from "./ProposalCard.vue";
import EssIcon from "@/components/ui/EssIcon.vue";

const props = defineProps<{ suggestions?: string[] }>();
interface Turn { role: "user" | "assistant"; text: string; reply?: AssistantReply; error?: boolean }
const turns = ref<Turn[]>([]);
const draft = ref("");
const busy = ref(false);
const conv = ref<string | null>(null);
const scroller = ref<HTMLElement | null>(null);

async function scroll() { await nextTick(); scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: "smooth" }); }

async function send(text?: string) {
  const msg = (text ?? draft.value).trim();
  if (!msg || busy.value) return;
  draft.value = "";
  turns.value.push({ role: "user", text: msg });
  busy.value = true;
  scroll();
  try {
    const reply = await Assistant.ask(msg, conv.value, lang.value);
    conv.value = reply.conversation_id;
    turns.value.push({ role: "assistant", text: reply.answer, reply });
  } catch (e: any) {
    turns.value.push({ role: "assistant", text: e?.message || "The assistant is unavailable right now.", error: true });
  } finally {
    busy.value = false;
    scroll();
  }
}
function key(e: KeyboardEvent) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }
</script>

<template>
  <div class="chat">
    <div class="scroll" ref="scroller" aria-live="polite">
      <div v-if="!turns.length" class="intro">
        <span class="spark"><EssIcon name="spark" :size="26" /></span>
        <h2>Ask about policies, your leave, payslips or requests</h2>
        <p class="muted">Answers come from approved HR policies and your own records. The assistant can prepare a leave request or ticket, but you confirm it before anything is submitted.</p>
        <div class="sugs">
          <button v-for="s in props.suggestions || []" :key="s" class="btn sm" @click="send(s)">{{ s }}</button>
        </div>
      </div>
      <div v-for="(tn, i) in turns" :key="i" class="turn" :class="tn.role">
        <div v-if="tn.role === 'user'" class="u">{{ tn.text }}</div>
        <div v-else class="a" :class="{ error: tn.error }">
          <div class="md" v-html="renderMarkdown(tn.text)" />
          <SourceCitation v-if="tn.reply?.citations?.length" :citations="tn.reply.citations" />
          <ProposalCard v-if="tn.reply?.proposal" :proposal="tn.reply.proposal" />
          <div class="foot" v-if="tn.reply">
            <FeedbackControl :conversation="tn.reply.conversation_id" />
            <span v-if="tn.reply.outcome === 'Fallback'" class="muted small">Matched from the policy library</span>
          </div>
        </div>
      </div>
      <div v-if="busy" class="turn assistant"><div class="a typing" aria-label="Assistant is writing"><i /><i /><i /></div></div>
    </div>
    <form class="composer" @submit.prevent="send()">
      <label for="ask" class="sr-only">{{ t("Ask a question about HR policies or your records") }}</label>
      <textarea id="ask" v-model="draft" rows="1" :placeholder="t('Ask a question about HR policies or your records')" @keydown="key" maxlength="2000" />
      <button class="btn primary icon" :disabled="busy || !draft.trim()" aria-label="Send"><EssIcon name="send" /></button>
    </form>
  </div>
</template>

<style scoped>
.chat { display: flex; flex-direction: column; height: calc(100vh - var(--header) - 160px); min-height: 420px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--r-lg); overflow: hidden; }
.scroll { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.intro { max-width: 560px; margin: auto; text-align: center; display: flex; flex-direction: column; gap: 10px; align-items: center; }
.spark { width: 52px; height: 52px; border-radius: 16px; display: grid; place-items: center; background: var(--brand-soft); color: var(--brand); }
.sugs { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 8px; }
.turn { display: flex; }
.turn.user { justify-content: flex-end; }
.u { max-width: 78%; background: var(--brand); color: #fff; padding: 10px 14px; border-radius: 14px 14px 4px 14px; white-space: pre-wrap; }
[dir="rtl"] .u { border-radius: 14px 14px 14px 4px; }
.a { max-width: 86%; display: flex; flex-direction: column; gap: 10px; }
.a.error { color: var(--pom); }
.foot { display: flex; align-items: center; gap: 12px; }
.typing { flex-direction: row; gap: 4px; padding: 12px 0; }
.typing i { width: 7px; height: 7px; border-radius: 50%; background: var(--ink-3); animation: b 1s infinite; }
.typing i:nth-child(2) { animation-delay: .15s; } .typing i:nth-child(3) { animation-delay: .3s; }
@keyframes b { 50% { opacity: .3; transform: translateY(-3px); } }
.composer { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--line); }
.composer textarea { flex: 1; resize: none; min-height: 42px; max-height: 140px; padding: 10px 12px; border: 1px solid var(--line-strong); border-radius: 10px; background: var(--surface); }
@media (max-width: 640px) { .chat { height: calc(100vh - var(--header) - 170px); border-radius: 12px; } .a, .u { max-width: 100%; } }
</style>
