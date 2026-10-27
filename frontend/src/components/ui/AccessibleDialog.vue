<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
const props = defineProps<{ open: boolean; title: string; wide?: boolean }>();
const emit = defineEmits<{ close: [] }>();
const box = ref<HTMLElement | null>(null);
let lastFocus: HTMLElement | null = null;

function trap(e: KeyboardEvent) {
  if (e.key === "Escape") { emit("close"); return; }
  if (e.key !== "Tab" || !box.value) return;
  const f = box.value.querySelectorAll<HTMLElement>('a,button:not([disabled]),input,select,textarea,[tabindex]:not([tabindex="-1"])');
  if (!f.length) return;
  const first = f[0], last = f[f.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}
watch(() => props.open, async (o) => {
  if (o) {
    lastFocus = document.activeElement as HTMLElement;
    document.body.style.overflow = "hidden";
    await nextTick();
    (box.value?.querySelector<HTMLElement>("[autofocus],input,select,textarea,button") || box.value)?.focus();
  } else {
    document.body.style.overflow = "";
    lastFocus?.focus();
  }
}, { immediate: true });
onBeforeUnmount(() => (document.body.style.overflow = ""));
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="ov" @click.self="emit('close')">
      <div ref="box" class="dlg" :class="{ wide }" role="dialog" aria-modal="true" :aria-label="title" tabindex="-1" @keydown="trap">
        <header>
          <h2>{{ title }}</h2>
          <button class="btn ghost icon" @click="emit('close')" aria-label="Close">×</button>
        </header>
        <div class="body"><slot /></div>
        <footer v-if="$slots.footer"><slot name="footer" /></footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.ov { position: fixed; inset: 0; z-index: 65; background: rgba(10, 20, 17, .45); display: grid; place-items: center; padding: 16px; }
.dlg { width: min(520px, 100%); max-height: calc(100vh - 32px); display: flex; flex-direction: column; background: var(--surface); border-radius: 16px; box-shadow: var(--shadow-pop); outline: none; }
.dlg.wide { width: min(760px, 100%); }
header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px 8px; }
header .btn { font-size: 22px; }
.body { padding: 8px 20px 16px; overflow-y: auto; }
footer { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 20px 16px; border-top: 1px solid var(--line); }
@media (max-width: 640px) {
  .ov { place-items: end stretch; padding: 0; }
  .dlg { width: 100%; border-radius: 16px 16px 0 0; max-height: 92vh; padding-bottom: env(safe-area-inset-bottom); }
}
</style>
