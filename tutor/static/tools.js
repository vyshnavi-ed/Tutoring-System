// Explore tools: interactive things a student investigates with before being taught.
// Each tool: render(container, cfg) -> { summary(): string }  (summary is attached to the student's
// recorded answer so the teacher and the AI tutor can see what they built).
// Add a topic-specific tool by registering it in TOOLS and using its name in a pack's episode.explore.tool.

const TOOLS = {};

// ---------------------------------------------------------------- fraction strips (a "fraction wall")
TOOLS.fraction_strips = (el, cfg) => {
  const dens = cfg.strips || [2, 3, 4, 6, 8, 12];
  const rows = [];
  el.innerHTML = `
    <div class="fs-add row small"><span class="muted">Add a strip cut into</span>
      ${dens.map(d => `<button class="fs-btn" data-d="${d}">${d} parts</button>`).join("")}</div>
    <div class="fs-wall"><div class="fs-row"><div class="fs-bar"><div class="fs-seg whole">1 whole</div></div><div class="fs-label"></div><div></div></div>
    <div id="fs-rows"></div></div>
    <div class="small muted">Click pieces to shade them. Pieces line up, so you can compare lengths.</div>`;
  const box = el.querySelector("#fs-rows");
  function draw() {
    box.innerHTML = rows.map((r, i) => `
      <div class="fs-row"><div class="fs-bar">${Array.from({ length: r.d }, (_, j) =>
        `<div class="fs-seg ${r.on.has(j) ? "on" : ""}" data-r="${i}" data-j="${j}">${r.d <= 12 ? `1/${r.d}` : ""}</div>`).join("")}</div>
        <div class="fs-label">${r.on.size}/${r.d}</div>
        <button class="link fs-x" data-x="${i}" title="Remove">✕</button></div>`).join("");
    box.querySelectorAll(".fs-seg").forEach(s => s.onclick = () => {
      const r = rows[+s.dataset.r], j = +s.dataset.j;
      r.on.has(j) ? r.on.delete(j) : r.on.add(j); draw();
    });
    box.querySelectorAll(".fs-x").forEach(b => b.onclick = () => { rows.splice(+b.dataset.x, 1); draw(); });
  }
  el.querySelectorAll(".fs-btn").forEach(b => b.onclick = () => {
    if (rows.length >= (cfg.max_rows || 6)) return;
    rows.push({ d: +b.dataset.d, on: new Set() }); draw();
  });
  (cfg.preset || []).forEach(p => rows.push({ d: p.parts, on: new Set(Array.from({ length: p.shaded || 0 }, (_, i) => i)) }));
  draw();
  return { summary: () => rows.length ? "strips built: " + rows.map(r => `${r.on.size}/${r.d}`).join(", ") : "" };
};

// ---------------------------------------------------------------- read a word in context, infer its meaning
TOOLS.context_sentences = (el, cfg) => {
  const w = cfg.word || "";
  const hi = s => esc(s).replace(new RegExp(`\\b(${w}\\w*)`, "gi"), "<mark>$1</mark>");
  el.innerHTML = `<ol class="ctx">${(cfg.sentences || []).map(s => `<li>${hi(s)}</li>`).join("")}</ol>`;
  return { summary: () => "" };
};

// ---------------------------------------------------------------- a rich problem to try before any teaching
TOOLS.problem = (el, cfg) => {
  el.innerHTML = cfg.problem ? `<div class="problem md">${md(cfg.problem)}</div>` : "";
  return { summary: () => "" };
};

// ---------------------------------------------------------------- hands-on with real materials
TOOLS.real_materials = (el, cfg) => {
  el.innerHTML = `
    ${cfg.materials ? `<div class="small"><b>You need:</b> ${cfg.materials.map(esc).join(", ")}</div>` : ""}
    ${cfg.steps ? `<ol class="steps">${cfg.steps.map(s => `<li>${mdi(s)}</li>`).join("")}</ol>` : ""}
    ${cfg.safety ? `<div class="small" style="color:var(--warn)">⚠ ${esc(cfg.safety)}</div>` : ""}`;
  return { summary: () => "" };
};
