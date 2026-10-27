<script setup lang="ts">
defineProps<{ modelValue: string; tabs: { value: string; label: string; count?: number }[]; label?: string }>();
defineEmits<{ "update:modelValue": [v: string] }>();
</script>

<template>
  <div class="tabs" role="tablist" :aria-label="label">
    <button v-for="t in tabs" :key="t.value" role="tab" :aria-selected="modelValue === t.value" :class="{ on: modelValue === t.value }"
            @click="$emit('update:modelValue', t.value)">
      {{ t.label }}<span v-if="t.count" class="c num">{{ t.count }}</span>
    </button>
  </div>
</template>

<style scoped>
.tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--line); overflow-x: auto; scrollbar-width: none; }
button { border: 0; background: none; padding: 10px 12px; color: var(--ink-3); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; white-space: nowrap; font-weight: 500; font-size: var(--fs-sm); }
button.on { color: var(--ink); border-color: var(--brand); }
.c { margin-inline-start: 6px; padding: 0 6px; border-radius: 9px; background: var(--surface-2); font-size: var(--fs-xs); }
</style>
