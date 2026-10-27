import { defineStore } from "pinia";
import { computed, ref } from "vue";
import type { Boot } from "@/types";
import { Boot as BootApi } from "@/services/endpoints";
import { setLang } from "@/i18n";

export const useSession = defineStore("session", () => {
  const boot = ref<Boot | null>(null);
  const unread = ref(0);

  async function load() {
    const data = window.ess_boot && window.ess_boot.user ? window.ess_boot : await BootApi.get();
    boot.value = data;
    unread.value = data.unread || 0;
    let saved: string | null = null;
    try { saved = localStorage.getItem("ess_lang"); } catch { /* ignore */ }
    setLang((saved as any) || data.lang || "en");
    applyBrand();
  }

  function applyBrand() {
    const c = boot.value?.settings?.brand_color;
    if (c && /^#[0-9a-fA-F]{6}$/.test(c)) document.documentElement.style.setProperty("--brand", c);
  }

  const caps = computed(() => boot.value!.capabilities);
  const employee = computed(() => boot.value?.employee || null);
  const user = computed(() => boot.value!.user);
  const settings = computed(() => boot.value?.settings || {});
  const module = (m: string) => caps.value?.modules?.[m] !== false;
  const can = (cap?: string) => {
    if (!cap) return true;
    return cap.split("|").some((c) => Boolean((caps.value as any)?.[c]));
  };

  return { boot, unread, load, caps, employee, user, settings, module, can };
});
