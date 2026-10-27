import { computed, ref } from "vue";
import type { Lang } from "@/types";
import ar from "./ar";

export const lang = ref<Lang>("en");
export const dir = computed(() => (lang.value === "ar" ? "rtl" : "ltr"));

export function setLang(l: Lang) {
  lang.value = l;
  document.documentElement.lang = l;
  document.documentElement.dir = l === "ar" ? "rtl" : "ltr";
  try { localStorage.setItem("ess_lang", l); } catch { /* ignore */ }
}

/** English strings are the keys; Arabic falls back to English when a translation is missing. */
export function t(key: string, ...args: (string | number)[]): string {
  let s = lang.value === "ar" ? (ar[key] ?? key) : key;
  args.forEach((a, i) => { s = s.replace(`{${i}}`, String(a)); });
  return s;
}

const locale = () => (lang.value === "ar" ? "ar-OM" : "en-GB");

export function fmtDate(d?: string | null, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" }) {
  if (!d) return "—";
  const dt = new Date(d.length <= 10 ? `${d}T00:00:00` : d.replace(" ", "T"));
  return isNaN(+dt) ? d : dt.toLocaleDateString(locale(), opts);
}
export function fmtTime(d?: string | null) {
  if (!d) return "—";
  const dt = new Date(d.replace(" ", "T"));
  return isNaN(+dt) ? d.slice(11, 16) : dt.toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit" });
}
export function fmtMoney(v: number | null | undefined, currency = "OMR") {
  if (v === null || v === undefined) return "—";
  const digits = currency === "OMR" || currency === "BHD" || currency === "KWD" ? 3 : 2;
  return new Intl.NumberFormat(locale(), { style: "currency", currency, minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v);
}
export function fmtNum(v: number | null | undefined, digits = 1) {
  if (v === null || v === undefined) return "—";
  return new Intl.NumberFormat(locale(), { maximumFractionDigits: digits }).format(v);
}
export function relative(d?: string | null) {
  if (!d) return "";
  const diff = (Date.now() - new Date(d.replace(" ", "T")).getTime()) / 1000;
  const rtf = new Intl.RelativeTimeFormat(locale(), { numeric: "auto" });
  if (Math.abs(diff) < 3600) return rtf.format(-Math.round(diff / 60), "minute");
  if (Math.abs(diff) < 86400) return rtf.format(-Math.round(diff / 3600), "hour");
  return rtf.format(-Math.round(diff / 86400), "day");
}
