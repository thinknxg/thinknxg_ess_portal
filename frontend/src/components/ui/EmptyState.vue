<script setup lang="ts">
import EssIcon from "./EssIcon.vue";
defineProps<{ title: string; text?: string; icon?: string; actionLabel?: string; actionTo?: string }>();
defineEmits<{ action: [] }>();
</script>

<template>
  <div class="empty">
    <EssIcon :name="icon || 'inbox'" :size="28" />
    <p class="t">{{ title }}</p>
    <p v-if="text" class="muted small">{{ text }}</p>
    <RouterLink v-if="actionLabel && actionTo" :to="actionTo" class="btn sm primary">{{ actionLabel }}</RouterLink>
    <button v-else-if="actionLabel" class="btn sm primary" @click="$emit('action')">{{ actionLabel }}</button>
  </div>
</template>

<style scoped>
.empty { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 6px; padding: 28px 16px; color: var(--ink-3); }
.t { color: var(--ink); font-weight: 500; }
.btn { margin-top: 8px; }
</style>
