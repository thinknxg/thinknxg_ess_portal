<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute } from "vue-router";
import { NAV } from "./nav";
import { useSession } from "@/stores/session";
import { useUi } from "@/stores/ui";
import { t } from "@/i18n";
import EssIcon from "@/components/ui/EssIcon.vue";
import { useApprovalQueue } from "@/composables/hr";

const s = useSession();
const ui = useUi();
const route = useRoute();
const approvals = s.can("manager|hr") ? useApprovalQueue() : null;

const groups = computed(() => NAV.filter((g) => s.can(g.cap)).map((g) => ({
  ...g, items: g.items.filter((i) => s.can(i.cap) && (!i.module || s.module(i.module)) && (s.employee || i.cap)),
})).filter((g) => g.items.length));

function badge(key?: string) {
  if (key === "approvals") return approvals?.items.value.length || 0;
  return 0;
}
// The most specific nav entry wins, so /team/approvals highlights Approvals, not Team overview.
const activeTo = computed(() => {
  const all = groups.value.flatMap((g) => g.items.map((i) => i.to));
  const hits = all.filter((to) => (to === "/" ? route.path === "/" : route.path === to || route.path.startsWith(to + "/")));
  return hits.sort((a, b) => b.length - a.length)[0];
});
const active = (to: string) => activeTo.value === to;
watch(() => route.fullPath, () => (ui.navOpen = false));
</script>

<template>
  <aside class="rail" :class="{ open: ui.navOpen }" :aria-label="t('Overview')">
    <div class="brand">
      <img v-if="s.settings.logo" :src="s.settings.logo" alt="" class="logo" />
      <span v-else class="mark" aria-hidden="true">n</span>
      <div class="brand-text">
        <strong>{{ s.settings.portal_title || "thinkNXG ESS Portal" }}</strong>
        <span class="muted small">{{ s.employee?.company || "thinkNXG HR" }}</span>
      </div>
    </div>
    <nav>
      <section v-for="g in groups" :key="g.label" class="group">
        <h2 class="group-label">{{ t(g.label) }}</h2>
        <RouterLink v-for="i in g.items" :key="i.to" :to="i.to" class="item" :class="{ active: active(i.to) }"
                    :aria-current="active(i.to) ? 'page' : undefined">
          <EssIcon :name="i.icon" :size="18" />
          <span class="grow">{{ t(i.label) }}</span>
          <span v-if="badge(i.badge)" class="count num">{{ badge(i.badge) }}</span>
        </RouterLink>
      </section>
    </nav>
    <a v-if="s.user.desk_access" href="/app" class="item desk" :title="t('Switch to Desk')">
      <EssIcon name="desk" :size="18" />
      <span class="grow">{{ t("Switch to Desk") }}</span>
    </a>
  </aside>
</template>

<style scoped>
.rail { position: sticky; top: 0; height: 100vh; overflow-y: auto; border-inline-end: 1px solid var(--line); background: var(--surface); padding: 16px 12px 24px; display: flex; flex-direction: column; gap: 20px; }
.brand { display: flex; align-items: center; gap: 10px; padding: 4px 8px; }
.mark { width: 34px; height: 34px; border-radius: 10px; background: var(--brand); color: #fff; display: grid; place-items: center; font-weight: 700; font-size: 18px; }
.logo { width: 34px; height: 34px; object-fit: contain; }
.brand-text { display: flex; flex-direction: column; line-height: 1.25; min-width: 0; }
.brand-text strong { font-size: var(--fs-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.group { display: flex; flex-direction: column; gap: 2px; }
.group + .group { margin-top: 14px; }
.group-label { font-size: var(--fs-xs); font-weight: 500; color: var(--ink-3); padding: 0 10px 4px; }
.item { display: flex; align-items: center; gap: 10px; min-height: 38px; padding: 0 10px; border-radius: 8px; color: var(--ink-2); text-decoration: none; font-size: var(--fs-sm); position: relative; }
.item:hover { background: var(--surface-2); color: var(--ink); }
.item.active { background: var(--brand-soft); color: var(--ink); font-weight: 500; }
.item.active::before { content: ""; position: absolute; inset-inline-start: -12px; top: 8px; bottom: 8px; width: 3px; border-radius: 3px; background: var(--brand); }
.desk { margin-top: auto; border-top: 1px solid var(--line); border-radius: 0 0 8px 8px; padding-top: 6px; min-height: 46px; }
.count { min-width: 22px; height: 20px; padding: 0 6px; border-radius: 10px; background: var(--saffron); color: #2B1D02; font-size: var(--fs-xs); font-weight: 600; display: grid; place-items: center; }
@media (max-width: 960px) {
  .rail { position: fixed; inset-block: 0; inset-inline-start: 0; width: min(86vw, 300px); z-index: 40; transform: translateX(-105%); transition: transform .2s ease; box-shadow: var(--shadow-pop); }
  [dir="rtl"] .rail { transform: translateX(105%); }
  .rail.open, [dir="rtl"] .rail.open { transform: none; }
}
</style>
