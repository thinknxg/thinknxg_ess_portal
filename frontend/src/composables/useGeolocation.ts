import { ref } from "vue";

export interface Fix { latitude: number; longitude: number; accuracy: number; at: number }
export type GeoState = "idle" | "locating" | "ok" | "denied" | "unavailable" | "timeout" | "insecure";

const MESSAGES: Record<string, string> = {
  insecure: "Location only works over a secure (https) connection. Open the portal from its https address.",
  unavailable: "This device couldn't determine its location. Turn on location services and try again.",
  denied: "Location is blocked for this site. Allow it in your browser's site settings (the icon next to the address), then try again.",
  timeout: "Getting your location took too long. Move near a window or outdoors and try again.",
};

/**
 * Browser geolocation with the best fix inside a time budget. The fix is only a claim from the device:
 * the server re-validates distance, accuracy and risk on every punch.
 */
export function useGeolocation() {
  const state = ref<GeoState>("idle");
  const fix = ref<Fix | null>(null);
  const message = ref("");
  let watchId: number | null = null;

  function stop() {
    if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    watchId = null;
  }

  async function permission(): Promise<string | null> {
    try {
      const p = await (navigator as any).permissions?.query({ name: "geolocation" });
      return p?.state || null;
    } catch { return null; }
  }

  function fail(s: GeoState) {
    state.value = s;
    message.value = MESSAGES[s] || "";
    return null;
  }

  /** Keep the most accurate reading until it is good enough or the budget runs out. */
  async function locate(targetAccuracy = 50, budgetMs = 12000): Promise<Fix | null> {
    stop();
    if (typeof window !== "undefined" && !window.isSecureContext) return fail("insecure");
    if (!("geolocation" in navigator)) return fail("unavailable");
    if ((await permission()) === "denied") return fail("denied");
    state.value = "locating";
    message.value = "";
    return new Promise((resolve) => {
      let best: Fix | null = null;
      const done = (r: Fix | null) => { stop(); clearTimeout(timer); resolve(r); };
      const timer = window.setTimeout(() => {
        if (best) { fix.value = best; state.value = "ok"; done(best); } else { done(fail("timeout")); }
      }, budgetMs);
      watchId = navigator.geolocation.watchPosition((pos) => {
        const f = { latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: Math.round(pos.coords.accuracy), at: Date.now() };
        if (!best || f.accuracy < best.accuracy) best = f;
        fix.value = best;
        if (best.accuracy <= targetAccuracy) { state.value = "ok"; done(best); }
      }, (err) => {
        done(fail(err.code === 1 ? "denied" : err.code === 3 ? "timeout" : "unavailable"));
      }, { enableHighAccuracy: true, maximumAge: 0, timeout: budgetMs });
    });
  }

  const fresh = (maxAgeMs = 30000) => !!fix.value && Date.now() - fix.value.at < maxAgeMs;
  return { state, fix, message, locate, stop, fresh };
}
