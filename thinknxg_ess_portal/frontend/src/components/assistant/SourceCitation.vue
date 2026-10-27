<script setup lang="ts">
import type { Citation } from "@/types";
import { t } from "@/i18n";
defineProps<{ citations: Citation[] }>();
</script>

<template>
  <details class="src">
    <summary>{{ t("Sources") }} ({{ citations.length }})</summary>
    <ol>
      <li v-for="c in citations" :key="c.source"><strong>{{ c.title }}</strong><span v-if="c.section && c.section !== c.title" class="muted"> — {{ c.section }}</span>
        <p v-if="c.snippet" class="small muted">{{ c.snippet }}…</p></li>
    </ol>
  </details>
</template>

<style scoped>
.src { border-inline-start: 2px solid var(--brand); padding-inline-start: 12px; font-size: var(--fs-sm); }
summary { cursor: pointer; color: var(--brand); font-weight: 500; }
ol { margin: 8px 0 0; padding-inline-start: 18px; display: flex; flex-direction: column; gap: 6px; }
</style>
