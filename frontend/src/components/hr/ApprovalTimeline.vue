<script setup lang="ts">
import { fmtDate } from "@/i18n";
defineProps<{ steps: { label: string; who?: string; when?: string | null; state: "done" | "current" | "todo" | "rejected" }[] }>();
</script>

<template>
  <ol class="tl">
    <li v-for="(s, i) in steps" :key="i" :class="s.state">
      <span class="dot" aria-hidden="true" />
      <div>
        <p class="l">{{ s.label }}</p>
        <p class="muted small" v-if="s.who || s.when">{{ s.who }}<template v-if="s.who && s.when"> — </template>{{ s.when ? fmtDate(s.when) : "" }}</p>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.tl { list-style: none; margin: 0; padding: 0; }
.tl li { display: flex; gap: 12px; position: relative; padding-bottom: 16px; }
.tl li:not(:last-child)::after { content: ""; position: absolute; inset-inline-start: 6px; top: 16px; bottom: 0; width: 2px; background: var(--line); }
.dot { width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--line-strong); background: var(--surface); flex: none; margin-top: 3px; }
.done .dot { background: var(--ok); border-color: var(--ok); }
.current .dot { border-color: var(--saffron); box-shadow: 0 0 0 4px var(--saffron-soft); }
.rejected .dot { background: var(--pom); border-color: var(--pom); }
.l { font-weight: 500; }
</style>
