<script setup lang="ts">
import { ref } from "vue";
import { useResource } from "@/composables/useResource";
import { Notifications } from "@/services/endpoints";
import { useUi } from "@/stores/ui";
import { useSession } from "@/stores/session";
import { lang, setLang, t } from "@/i18n";
import { enablePush, installEvent, promptInstall } from "@/services/pwa";
import PageHeader from "@/components/ui/PageHeader.vue";
import SkeletonLoader from "@/components/ui/SkeletonLoader.vue";

const ui = useUi();
const s = useSession();
const { data, loading } = useResource<any>(() => "prefs", () => Notifications.prefs());
const pushMsg = ref("");
async function toggle(e: string, c: string, v: boolean) {
  try { await Notifications.setPref(e, c, v); data.value.matrix[e][c] = v; } catch (err: any) { ui.toast(err.message, "error"); }
}
async function push() {
  try { await enablePush(s.settings.vapid_public_key); pushMsg.value = "Push notifications are on for this device."; }
  catch (e: any) { pushMsg.value = e.message; }
}
</script>

<template>
  <div class="page">
    <PageHeader :title="t('Settings')" subtitle="Personal preferences for this portal. They don't change your HR records." />
    <div class="cols-2">
      <section class="panel stack">
        <h2>Display</h2>
        <div class="field"><label for="lang">{{ t("Language") }}</label>
          <select id="lang" class="select" :value="lang" @change="setLang(($event.target as HTMLSelectElement).value as any)">
            <option value="en">English</option><option value="ar">العربية</option></select></div>
        <div class="field"><label for="theme">{{ t("Theme") }}</label>
          <select id="theme" class="select" :value="ui.theme" @change="ui.setTheme(($event.target as HTMLSelectElement).value as any)">
            <option value="system">{{ t("System") }}</option><option value="light">{{ t("Light") }}</option><option value="dark">{{ t("Dark") }}</option></select></div>
        <div v-if="installEvent"><button class="btn" @click="promptInstall">{{ t("Install app") }}</button></div>
      </section>
      <section class="panel stack">
        <h2>Push on this device</h2>
        <p class="muted small">Get a short alert when something needs you. Alerts never include amounts or personal details.</p>
        <div><button class="btn" :disabled="!s.settings.vapid_public_key" @click="push">Turn on push notifications</button></div>
        <p v-if="!s.settings.vapid_public_key" class="small muted">Your administrator hasn't enabled push yet.</p>
        <p v-if="pushMsg" class="small">{{ pushMsg }}</p>
      </section>
    </div>
    <section class="panel">
      <header><h2>{{ t("Notifications") }}</h2></header>
      <SkeletonLoader v-if="loading && !data" />
      <div class="table-wrap" v-else-if="data">
        <table class="data">
          <thead><tr><th scope="col">Topic</th><th v-for="c in data.channels" :key="c" scope="col">{{ c }}</th></tr></thead>
          <tbody><tr v-for="e in data.events" :key="e"><td>{{ t(e) }}</td>
            <td v-for="c in data.channels" :key="c"><label class="check"><input type="checkbox" :checked="data.matrix[e][c]"
              @change="toggle(e, c, ($event.target as HTMLInputElement).checked)" :aria-label="`${e} via ${c}`" /></label></td></tr></tbody>
        </table>
      </div>
    </section>
  </div>
</template>
