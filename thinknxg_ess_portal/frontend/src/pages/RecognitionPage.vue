<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { useResource, invalidate } from "@/composables/useResource";
import { Approvals, Recognition } from "@/services/endpoints";
import { useSubmit } from "@/composables/useSubmit";
import { useSession } from "@/stores/session";
import { relative, t } from "@/i18n";
import PageHeader from "@/components/ui/PageHeader.vue";
import SegmentTabs from "@/components/ui/SegmentTabs.vue";
import AccessibleDialog from "@/components/ui/AccessibleDialog.vue";
import Avatar from "@/components/ui/Avatar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";

const route = useRoute();
const s = useSession();
const scope = ref("all");
const { data: feed, reload } = useResource<any[]>(() => `rec:feed:${scope.value}`, () => Recognition.feed(scope.value), { watch: [scope] });
const { data: sum, reload: reloadSum } = useResource<any>(() => "rec:summary", () => Recognition.summary());
const open = ref(!!route.query.give);
const q = ref("");
const people = ref<any[]>([]);
const form = ref<any>({ recipient: null, category: "", message: "", visibility: "Public" });
const { state, error, submit, reset } = useSubmit();
const EMO: Record<string, string> = { clap: "👏", celebrate: "🎉", heart: "❤️", highfive: "🙌", insight: "💡" };
const pts = computed(() => sum.value?.categories?.find((c: any) => c.name === form.value.category)?.default_points || 0);

let timer: number | undefined;
function search() { window.clearTimeout(timer); timer = window.setTimeout(async () => { people.value = q.value.length > 1 ? await Approvals.colleagues(q.value) : []; }, 250); }
function choose(p: any) { form.value.recipient = p; people.value = []; q.value = ""; }
async function give() {
  const r = await submit("recognition.give", { recipient: form.value.recipient.name, category: form.value.category, message: form.value.message, visibility: form.value.visibility },
    `Recognition for ${form.value.recipient.employee_name}`, ["rec:"]);
  if (r || state.value === "queued") { open.value = false; form.value = { recipient: null, category: "", message: "", visibility: "Public" }; reset(); reload(); reloadSum(); }
}
async function react(r: any, key: string) {
  const res: any = await Recognition.react(r.name, key);
  r.reactions[key] = (r.reactions[key] || 0) + (res.active ? 1 : -1);
  r.my_reactions = res.active ? [...r.my_reactions, key] : r.my_reactions.filter((x: string) => x !== key);
  invalidate("rec:feed");
}
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Recognition')" subtitle="Thank colleagues for the work that matched our values.">
      <button class="btn primary" @click="open = true">{{ t("Give recognition") }}</button>
    </PageHeader>
    <div class="cols">
      <div class="stack">
        <SegmentTabs v-model="scope" :tabs="[{ value: 'all', label: 'Company' }, { value: 'mine', label: 'Mine' }, ...(s.can('manager') ? [{ value: 'team', label: 'My team' }] : [])]" />
        <article v-for="r in feed || []" :key="r.name" class="kudo panel tight">
          <div class="row"><span class="cat" aria-hidden="true">{{ r.icon }}</span>
            <p class="grow"><strong>{{ r.sender_name }}</strong> recognised <strong>{{ r.recipient_name }}</strong><span class="muted"> for {{ r.category || "great work" }}</span></p>
            <span class="muted small">{{ relative(r.posted_on) }}</span></div>
          <p class="msg">{{ r.message }}</p>
          <div class="reacts">
            <button v-for="(e, k) in EMO" :key="k" class="react" :class="{ on: r.my_reactions.includes(k) }" :aria-pressed="r.my_reactions.includes(k)" @click="react(r, String(k))" :aria-label="String(k)">
              {{ e }}<span v-if="r.reactions[k]" class="num">{{ r.reactions[k] }}</span></button>
          </div>
        </article>
        <section class="panel" v-if="feed && !feed.length"><EmptyState title="No recognition yet" text="Be the first to thank someone." icon="star" :action-label="t('Give recognition')" @action="open = true" /></section>
      </div>
      <aside class="stack" v-if="sum">
        <section class="panel">
          <header><h2>Your recognition</h2></header>
          <div class="trio"><div><span class="big num">{{ sum.received }}</span><span class="small muted">received</span></div>
            <div><span class="big num">{{ sum.given }}</span><span class="small muted">given</span></div>
            <div><span class="big num">{{ sum.budget_remaining }}</span><span class="small muted">points left this month</span></div></div>
        </section>
        <section class="panel">
          <header><h2>{{ t("Badges") }}</h2></header>
          <ul class="list">
            <li v-for="b in sum.catalog" :key="b.name" :class="{ dim: !sum.badges.find((x: any) => x.badge === b.name) }">
              <span class="bi">{{ b.icon }}</span><span class="grow"><span class="title">{{ b.name }}</span><br><span class="small muted">{{ b.description || b.rule_type }}</span></span>
              <span v-if="sum.badges.find((x: any) => x.badge === b.name)" class="small ok">Earned</span>
            </li>
          </ul>
        </section>
      </aside>
    </div>

    <AccessibleDialog :open="open" :title="t('Give recognition')" @close="open = false">
      <form id="giv" class="stack" @submit.prevent="give">
        <div class="field" v-if="!form.recipient"><label for="who">{{ t("Colleague") }}</label>
          <input id="who" class="input" v-model="q" @input="search" placeholder="Type a name" autocomplete="off" />
          <ul class="list pick" v-if="people.length"><li v-for="p in people" :key="p.name"><button type="button" class="rowlink plain" @click="choose(p)"><Avatar :name="p.employee_name" :image="p.image" :size="28" /><span class="grow">{{ p.employee_name }}<br><span class="small muted">{{ p.designation }}</span></span></button></li></ul>
        </div>
        <div v-else class="row chosen"><Avatar :name="form.recipient.employee_name" :image="form.recipient.image" :size="32" /><span class="grow">{{ form.recipient.employee_name }}</span><button type="button" class="btn ghost sm" @click="form.recipient = null">Change</button></div>
        <fieldset class="vals"><legend>Value</legend>
          <label v-for="c in sum?.categories || []" :key="c.name" class="val" :class="{ on: form.category === c.name }"><input type="radio" class="sr-only" :value="c.name" v-model="form.category" />{{ c.icon }} {{ c.name }}</label></fieldset>
        <div class="field"><label for="msg">{{ t("Message") }}</label><textarea id="msg" class="textarea" v-model="form.message" minlength="10" maxlength="1000" required placeholder="What did they do, and what difference did it make?" /></div>
        <div class="field"><label for="vis">Who can see it</label><select id="vis" class="select" v-model="form.visibility">
          <option v-if="s.settings.allow_public_recognition" value="Public">Everyone in the company</option><option value="Team">Their team</option><option value="Private">Only them</option></select></div>
        <p class="small muted" v-if="pts">Includes {{ pts }} points from your monthly budget ({{ sum?.budget_remaining }} left).</p>
        <p v-if="error" class="small bad" role="alert">{{ error }}</p>
      </form>
      <template #footer><button class="btn" @click="open = false">{{ t("Cancel") }}</button><button class="btn primary" form="giv" :disabled="!form.recipient || state === 'submitting'">Send recognition</button></template>
    </AccessibleDialog>
  </div>
