import { ref } from "vue";
import { Notifications } from "./endpoints";

export const updateReady = ref(false);
export const installEvent = ref<any>(null);
let registration: ServiceWorkerRegistration | null = null;

export async function registerServiceWorker() {
  if (!("serviceWorker" in navigator) || import.meta.env.DEV) return;
  try {
    registration = await navigator.serviceWorker.register("/ess-sw.js", { scope: "/ess" });
    registration.addEventListener("updatefound", () => {
      const nw = registration!.installing;
      nw?.addEventListener("statechange", () => {
        if (nw.state === "installed" && navigator.serviceWorker.controller) updateReady.value = true;
      });
    });
    navigator.serviceWorker.addEventListener("message", (e) => {
      if (e.data?.type === "navigate" && e.data.url) window.location.assign(e.data.url);
    });
  } catch (e) {
    console.warn("Service worker registration failed", e);
  }
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    installEvent.value = e;
  });
}

export function applyUpdate() {
  registration?.waiting?.postMessage({ type: "skip-waiting" });
  window.location.reload();
}

export async function promptInstall() {
  const e = installEvent.value;
  if (!e) return false;
  e.prompt();
  const choice = await e.userChoice;
  installEvent.value = null;
  return choice?.outcome === "accepted";
}

function urlB64ToUint8Array(base64: string) {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const raw = atob((base64 + padding).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export async function enablePush(vapidKey: string) {
  if (!registration || !("PushManager" in window)) throw new Error("Push notifications aren't supported on this device.");
  const perm = await Notification.requestPermission();
  if (perm !== "granted") throw new Error("Notifications are blocked in your browser settings.");
  const sub = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlB64ToUint8Array(vapidKey) });
  await Notifications.subscribe(sub.toJSON());
}
