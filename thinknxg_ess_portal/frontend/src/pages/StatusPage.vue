<script setup lang="ts">
import { t } from "@/i18n";
import EmptyState from "@/components/ui/EmptyState.vue";
defineProps<{ kind: "forbidden" | "notfound" }>();
</script>

<template>
  <div class="page">
    <section class="panel">
      <EmptyState v-if="kind === 'forbidden'" :title="t('You don\'t have access to this page.')"
        text="Access follows your HR role and reporting line. If you think you should see this, raise an HR ticket." icon="shield" :action-label="t('Go home')" action-to="/" />
      <EmptyState v-else :title="t('Page not found')" text="The link may be old, or the record was removed." icon="search" :action-label="t('Go home')" action-to="/" />
    </section>
  </div>
</template>
