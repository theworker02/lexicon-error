const state = { records: [], selected: null, query: "", language: "", severity: "" };

const queryInput = document.querySelector("#query");
const languageFilter = document.querySelector("#language-filter");
const severityFilter = document.querySelector("#severity-filter");
const resultsElement = document.querySelector("#results");
const inspector = document.querySelector("#inspector");
const stateElement = document.querySelector("#dataset-state");
const countElement = document.querySelector("#record-count");
const rowTemplate = document.querySelector("#row-template");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
}

function tone(severity) {
  const value = String(severity).toLowerCase();
  return value.includes("fatal") || value.includes("undefined") ? "fatal" : value.includes("warning") || value.includes("linter") ? "warning" : "";
}

function filteredRecords() {
  const terms = state.query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  return state.records
    .filter((entry) => (!state.language || entry.language === state.language) && (!state.severity || entry.severity === state.severity))
    .map((entry) => {
      const haystack = [entry.code, entry.title, entry.description, entry.language, entry.category].join(" ").toLowerCase();
      const rank = terms.reduce((score, term) => score + (entry.code.toLowerCase() === term ? 30 : 0) + (entry.code.toLowerCase().includes(term) ? 12 : 0) + (entry.title.toLowerCase().includes(term) ? 6 : 0) + (haystack.includes(term) ? 1 : 0), 0);
      return { entry, rank };
    })
    .filter(({ rank }) => !terms.length || rank > 0)
    .sort((a, b) => b.rank - a.rank || a.entry.language.localeCompare(b.entry.language) || a.entry.code.localeCompare(b.entry.code))
    .slice(0, 120)
    .map(({ entry }) => entry);
}

function renderResults() {
  const records = filteredRecords();
  resultsElement.replaceChildren();
  countElement.textContent = `${records.length.toLocaleString()} shown · ${state.records.length.toLocaleString()} indexed`;
  if (!records.length) {
    resultsElement.innerHTML = '<p class="empty">No diagnostics match this query.</p>';
    return;
  }
  for (const entry of records) {
    const node = rowTemplate.content.firstElementChild.cloneNode(true);
    node.classList.toggle("selected", state.selected?.id === entry.id);
    node.querySelector("code").textContent = entry.code;
    node.querySelector("strong").textContent = entry.title;
    node.querySelector("small").textContent = entry.description;
    node.querySelector(".language").textContent = entry.language;
    const severity = node.querySelector(".severity");
    severity.textContent = entry.severity;
    severity.classList.add(tone(entry.severity));
    node.addEventListener("click", () => { state.selected = entry; renderResults(); renderInspector(); });
    resultsElement.appendChild(node);
  }
}

function renderInspector() {
  const entry = state.selected;
  if (!entry) {
    inspector.innerHTML = '<div class="empty">Choose a diagnostic to inspect its root cause and repair.</div>';
    return;
  }
  const context = Array.isArray(entry.situational_context) && entry.situational_context.length ? entry.situational_context.join(" · ") : "Standard usage";
  const source = entry.source_url ? `<a class="source-link" href="${escapeHtml(entry.source_url)}" target="_blank" rel="noreferrer">Open official source ↗</a>` : "";
  inspector.innerHTML = `
    <header class="entry-header"><div><p>${escapeHtml(entry.language)} · ${escapeHtml(entry.category)}</p><h2>${escapeHtml(entry.code)}</h2><h3>${escapeHtml(entry.title)}</h3></div><span class="severity ${tone(entry.severity)}">${escapeHtml(entry.severity)}</span></header>
    <p class="description">${escapeHtml(entry.description)}</p>
    <div class="facts"><span><b>Tier:</b> ${escapeHtml(entry.tier)}</span><span><b>Frequency:</b> ${escapeHtml(entry.frequency)}</span><span><b>Context:</b> ${escapeHtml(context)}</span><span><b>Verification:</b> ${escapeHtml(entry.verification_status)}</span></div>
    <section class="comparison"><article class="code-card bad"><header>Trigger state</header><pre>${escapeHtml(entry.bad_example)}</pre></article><article class="code-card good"><header>Hardened fix</header><pre>${escapeHtml(entry.good_example)}</pre></article></section>
    ${source}`;
}

function populateFilters() {
  const populate = (element, values, label) => {
    for (const value of [...values].sort()) {
      const option = document.createElement("option");
      option.value = value; option.textContent = value; element.appendChild(option);
    }
    element.setAttribute("aria-label", label);
  };
  populate(languageFilter, new Set(state.records.map((entry) => entry.language)), "Filter by language");
  populate(severityFilter, new Set(state.records.map((entry) => entry.severity)), "Filter by severity");
}

async function readJsonl(response) {
  const text = await response.text();
  return text.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

async function loadRecords() {
  const datasetUrl = window.huggingface?.variables?.DATASET_URL;
  try {
    const response = await fetch(datasetUrl || "sample-data.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.records = datasetUrl ? await readJsonl(response) : await response.json();
    state.selected = state.records[0] ?? null;
    stateElement.textContent = datasetUrl ? "Published dataset loaded" : "Bundled 80-record preview";
  } catch (error) {
    stateElement.textContent = `Dataset unavailable: ${error.message}`;
    state.records = [];
  }
  populateFilters();
  renderResults();
  renderInspector();
}

queryInput.addEventListener("input", (event) => { state.query = event.target.value; renderResults(); });
languageFilter.addEventListener("change", (event) => { state.language = event.target.value; renderResults(); });
severityFilter.addEventListener("change", (event) => { state.severity = event.target.value; renderResults(); });
window.addEventListener("keydown", (event) => { if (event.key === "/" && document.activeElement !== queryInput) { event.preventDefault(); queryInput.focus(); } });
void loadRecords();

