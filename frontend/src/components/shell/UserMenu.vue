<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useSession } from "@/stores/session";
import { t } from "@/i18n";
import EssIcon from "@/components/ui/EssIcon.vue";
import Avatar from "@/components/ui/Avatar.vue";
import { clearQueueOnLogout } from "@/services/offlineQueue";

const s = useSession();
const open = ref(false);
const root = ref<HTMLElement | null>(null);
function outside(e: MouseEvent) { if (root.value && !root.value.contains(e.target as Node)) open.value = false; }
onMounted(() => document.addEventListener("click", outside));
onBeforeUnmount(() => document.removeEventListener("click", outside));

async function logout() {
  clearQueueOnLogout();
  if ("caches" in window) { for (const k of await caches.keys()) await caches.delete(k); }
  await fetch("/api/method/logout", { method: "POST", credentials: "same-origin", headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" } });
  window.location.href = "/login";
}
</script>

<template>
  <div class="menu" ref="root">
    <button class="trigger" @click="open = !open" :aria-expanded="open" aria-haspopup="menu">
      <Avatar :name="s.user.full_name" :image="s.employee?.image || s.user.image" :size="32" />
    </button>
    <div v-if="open" class="pop" role="menu" @keydown.esc="open = false">
      <div class="who">
        <strong>{{ s.user.full_name }}</strong>
        <span class="muted small">{{ s.employee?.designation || s.user.email }}</span>
      </div>
      <RouterLink role="menuitem" to="/profile" class="mi" @click="open = false"><EssIcon name="user" :size="18" />{{ t("My profile") }}</RouterLink>
      <RouterLink role="menuitem" to="/settings" class="mi" @click="open = false"><EssIcon name="gear" :size="18" />{{ t("Settings") }}</RouterLink>
      <a role="menuitem" href="/app" class="mi" v-if="s.can('hr|admin')"><EssIcon name="chart" :size="18" />Desk</a>
      <button role="menuitem" class="mi" @click="logout"><EssIcon name="logout" :size="18" />{{ t("Sign out") }}</button>
    </div>
  </div>
</template>

<style scoped>
.menu { position: relative; }
.trigger { border: 0; background: none; padding: 2px; border-radius: 50%; cursor: pointer; }
.pop { position: absolute; inset-inline-end: 0; top: 44px; width: 240px; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; box-shadow: var(--shadow-pop); padding: 6px; z-index: 50; }
.who { display: flex; flex-direction: column; padding: 10px; border-bottom: 1px solid var(--line); margin-bottom: 4px; }
.mi { display: flex; align-items: center; gap: 10px; width: 100%; min-height: 38px; padding: 0 10px; border: 0; background: none; border-radius: 8px; color: var(--ink); text-decoration: none; cursor: pointer; font-size: var(--fs-sm); text-align: start; }
.mi:hover { background: var(--surface-2); }
</style>
