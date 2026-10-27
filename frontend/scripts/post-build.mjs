// Turns the Vite index.html into the Frappe www/ess.html Jinja page and stamps the service worker version.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, "../../thinknxg_ess_portal/public/ess");
const www = resolve(here, "../../thinknxg_ess_portal/www");

let html = readFileSync(resolve(dist, "index.html"), "utf8");
const boot = `<script>window.csrf_token = "{{ csrf_token }}"; window.ess_boot = {{ boot_json }};</script>`;
html = html.replace("<!--ESS_BOOT-->", boot);
writeFileSync(resolve(www, "ess.html"), html);

const version = createHash("sha1").update(html).digest("hex").slice(0, 10);
const swPath = resolve(www, "ess-sw.js");
if (existsSync(swPath)) {
  const sw = readFileSync(swPath, "utf8").replace(/const VERSION = "[^"]*";/, `const VERSION = "${version}";`);
  writeFileSync(swPath, sw);
}
console.log(`ess.html written, service worker version ${version}`);
