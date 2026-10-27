<script setup lang="ts">
defineProps<{ lines?: number; height?: number }>();
</script>

<template>
  <div class="sk" aria-busy="true" aria-live="polite">
    <span class="sr-only">Loading</span>
    <span v-for="i in lines || 3" :key="i" class="bar" :style="{ height: `${height || 14}px`, width: `${100 - ((i * 17) % 45)}%` }" />
  </div>
</template>

<style scoped>
.sk { display: flex; flex-direction: column; gap: 10px; padding: 4px 0; }
.bar { border-radius: 6px; background: linear-gradient(90deg, var(--surface-2), var(--line), var(--surface-2)); background-size: 200% 100%; animation: sh 1.4s infinite; }
@keyframes sh { to { background-position: -200% 0; } }
</style>
