/// <reference types="vitest" />
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

// Built assets are served by Frappe from /assets/thinknxg_ess_portal/ess/
export default defineConfig(({ command }) => ({
  plugins: [vue()],
  base: command === "build" ? "/assets/thinknxg_ess_portal/ess/" : "/",
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: {
    outDir: "../thinknxg_ess_portal/public/ess",
    emptyOutDir: true,
    manifest: true,
    target: "es2020",
    rollupOptions: {
      output: {
        manualChunks: { vue: ["vue", "vue-router", "pinia"] },
      },
    },
  },
  server: {
    port: 8080,
    proxy: {
      "^/(api|assets|files|private|socket.io|ess-sw.js)": {
        target: process.env.FRAPPE_URL || "http://127.0.0.1:8000",
        ws: true,
      },
    },
  },
  test: { environment: "happy-dom" },
}));
