<script setup lang="ts">
import { useSession } from "@/stores/session";
import { t } from "@/i18n";
import EssIcon from "@/components/ui/EssIcon.vue";

const s = useSession();
</script>

<template>
  <nav class="tabs" aria-label="Primary" v-if="s.employee">
    <RouterLink to="/" class="tab" exact-active-class="on"><EssIcon name="home" /><span>{{ t("Home") }}</span></RouterLink>
    <RouterLink v-if="s.module('leave')" to="/leave" class="tab" active-class="on"><EssIcon name="sun" /><span>{{ t("Leave") }}</span></RouterLink>
    <RouterLink v-if="s.module('checkin')" to="/attendance/check-in" class="punch" :aria-label="t('Check in')"><EssIcon name="clock" :size="24" /></RouterLink>
    <RouterLink to="/inbox" class="tab" active-class="on"><EssIcon name="inbox" /><span>{{ t("Inbox") }}</span></RouterLink>
    <RouterLink v-if="s.can('manager|hr')" to="/team/approvals" class="tab" active-class="on"><EssIcon name="check" /><span>{{ t("Approvals") }}</span></RouterLink>
    <RouterLink v-else to="/assistant" class="tab" active-class="on"><EssIcon name="spark" /><span>{{ t("HR assistant") }}</span></RouterLink>
  </nav>
</template>

<style scoped>
.tabs { display: none; }
@media (max-width: 960px) {
  .tabs { position: fixed; bottom: 0; inset-inline: 0; z-index: 25; display: grid; grid-template-columns: repeat(5, 1fr); align-items: end;
    background: var(--surface); border-top: 1px solid var(--line); padding: 6px 4px calc(6px + env(safe-area-inset-bottom)); }
  .tab { display: flex; flex-direction: column; align-items: center; gap: 2px; min-height: 48px; justify-content: center; color: var(--ink-3); text-decoration: none; font-size: 11px; }
  .tab span { max-width: 72px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tab.on { color: var(--brand); font-weight: 600; }
  .punch { justify-self: center; width: 56px; height: 56px; margin-top: -22px; border-radius: 50%; background: var(--brand); color: #fff; display: grid; place-items: center; box-shadow: 0 6px 16px -4px color-mix(in srgb, var(--brand) 60%, transparent); border: 4px solid var(--surface); }
}
</style>
