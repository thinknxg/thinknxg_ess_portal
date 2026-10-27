<script setup lang="ts">
import { ref } from "vue";
import { uploadPrivate } from "@/services/api";
import EssIcon from "./EssIcon.vue";

const props = defineProps<{ modelValue: string[]; accept?: string; max?: number; label?: string; capture?: boolean }>();
const emit = defineEmits<{ "update:modelValue": [v: string[]] }>();
const busy = ref(false);
const error = ref<string | null>(null);
const names = ref<Record<string, string>>({});

async function pick(e: Event) {
  const files = Array.from((e.target as HTMLInputElement).files || []);
  (e.target as HTMLInputElement).value = "";
  error.value = null;
  busy.value = true;
  try {
    const out = [...props.modelValue];
    for (const f of files.slice(0, (props.max || 5) - out.length)) {
      const url = await uploadPrivate(f);
      names.value[url] = f.name;
      out.push(url);
    }
    emit("update:modelValue", out);
  } catch (err: any) {
    error.value = err?.message || "Upload failed";
  } finally {
    busy.value = false;
  }
}
function remove(u: string) { emit("update:modelValue", props.modelValue.filter((x) => x !== u)); }
</script>

<template>
  <div class="up">
    <label class="drop" :class="{ busy }">
      <EssIcon name="paperclip" :size="18" />
      <span>{{ busy ? "Uploading…" : (label || "Attach files") }}</span>
      <span class="muted small">Private · up to 10 MB each</span>
      <input type="file" class="sr-only" :accept="accept || 'image/*,application/pdf'" multiple
             :capture="capture ? 'environment' : undefined" :disabled="busy || modelValue.length >= (max || 5)" @change="pick" />
    </label>
    <ul v-if="modelValue.length" class="files">
      <li v-for="u in modelValue" :key="u"><span class="grow">{{ names[u] || u.split("/").pop() }}</span>
        <button type="button" class="btn ghost sm" @click="remove(u)" :aria-label="`Remove ${names[u] || u}`">Remove</button></li>
    </ul>
    <p v-if="error" class="err small">{{ error }}</p>
  </div>
</template>

<style scoped>
.drop { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 14px; border: 1px dashed var(--line-strong); border-radius: 10px; cursor: pointer; color: var(--ink-2); }
.drop:focus-within { outline: 2px solid var(--focus); }
.drop.busy { opacity: .7; }
.files { list-style: none; padding: 0; margin: 8px 0 0; display: flex; flex-direction: column; gap: 4px; font-size: var(--fs-sm); }
.files li { display: flex; align-items: center; gap: 8px; padding: 4px 8px; background: var(--surface-2); border-radius: 6px; }
.err { color: var(--pom); margin-top: 6px; }
</style>
