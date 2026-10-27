<script setup lang="ts">
import { useUi } from "@/stores/ui";
const ui = useUi();
</script>

<template>
  <div class="toasts" aria-live="polite" aria-atomic="false">
    <div v-for="t in ui.toasts" :key="t.id" class="toast" :class="t.kind" :role="t.kind === 'error' ? 'alert' : 'status'">
      <span class="grow">{{ t.message }}</span>
      <button v-if="t.action" class="btn sm ghost" @click="t.action.run(); ui.dismiss(t.id)">{{ t.action.label }}</button>
      <button class="x" @click="ui.dismiss(t.id)" aria-label="Dismiss">×</button>
    </div>
  </div>
</template>

<style scoped>
.toasts { position: fixed; z-index: 70; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; flex-direction: column; gap: 8px; width: min(440px, calc(100vw - 24px)); }
.toast { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border-radius: 10px; background: var(--ink); color: var(--paper); box-shadow: var(--shadow-pop); font-size: var(--fs-sm); animation: up .18s ease-out; }
.toast.error { background: var(--pom); color: #fff; }
.toast .btn { color: inherit; }
.x { border: 0; background: none; color: inherit; font-size: 20px; cursor: pointer; opacity: .7; }
@keyframes up { from { transform: translateY(8px); opacity: 0; } }
@media (max-width: 960px) { .toasts { bottom: 92px; } }
</style>