</template>

<style scoped>
.kudo { display: flex; flex-direction: column; gap: 10px; }
.cat { font-size: 24px; }
.msg { font-size: var(--fs-md); line-height: 1.6; max-width: 70ch; }
.reacts { display: flex; gap: 6px; flex-wrap: wrap; }
.react { display: inline-flex; gap: 4px; align-items: center; height: 30px; padding: 0 10px; border-radius: 15px; border: 1px solid var(--line); background: var(--surface); cursor: pointer; font-size: var(--fs-sm); }
.react.on { border-color: var(--brand); background: var(--brand-soft); }
.trio { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; } .trio div { display: flex; flex-direction: column; }
.big { font-size: var(--fs-xl); font-weight: 600; }
.bi { font-size: 24px; } .dim { opacity: .45; } .ok { color: var(--ok); } .bad { color: var(--pom); }
.vals { border: 0; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
.vals legend { font-size: var(--fs-sm); font-weight: 500; color: var(--ink-2); margin-bottom: 6px; }
.val { padding: 6px 12px; border-radius: 16px; border: 1px solid var(--line); cursor: pointer; font-size: var(--fs-sm); }
.val.on { border-color: var(--brand); background: var(--brand-soft); }
.val:focus-within { outline: 2px solid var(--focus); }
.pick { border: 1px solid var(--line); border-radius: 8px; padding: 0 8px; }
.plain { border: 0; background: none; cursor: pointer; text-align: start; padding: 0; }
</style>
