const state = { entries: [], selected: null, query: "" };
const results = document.querySelector("#results");
const detail = document.querySelector("#detail");
const input = document.querySelector("#query");
const status = document.querySelector("#preview-status");
const template = document.querySelector("#result-template");

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
}

function matching() {
  const terms = state.query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  return state.entries
    .map((entry) => {
      const text = [entry.code, entry.title, entry.description, entry.language, entry.category].join(" ").toLowerCase();
      const score = terms.reduce((total, term) => total + (entry.code.toLowerCase() === term ? 40 : 0) + (entry.code.toLowerCase().includes(term) ? 12 : 0) + (entry.title.toLowerCase().includes(term) ? 7 : 0) + (text.includes(term) ? 1 : 0), 0);
      return { entry, score };
    })
    .filter(({ score }) => !terms.length || score > 0)
    .sort((left, right) => right.score - left.score || left.entry.code.localeCompare(right.entry.code))
    .slice(0, 12)
    .map(({ entry }) => entry);
}

function renderDetail() {
  const entry = state.selected;
  if (!entry) {
    detail.innerHTML = "<p>No matching diagnostic in this sample.</p>";
    return;
  }
  const source = entry.source_url ? '<a href="' + escapeHtml(entry.source_url) + '" target="_blank" rel="noreferrer">Open official source</a>' : "";
  detail.innerHTML = '<p class="meta">' + escapeHtml(entry.language) + ' | ' + escapeHtml(entry.category) + '</p>' +
    '<h3>' + escapeHtml(entry.code) + '</h3><h4>' + escapeHtml(entry.title) + '</h4>' +
    '<p class="description">' + escapeHtml(entry.description) + '</p>' +
    '<div class="codes"><pre class="code-block"><span class="code-label bad">Trigger</span>' + escapeHtml(entry.bad_example) + '</pre>' +
    '<pre class="code-block"><span class="code-label good">Hardened fix</span>' + escapeHtml(entry.good_example) + '</pre></div>' + source;
}

function renderResults() {
  const entries = matching();
  results.replaceChildren();
  if (!entries.length) {
    results.innerHTML = "<p class=\"empty\">No sample record matches that search.</p>";
    return;
  }
  for (const entry of entries) {
    const row = template.content.firstElementChild.cloneNode(true);
    row.classList.toggle("selected", state.selected && state.selected.id === entry.id);
    row.querySelector("code").textContent = entry.code;
    row.querySelector("strong").textContent = entry.title;
    row.querySelector("span").textContent = entry.language + " | " + entry.severity;
    row.addEventListener("click", () => { state.selected = entry; renderResults(); renderDetail(); });
    results.appendChild(row);
  }
}

async function load() {
  try {
    const response = await fetch("sample-data.json", { cache: "no-store" });
    if (!response.ok) throw new Error("sample unavailable");
    state.entries = await response.json();
    state.selected = state.entries[0] || null;
    status.textContent = state.entries.length + " local preview records";
  } catch (error) {
    status.textContent = "Preview unavailable";
  }
  renderResults();
  renderDetail();
}

input.addEventListener("input", (event) => { state.query = event.target.value; renderResults(); });
window.addEventListener("keydown", (event) => { if (event.key === "/" && document.activeElement !== input) { event.preventDefault(); input.focus(); } });
void load();

