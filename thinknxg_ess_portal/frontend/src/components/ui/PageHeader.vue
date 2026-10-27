<script setup lang="ts">
import EssIcon from "./EssIcon.vue";
defineProps<{ title: string; subtitle?: string; back?: string }>();
</script>

<template>
  <div class="ph">
    <RouterLink v-if="back" :to="back" class="btn ghost icon" aria-label="Back"><EssIcon name="back" /></RouterLink>
    <div class="grow">
      <h1>{{ title }}</h1>
      <p v-if="subtitle" class="muted">{{ subtitle }}</p>
    </div>
    <div class="actions"><slot /></div>
  </div>
</template>

<style scoped>
.ph { display: flex; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.ph h1 { font-size: var(--fs-xl); }
.ph p { margin-top: 4px; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; }
@media (max-width: 640px) { .ph h1 { font-size: 1.3rem; } .actions { width: 100%; } .actions :deep(.btn) { flex: 1; } }
</style>
