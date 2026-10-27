<script setup lang="ts">
import { ref, watch } from "vue";
import AccessibleDialog from "./AccessibleDialog.vue";
import { t } from "@/i18n";
const props = defineProps<{ open: boolean; title: string; text?: string; confirmLabel: string; danger?: boolean; requireComment?: boolean; commentLabel?: string; busy?: boolean }>();
const emit = defineEmits<{ close: []; confirm: [comment: string] }>();
const comment = ref("");
watch(() => props.open, (o) => { if (o) comment.value = ""; });
</script>

<template>
  <AccessibleDialog :open="open" :title="title" @close="emit('close')">
    <div class="stack">
      <p v-if="text">{{ text }}</p>
      <div class="field" v-if="requireComment !== undefined">
        <label for="cad-c">{{ commentLabel || t("Reason") }}<span v-if="requireComment"> *</span></label>
        <textarea id="cad-c" class="textarea" v-model="comment" />
      </div>
    </div>
    <template #footer>
      <button class="btn" @click="emit('close')">{{ t("Cancel") }}</button>
      <button class="btn" :class="danger ? 'danger' : 'primary'" :disabled="busy || (requireComment && !comment.trim())"
              @click="emit('confirm', comment)">{{ confirmLabel }}</button>
    </template>
  </AccessibleDialog>
</template>
