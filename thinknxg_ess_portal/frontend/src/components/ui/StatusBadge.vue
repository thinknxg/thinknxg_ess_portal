<script setup lang="ts">
import { computed } from "vue";
import { toneFor } from "@/utils/format";
import { t } from "@/i18n";
const props = defineProps<{ status?: string | null; tone?: "ok" | "warn" | "bad" | "info" | "muted"; label?: string }>();
const tn = computed(() => props.tone || toneFor(props.status));
</script>

<template>
  <span class="badge" :class="tn"><span class="pip" aria-hidden="true" />{{ label || t(status || "") }}</span>
</template>

<style scoped>
.badge { display: inline-flex; align-items: center; gap: 6px; height: 24px; padding: 0 9px; border-radius: 12px; font-size: var(--fs-xs); font-weight: 500; white-space: nowrap; }
.pip { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.ok { background: var(--ok-soft); color: var(--ok); }
.warn { background: var(--saffron-soft); color: var(--saffron-ink); }
.bad { background: var(--pom-soft); color: var(--pom); }
.info { background: var(--info-soft); color: var(--info); }
.muted { background: var(--surface-2); color: var(--ink-3); }
</style>
