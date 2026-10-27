<script setup lang="ts">
import type { ApiError } from "@/services/api";
import { t } from "@/i18n";
defineProps<{ error: ApiError | null }>();
defineEmits<{ retry: [] }>();
</script>

<template>
  <div v-if="error" class="err" role="alert">
    <p v-if="error.isPermission">{{ t("You don't have access to this page.") }}</p>
    <p v-else-if="error.isOffline">{{ error.message }}</p>
    <p v-else>{{ error.message || t("Something went wrong") }}</p>
    <button v-if="!error.isPermission" class="btn sm" @click="$emit('retry')">{{ t("Try again") }}</button>
  </div>
</template>

<style scoped>
.err { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; border-radius: 10px; background: var(--pom-soft); color: var(--pom); font-size: var(--fs-sm); }
</style>
