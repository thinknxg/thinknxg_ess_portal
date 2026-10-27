<script setup lang="ts">
import { fmtDate, fmtTime } from "@/i18n";
import Avatar from "@/components/ui/Avatar.vue";
defineProps<{ description?: string; raisedBy?: string; created?: string; comments: any[] }>();
</script>

<template>
  <ol class="conv">
    <li v-if="description" class="msg emp">
      <Avatar :name="raisedBy" :size="30" />
      <div class="bubble"><p class="meta small"><strong>{{ raisedBy }}</strong> <span class="muted">{{ fmtDate(created) }}</span></p>
        <div class="body" v-html="description" /></div>
    </li>
    <li v-for="c in comments" :key="c.name" class="msg" :class="[c.via === 'Agent' ? 'agent' : c.via === 'System' ? 'sys' : 'emp', { internal: c.is_internal }]">
      <Avatar v-if="c.via !== 'System'" :name="c.author_name" :size="30" />
      <div class="bubble">
        <p class="meta small"><strong>{{ c.via === "System" ? "System" : c.author_name }}</strong>
          <span class="muted">{{ fmtDate(c.creation) }} {{ fmtTime(c.creation) }}</span>
          <span v-if="c.is_internal" class="int">Internal note</span></p>
        <div class="body" v-html="c.comment" />
      </div>
    </li>
  </ol>
</template>

<style scoped>
.conv { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 14px; }
.msg { display: flex; gap: 10px; align-items: flex-start; }
.bubble { flex: 1; min-width: 0; padding: 10px 14px; border-radius: 12px; background: var(--surface-2); }
.agent .bubble { background: var(--brand-soft); }
.internal .bubble { background: var(--saffron-soft); border: 1px dashed var(--saffron); }
.sys { justify-content: center; }
.sys .bubble { flex: 0 1 auto; background: none; color: var(--ink-3); font-size: var(--fs-sm); text-align: center; }
.meta { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 4px; }
.int { color: var(--saffron-ink); font-weight: 600; }
.body :deep(p) { margin: 0 0 6px; }
.body :deep(img) { max-width: 100%; }
.body { overflow-wrap: anywhere; }
</style>
