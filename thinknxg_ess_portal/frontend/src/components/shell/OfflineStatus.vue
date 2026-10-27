<script setup lang="ts">
import { useOnline } from "@/composables/useOnline";
import { queue } from "@/services/offlineQueue";
import { updateReady, applyUpdate } from "@/services/pwa";
import { t } from "@/i18n";
import EssIcon from "@/components/ui/EssIcon.vue";

const online = useOnline();
</script>

<template>
  <div v-if="!online" class="strip off" role="status">
    <EssIcon name="wifi_off" :size="18" />
    <span>{{ t("You're offline") }}. Pages you open need a connection; leave requests, tickets and recognition you submit are kept and sent when you're back.</span>
    <RouterLink v-if="queue.items.length" to="/inbox" class="q">{{ queue.items.length }} {{ t("Waiting to send").toLowerCase() }}</RouterLink>
  </div>
  <div v-else-if="queue.items.length" class="strip q-only" role="status">
    <span>{{ queue.items.length }} {{ t("Waiting to send").toLowerCase() }}…</span>
  </div>
  <div v-if="updateReady" class="strip upd" role="status">
    <span>{{ t("Update available") }}</span>
    <button class="btn sm" @click="applyUpdate">{{ t("Reload") }}</button>
  </div>
</template>

<style scoped>
.strip { display: flex; align-items: center; gap: 10px; padding: 8px 20px; font-size: var(--fs-sm); }
.off { background: var(--saffron-soft); color: var(--saffron-ink); }
.q-only { background: var(--info-soft); color: var(--info); }
.upd { background: var(--brand-soft); justify-content: space-between; }
.q { margin-inline-start: auto; color: inherit; font-weight: 600; }
</style>
