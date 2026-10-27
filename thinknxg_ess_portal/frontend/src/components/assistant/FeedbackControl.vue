<script setup lang="ts">
import { ref } from "vue";
import { Assistant } from "@/services/endpoints";
import { t } from "@/i18n";
import EssIcon from "@/components/ui/EssIcon.vue";
const props = defineProps<{ conversation: string }>();
const sent = ref<null | boolean>(null);
async function give(v: boolean) { sent.value = v; try { await Assistant.feedback(props.conversation, v); } catch { /* non-critical */ } }
</script>

<template>
  <span class="fb" role="group" aria-label="Was this helpful?">
    <button class="btn ghost sm icon" :class="{ on: sent === true }" @click="give(true)" :aria-pressed="sent === true" :aria-label="t('Helpful')"><EssIcon name="thumbs_up" :size="16" /></button>
    <button class="btn ghost sm icon" :class="{ on: sent === false }" @click="give(false)" :aria-pressed="sent === false" :aria-label="t('Not helpful')"><EssIcon name="thumbs_down" :size="16" /></button>
  </span>
</template>

<style scoped>
.fb { display: inline-flex; gap: 2px; }
.on { color: var(--brand); background: var(--brand-soft); }
</style>
