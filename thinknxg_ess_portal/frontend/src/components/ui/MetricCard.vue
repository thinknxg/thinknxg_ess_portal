<script setup lang="ts">
defineProps<{ label: string; value: string | number | null; hint?: string; tone?: "warn" | "bad" | "ok" }>();
</script>

<template>
  <div class="metric" :class="tone">
    <span class="label">{{ label }}</span>
    <span class="value num">{{ value ?? "—" }}</span>
    <span v-if="hint" class="hint">{{ hint }}</span>
  </div>
</template>

<style scoped>
.metric { display: flex; flex-direction: column; gap: 2px; padding: 14px 16px; border-inline-start: 3px solid var(--line-strong); }
.metric.warn { border-color: var(--saffron); }
.metric.bad { border-color: var(--pom); }
.metric.ok { border-color: var(--ok); }
.label { font-size: var(--fs-sm); color: var(--ink-3); }
.value { font-size: var(--fs-xl); font-weight: 600; letter-spacing: -0.02em; }
.hint { font-size: var(--fs-xs); color: var(--ink-3); }
</style>
