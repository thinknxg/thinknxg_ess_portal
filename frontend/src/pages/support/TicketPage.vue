<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { useResource, invalidate } from "@/composables/useResource";
import { Helpdesk } from "@/services/endpoints";
import { fmtDate, fmtTime, t } from "@/i18n";
import { useUi } from "@/stores/ui";
import PageHeader from "@/components/ui/PageHeader.vue";
import StatusBadge from "@/components/ui/StatusBadge.vue";
import TicketConversation from "@/components/support/TicketConversation.vue";
import FileUploader from "@/components/ui/FileUploader.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";
import ErrorState from "@/components/ui/ErrorState.vue";

const route = useRoute();
const ui = useUi();
const name = String(route.params.name);
const agentView = route.path.startsWith("/hr/");
const { data: tk, loading, error, reload } = useResource<any>(() => `ticket:${name}`, () => Helpdesk.ticket(name), { staleMs: 5_000 });
const reply = ref("");
const internal = ref(false);
const files = ref<string[]>([]);
const busy = ref(false);
const rating = ref(0);
const { data: canned } = agentView ? useResource<any[]>(() => "canned", () => Helpdesk.canned()) : { data: ref([]) };
const { data: agents } = agentView ? useResource<any[]>(() => "agents", () => Helpdesk.agents()) : { data: ref([]) };
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>");
const dueText = computed(() => tk.value?.resolution_due ? `${fmtDate(tk.value.resolution_due)} ${fmtTime(tk.value.resolution_due)}` : "—");

async function send() {
  if (!reply.value.trim()) return;
  busy.value = true;
  try {
    await Helpdesk.reply(name, esc(reply.value), internal.value ? 1 : 0, files.value);
    reply.value = ""; files.value = []; invalidate(`ticket:${name}`); await reload();
  } catch (e: any) { ui.toast(e.message, "error"); } finally { busy.value = false; }
}
async function act(fn: () => Promise<any>, msg: string) {
  try { await fn(); ui.toast(msg); invalidate("ticket"); invalidate("tickets"); await reload(); } catch (e: any) { ui.toast(e.message, "error"); }
}
function useCanned(e: Event) { const c = canned.value?.find((x: any) => x.name === (e.target as HTMLSelectElement).value); if (c) reply.value = c.response.replace(/<[^>]+>/g, ""); }
</script>

<template>
  <div class="page">
    <ErrorState :error="error" @retry="reload" />
    <SkeletonLoader v-if="loading && !tk" :lines="8" />
    <template v-if="tk">
      <PageHeader :title="tk.subject" :subtitle="`${tk.name} · ${tk.category}`" :back="agentView ? '/hr/tickets' : '/support'">
        <StatusBadge :status="tk.status" />
      </PageHeader>
      <div class="cols">
        <section class="panel stack">
          <TicketConversation :description="tk.description" :raised-by="tk.employee_name" :created="tk.creation" :comments="tk.comments" />
          <form v-if="tk.status !== 'Closed' || tk.is_staff" class="composer stack" @submit.prevent="send">
            <div class="row" v-if="tk.is_staff">
              <label class="check"><input type="checkbox" v-model="internal" />{{ t("Internal note") }}</label>
              <select class="select grow" v-if="canned?.length" @change="useCanned" aria-label="Insert saved reply"><option value="">Insert a saved reply…</option><option v-for="c in canned" :key="c.name" :value="c.name">{{ c.title }}</option></select>
            </div>
            <label for="rp" class="sr-only">{{ t("Reply") }}</label>
            <textarea id="rp" class="textarea" :class="{ int: internal }" v-model="reply" :placeholder="internal ? 'Only HR can see this note' : 'Write a reply'" />
            <FileUploader v-model="files" />
            <div><button class="btn primary" :disabled="busy || !reply.trim()">{{ internal ? "Add note" : t("Send") }}</button></div>
          </form>
          <div v-if="!tk.is_staff && ['Resolved', 'Closed'].includes(tk.status)" class="stack resolved">
            <template v-if="!tk.rating">
              <p>{{ t("Rate this resolution") }}</p>
              <div class="stars" role="radiogroup" aria-label="Rating"><button v-for="n in 5" :key="n" type="button" role="radio" :aria-checked="rating === n" :class="{ on: n <= rating }" @click="rating = n">★</button></div>
              <div><button class="btn sm primary" :disabled="!rating" @click="act(() => Helpdesk.rate(name, rating), 'Thanks for the feedback')">Send rating</button></div>
            </template>
            <p v-else class="small muted">You rated this {{ Math.round(tk.rating * 5) }} / 5.</p>
            <button v-if="tk.can_reopen" class="btn sm" @click="act(() => Helpdesk.reopen(name, 'Issue not resolved'), 'Ticket reopened')">{{ t("Reopen") }}</button>
          </div>
        </section>
        <aside class="panel stack">
          <dl class="kv">
            <div><dt>{{ t("Status") }}</dt><dd><StatusBadge :status="tk.status" /></dd></div>
            <div><dt>Service level</dt><dd><StatusBadge :status="tk.sla_status" /></dd></div>
            <div><dt>Resolve by</dt><dd class="num">{{ dueText }}</dd></div>
            <div><dt>{{ t("Priority") }}</dt><dd>{{ tk.priority }}</dd></div>
            <div><dt>Handled by</dt><dd>{{ tk.assigned_to_name || t("Unassigned") }}</dd></div>
            <div v-if="tk.is_staff"><dt>Employee</dt><dd>{{ tk.employee_name }} <span class="muted small">{{ tk.department }}</span></dd></div>
          </dl>
          <div v-if="tk.attachments.length"><h3>Attachments</h3><ul class="small"><li v-for="a in tk.attachments" :key="a.file_url"><a :href="a.file_url" target="_blank" rel="noopener">{{ a.file_name }}</a></li></ul></div>
          <template v-if="tk.is_staff">
            <div class="field"><label for="as">Assign to</label><select id="as" class="select" :value="tk.assigned_to" @change="act(() => Helpdesk.assign(name, ($event.target as HTMLSelectElement).value), 'Assigned')">
              <option value="" disabled>Choose</option><option v-for="a in agents || []" :key="a.user" :value="a.user">{{ a.name }}</option></select></div>
            <div class="field"><label for="pp">{{ t("Priority") }}</label><select id="pp" class="select" :value="tk.priority" @change="act(() => Helpdesk.setPriority(name, ($event.target as HTMLSelectElement).value), 'Priority updated')">
              <option>Low</option><option>Medium</option><option>High</option><option>Urgent</option></select></div>
            <div class="field"><span class="small muted">Move to</span><div class="row wrap">
              <button v-for="s in tk.transitions" :key="s" class="btn sm" @click="act(() => Helpdesk.setStatus(name, s), `Moved to ${s}`)">{{ t(s) }}</button></div></div>
          </template>
          <button v-else-if="!['Resolved', 'Closed'].includes(tk.status)" class="btn sm ghost" @click="act(() => Helpdesk.close(name), 'Ticket closed')">My issue is solved — close ticket</button>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.composer { border-top: 1px solid var(--line); padding-top: 16px; }
.textarea.int { background: var(--saffron-soft); }
.kv { margin: 0; display: flex; flex-direction: column; gap: 12px; }
dt { font-size: var(--fs-xs); color: var(--ink-3); } dd { margin: 2px 0 0; }
.resolved { border-top: 1px solid var(--line); padding-top: 16px; }
.stars button { border: 0; background: none; font-size: 28px; color: var(--line-strong); cursor: pointer; }
.stars button.on { color: var(--saffron); }
</style>
