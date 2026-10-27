<script setup lang="ts">
import { useResource } from "@/composables/useResource";
import { Assistant } from "@/services/endpoints";
import { useSession } from "@/stores/session";
import { t } from "@/i18n";
import AssistantChat from "@/components/assistant/AssistantChat.vue";

const s = useSession();
const { data } = useResource<string[]>(() => "ai:sugs", () => Assistant.suggestions(), { staleMs: 3600_000 });
</script>

<template>
  <div class="page">
    <div class="spread">
      <h1>{{ t("HR assistant") }}</h1>
      <RouterLink to="/support/new" class="btn sm">Talk to a person</RouterLink>
    </div>
    <AssistantChat :suggestions="data || []" />
    <p class="small muted notice">{{ s.settings.ai_system_notice }} The assistant can only see your own records and can't approve or change anything.</p>
  </div>
</template>

<style scoped>.notice { max-width: 72ch; }</style>
