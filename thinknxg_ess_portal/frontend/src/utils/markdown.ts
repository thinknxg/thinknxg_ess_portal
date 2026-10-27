/** Tiny, safe markdown renderer for assistant answers: escapes HTML first, then adds a small allow-list. */
export function escapeHtml(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function inline(s: string) {
  return s
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])_(.+?)_(?=[\s.,)!?]|$)/g, "$1<em>$2</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\(((?:\/ess[^\s)]*)|(?:https:\/\/[^\s)]+))\)/g,
      (_m, t, u) => `<a href="${u}"${u.startsWith("http") ? ' target="_blank" rel="noopener noreferrer"' : ""}>${t}</a>`)
    .replace(/\[(\d{1,2})\]/g, '<sup class="cite-ref">$1</sup>');
}

export function renderMarkdown(src: string): string {
  const lines = escapeHtml(src || "").split(/\r?\n/);
  const out: string[] = [];
  let list: "ul" | "ol" | null = null;
  const close = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const raw of lines) {
    const line = raw.trimEnd();
    const ul = line.match(/^\s*[-*•]\s+(.*)$/);
    const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (ul || ol) {
      const kind = ul ? "ul" : "ol";
      if (list !== kind) { close(); out.push(`<${kind}>`); list = kind; }
      out.push(`<li>${inline((ul || ol)![1])}</li>`);
      continue;
    }
    close();
    const h = line.match(/^#{1,4}\s+(.*)$/);
    if (h) out.push(`<p class="md-h">${inline(h[1])}</p>`);
    else if (line.trim()) out.push(`<p>${inline(line)}</p>`);
  }
  close();
  return out.join("");
}
