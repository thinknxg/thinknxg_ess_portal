<script setup lang="ts">
import { onMounted, onBeforeUnmount } from "vue";
import { useRoute } from "vue-router";
import EssSidebar from "./EssSidebar.vue";
import EssHeader from "./EssHeader.vue";
import EssMobileNav from "./EssMobileNav.vue";
import CommandPalette from "@/components/shell/CommandPalette.vue";
import ToastNotifications from "@/components/ui/ToastNotifications.vue";
import OfflineStatus from "@/components/shell/OfflineStatus.vue";
import InstallPrompt from "@/components/shell/InstallPrompt.vue";
import { useUi } from "@/stores/ui";
import { useSession } from "@/stores/session";
import { flush } from "@/services/offlineQueue";
import { Notifications } from "@/services/endpoints";
import { invalidate } from "@/composables/useResource";

const ui = useUi();
const session = useSession();
const route = useRoute();
let timer: number | undefined;

function onKey(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); ui.paletteOpen = !ui.paletteOpen; }
}
async function pollUnread() {
  if (!navigator.onLine || document.hidden) return;
  try { session.unread = (await Notifications.list(1)).length; } catch { /* ignore */ }
}
function onOnline() {
  flush((item) => { ui.toast(`Sent: ${item.label}`); invalidate(""); });
}
onMounted(() => {
  window.addEventListener("keydown", onKey);
  window.addEventListener("online", onOnline);
  onOnline();
  timer = window.setInterval(pollUnread, 60_000);
});
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKey);
  window.removeEventListener("online", onOnline);
  window.clearInterval(timer);
});
</script>

<template>
  <a class="skip" href="#main">Skip to content</a>
  <div class="shell" :class="{ 'nav-open': ui.navOpen }">
    <EssSidebar />
    <div class="scrim" v-if="ui.navOpen" @click="ui.navOpen = false" />
    <div class="main-col">
      <EssHeader />
      <OfflineStatus />
      <main id="main" tabindex="-1">
        <RouterView v-slot="{ Component }">
          <component :is="Component" :key="route.fullPath.split('?')[0]" />
        </RouterView>
      </main>
    </div>
    <EssMobileNav />
  </div>
  <CommandPalette />
  <InstallPrompt />
  <ToastNotifications />
</template>

<style scoped>
.skip { position: absolute; inset-inline-start: 8px; top: -40px; background: var(--brand); color: #fff; padding: 8px 12px; border-radius: 6px; z-index: 100; }
.skip:focus { top: 8px; }
.shell { display: grid; grid-template-columns: var(--rail) minmax(0, 1fr); min-height: 100vh; }
.main-col { min-width: 0; display: flex; flex-direction: column; }
main { flex: 1; outline: none; }
.scrim { display: none; }
@media (max-width: 960px) {
  .shell { grid-template-columns: minmax(0, 1fr); }
  .scrim { display: block; position: fixed; inset: 0; background: rgba(10, 20, 17, .45); z-index: 30; }
}
</style>
