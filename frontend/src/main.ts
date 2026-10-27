import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { router } from "./router";
import { useSession } from "./stores/session";
import { useUi } from "./stores/ui";
import { registerServiceWorker } from "./services/pwa";
import "./styles/tokens.css";
import "./styles/base.css";

async function start() {
  const app = createApp(App);
  const pinia = createPinia();
  app.use(pinia);
  const session = useSession();
  useUi().applyTheme();
  try {
    await session.load();
  } catch {
    window.location.href = `/login?redirect-to=${encodeURIComponent(location.pathname)}`;
    return;
  }
  app.use(router);
  app.config.errorHandler = (err) => {
    console.error(err);
    useUi().toast("Something went wrong on this page. Try again.", "error");
  };
  window.addEventListener("ess:session-expired", () => {
    window.location.href = `/login?redirect-to=${encodeURIComponent(location.pathname)}`;
  });
  app.mount("#app");
  registerServiceWorker();
}
start();
