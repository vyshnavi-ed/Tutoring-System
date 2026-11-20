// Small shared helpers: fetch wrapper + a tiny, safe markdown renderer.
const api = {
  async get(url) { const r = await fetch(url); if (!r.ok) throw new Error(await r.text()); return r.json(); },
  async post(url, body = {}) {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
};

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function inlineMd(s) {
  return s
    .replace(/`([^`]+)`/g, (_, c) => `<code>${c}</code>`)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
}

function md(src) {
  const text = esc(src || "");
  const blocks = [];
  const withCode = text.replace(/```[a-z]*\n?([\s\S]*?)```/g, (_, code) => {
    blocks.push(`<pre><code>${code.replace(/\n$/, "")}</code></pre>`);
    return `\u0000${blocks.length - 1}\u0000`;
  });
  const out = [];
  for (const para of withCode.split(/\n{2,}/)) {
    const p = para.trim();
    if (!p) continue;
    const m = p.match(/^\u0000(\d+)\u0000$/);
    if (m) { out.push(blocks[+m[1]]); continue; }
    const lines = p.split("\n");
    if (lines.every(l => /^\s*[-*] /.test(l))) {
      out.push("<ul>" + lines.map(l => `<li>${inlineMd(l.replace(/^\s*[-*] /, ""))}</li>`).join("") + "</ul>");
    } else if (lines.every(l => /^\s*\d+\. /.test(l))) {
      out.push("<ol>" + lines.map(l => `<li>${inlineMd(l.replace(/^\s*\d+\. /, ""))}</li>`).join("") + "</ol>");
    } else if (/^#{1,3} /.test(p)) {
      const lvl = p.match(/^#+/)[0].length;
      out.push(`<h${lvl + 1}>${inlineMd(p.replace(/^#+ /, ""))}</h${lvl + 1}>`);
    } else {
      out.push(`<p>${lines.map(inlineMd).join("<br>").replace(/\u0000(\d+)\u0000/g, (_, i) => blocks[+i])}</p>`);
    }
  }
  return out.join("\n");
}

// inline markdown only (no paragraphs) for short one-line texts
function mdi(s) { return inlineMd(esc(s || "")); }

function ago(ts) {
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

const STRATEGY_LABEL = {
  level_descent: "Level descent (thesis)",
  prereq_graph: "Prerequisite graph",
  spaced_repetition: "Spaced repetition",
};
