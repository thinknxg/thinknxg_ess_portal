<script setup lang="ts">
defineProps<{ modelValue: boolean | number; label: string; hint?: string; disabled?: boolean; id: string }>();
defineEmits<{ "update:modelValue": [v: number] }>();
</script>

<template>
  <div class="sw">
    <div class="txt">
      <label :for="id" class="l">{{ label }}</label>
      <p v-if="hint" class="small muted">{{ hint }}</p>
    </div>
    <button :id="id" type="button" role="switch" :aria-checked="!!modelValue" :disabled="disabled" class="track" :class="{ on: !!modelValue }"
            @click="$emit('update:modelValue', modelValue ? 0 : 1)"><span class="knob" /></button>
  </div>
</template>

<style scoped>
.sw { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 12px 0; border-top: 1px solid var(--line); }
.sw:first-child { border-top: 0; }
.l { font-weight: 500; }
.txt { min-width: 0; }
.track { flex: none; width: 46px; height: 26px; border-radius: 13px; border: 0; background: var(--line-strong); position: relative; cursor: pointer; transition: background .15s; }
.track.on { background: var(--brand); }
.track:disabled { opacity: .5; cursor: not-allowed; }
.knob { position: absolute; top: 3px; inset-inline-start: 3px; width: 20px; height: 20px; border-radius: 50%; background: #fff; transition: inset-inline-start .15s; box-shadow: 0 1px 3px rgba(0,0,0,.25); }
.track.on .knob { inset-inline-start: 23px; }
</style>
