<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useUi } from "@/stores/ui";
import { useSession } from "@/stores/session";
import { NAV } from "@/layouts/nav";
import { t } from "@/i18n";
import EssIcon from "@/components/ui/EssIcon.vue";

const ui = useUi();
const s = useSession();
const router = useRouter();
const q = ref("");
const idx = ref(0);
const input = ref<HTMLInputElement | null>(null);

const ACTIONS = [
  { label: "Check in", to: "/attendance/check-in", icon: "clock", module: "attendance" },
  { label: "My roster", to: "/roster", icon: "calendar", module: "roster" },
  { label: "Holidays", to: "/holidays", icon: "calendar", module: "attendance" },
  { label: "Apply for leave", to: "/leave/apply", icon: "sun", module: "leave" },
  { label: "New claim", to: "/finances/expenses/new", icon: "receipt", module: "expenses" },
  { label: "New ticket", to: "/support/new", icon: "lifebuoy", module: "helpdesk" },
  { label: "Request document", to: "/documents?request=1", icon: "file", module: "documents" },
  { label: "Give recognition", to: "/recognition?give=1", icon: "star", module: "recognition" },
  { label: "Request correction", to: "/attendance/corrections?new=1", icon: "clock", module: "attendance" },
];

const all = computed(() => {
  const navItems = NAV.filter((g) => s.can(g.cap)).flatMap((g) => g.items)
    .filter((i) => s.can(i.cap) && (!i.module || s.module(i.module)));
  const acts = ACTIONS.filter((a) => s.module(a.module) && s.employee);
  return [...acts.map((a) => ({ ...a, kind: "Action" })), ...navItems.map((n) => ({ ...n, kind: "Page" }))];
});
const results = computed(() => {
  const term = q.value.trim().toLowerCase();
  const list = term ? all.value.filter((i) => `${i.label} ${t(i.label)}`.toLowerCase().includes(term)) : all.value;
  return list.slice(0, 12);
});
watch(() => ui.paletteOpen, async (o) => { if (o) { q.value = ""; idx.value = 0; await nextTick(); input.value?.focus(); } });
watch(q, () => (idx.value = 0));

function go(i = idx.value) {
  const r = results.value[i];
  if (!r) return;
  ui.paletteOpen = false;
  router.push(r.to);
}
function key(e: KeyboardEvent) {
  if (e.key === "ArrowDown") { e.preventDefault(); idx.value = Math.min(idx.value + 1, results.value.length - 1); }
  else if (e.key === "ArrowUp") { e.preventDefault(); idx.value = Math.max(idx.value - 1, 0); }
  else if (e.key === "Enter") { e.preventDefault(); go(); }
  else if (e.key === "Escape") ui.paletteOpen = false;
}
</script>

<template>
  <div v-if="ui.paletteOpen" class="overlay" @click.self="ui.paletteOpen = false">
    <div class="palette" role="dialog" aria-modal="true" :aria-label="t('Search or jump to…')">
      <div class="in">
        <EssIcon name="search" :size="18" />
        <input ref="input" v-model="q" :placeholder="t('Search or jump to…')" @keydown="key" role="combobox"
               aria-controls="pal-list" :aria-activedescendant="`pal-${idx}`" aria-expanded="true" />
      </div>
      <ul id="pal-list" role="listbox">
        <li v-for="(r, i) in results" :key="r.to + r.kind" :id="`pal-${i}`" role="option" :aria-selected="i === idx"
            :class="{ on: i === idx }" @mouseenter="idx = i" @click="go(i)">
          <EssIcon :name="r.icon" :size="18" />
          <span class="grow">{{ t(r.label) }}</span>
          <span class="muted small">{{ r.kind === "Action" ? "Do" : "Go" }}</span>
        </li>
        <li v-if="!results.length" class="muted empty">{{ t("No results") }}</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(10, 20, 17, .4); z-index: 60; display: flex; justify-content: center; padding-top: 12vh; }
.palette { width: min(560px, calc(100vw - 24px)); background: var(--surface); border-radius: 14px; box-shadow: var(--shadow-pop); overflow: hidden; align-self: flex-start; border: 1px solid var(--line); }
.in { display: flex; align-items: center; gap: 10px; padding: 0 16px; border-bottom: 1px solid var(--line); color: var(--ink-3); }
.in input { flex: 1; border: 0; outline: none; background: none; height: 52px; font-size: var(--fs-md); color: var(--ink); }
ul { list-style: none; margin: 0; padding: 6px; max-height: 50vh; overflow-y: auto; }
li { display: flex; align-items: center; gap: 12px; min-height: 42px; padding: 0 12px; border-radius: 8px; cursor: pointer; }
li.on { background: var(--brand-soft); }
.empty { padding: 16px; cursor: default; }
</style>
