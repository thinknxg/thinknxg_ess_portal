import { defineStore } from "pinia";
import { ref } from "vue";

export interface Toast { id: number; kind: "success" | "error" | "info"; message: string; action?: { label: string; run: () => void } }
type Theme = "light" | "dark" | "system";

export const useUi = defineStore("ui", () => {
  const toasts = ref<Toast[]>([]);
  const paletteOpen = ref(false);
  const navOpen = ref(false);
  let theme: Theme = "system";
  try { theme = (localStorage.getItem("ess_theme") as Theme) || "system"; } catch { /* ignore */ }
  const themeRef = ref<Theme>(theme);
  let seq = 0;

  function toast(message: string, kind: Toast["kind"] = "success", action?: Toast["action"]) {
    const id = ++seq;
    toasts.value.push({ id, kind, message, action });
    setTimeout(() => dismiss(id), kind === "error" ? 7000 : 4000);
  }
  function dismiss(id: number) { toasts.value = toasts.value.filter((t) => t.id !== id); }

  function setTheme(t: Theme) {
    themeRef.value = t;
    try { localStorage.setItem("ess_theme", t); } catch { /* ignore */ }
    applyTheme();
  }
  function applyTheme() {
    const root = document.documentElement;
    if (themeRef.value === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", themeRef.value);
  }

  return { toasts, toast, dismiss, paletteOpen, navOpen, theme: themeRef, setTheme, applyTheme };
});
