<script setup lang="ts">
import { useRoute } from "vue-router";
import { computed } from "vue";
import { useUi } from "@/stores/ui";
import { useSession } from "@/stores/session";
import { t } from "@/i18n";
import EssIcon from "@/components/ui/EssIcon.vue";
import UserMenu from "@/components/shell/UserMenu.vue";

const ui = useUi();
const s = useSession();
const route = useRoute();
const title = computed(() => t(String(route.meta.title || "Home")));
const isMac = typeof navigator !== "undefined" && /Mac/.test(navigator.platform);
</script>

<template>
  <header class="bar">
    <button class="btn ghost icon menu" @click="ui.navOpen = true" aria-label="Open navigation"><EssIcon name="menu" /></button>
    <span class="title">{{ title }}</span>
    <button class="search" @click="ui.paletteOpen = true">
      <EssIcon name="search" :size="16" />
      <span class="grow">{{ t("Search or jump to…") }}</span>
      <kbd>{{ isMac ? "⌘" : "Ctrl" }} K</kbd>
    </button>
    <RouterLink to="/notifications" class="btn ghost icon bell" :aria-label="`${t('Notifications')} (${s.unread})`">
      <EssIcon name="bell" />
      <span v-if="s.unread" class="dot num">{{ s.unread > 9 ? "9+" : s.unread }}</span>
    </RouterLink>
    <UserMenu />
  </header>
</template>

<style scoped>
.bar { position: sticky; top: 0; z-index: 20; height: var(--header); display: flex; align-items: center; gap: 12px; padding: 0 20px; background: color-mix(in srgb, var(--paper) 88%, transparent); backdrop-filter: blur(10px); border-bottom: 1px solid var(--line); }
.title { font-weight: 600; display: none; }
.menu { display: none; }
.search { flex: 0 1 420px; display: flex; align-items: center; gap: 8px; height: 38px; padding: 0 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink-3); cursor: pointer; text-align: start; }
.search:hover { border-color: var(--line-strong); }
kbd { font: inherit; font-size: var(--fs-xs); border: 1px solid var(--line); border-radius: 4px; padding: 0 5px; }
.bell { position: relative; margin-inline-start: auto; }
.dot { position: absolute; top: 3px; inset-inline-end: 2px; min-width: 18px; height: 18px; padding: 0 4px; border-radius: 9px; background: var(--pom); color: #fff; font-size: 11px; display: grid; place-items: center; }
@media (max-width: 960px) {
  .menu, .title { display: inline-flex; }
  .search { flex: 0 0 auto; width: 40px; padding: 0; justify-content: center; border-color: transparent; background: transparent; }
  .search span, .search kbd { display: none; }
  .bar { padding: 0 8px; padding-top: env(safe-area-inset-top); }
  .bell { margin-inline-start: auto; }
}
</style>
