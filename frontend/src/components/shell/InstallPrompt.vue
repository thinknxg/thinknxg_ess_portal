<script setup lang="ts">
import { ref } from "vue";
import { installEvent, promptInstall } from "@/services/pwa";
import { t } from "@/i18n";

let dismissed = false;
try { dismissed = localStorage.getItem("ess_install_dismissed") === "1"; } catch { /* ignore */ }
const hidden = ref(dismissed);
function later() {
  hidden.value = true;
  try { localStorage.setItem("ess_install_dismissed", "1"); } catch { /* ignore */ }
}
</script>

<template>
  <div v-if="installEvent && !hidden" class="install" role="dialog" aria-label="Install app">
    <div class="grow">
      <strong>{{ t("Install app") }}</strong>
      <p class="small muted">Open the portal from your home screen, like any other app.</p>
    </div>
    <button class="btn sm ghost" @click="later">Not now</button>
    <button class="btn sm primary" @click="promptInstall">{{ t("Install app") }}</button>
  </div>
</template>

<style scoped>
.install { position: fixed; z-index: 45; inset-inline-end: 20px; bottom: 20px; width: min(380px, calc(100vw - 24px)); display: flex; align-items: center; gap: 10px; padding: 14px; background: var(--surface); border: 1px solid var(--line); border-radius: 14px; box-shadow: var(--shadow-pop); }
@media (max-width: 960px) { .install { bottom: 90px; inset-inline-end: 12px; } }
</style>
