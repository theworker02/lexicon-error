import { open, save } from "@tauri-apps/plugin-dialog";
import { useCallback, useEffect, useMemo, useRef, useState, type RefObject } from "react";
import { detectError, exportDatabase, getCoverage, getFacets, getMatrix, importContributions, searchEntries } from "./lib/api";
import type { CoverageProfile, ErrorEntry, Facets, Filters, MatrixCell } from "./types";
import logoMark from "./assets/lexiconerror-mark.svg";

const emptyFilters: Filters = { languages: [], categories: [], severities: [], frequencies: [], interactions: [] };
const fallbackFacets: Facets = { languages: [], categories: [], severities: [], frequencies: [], interactions: [], total: 0 };
type DetailTab = "overview" | "diff" | "context";

const domainGroups = [
  { label: "Systems & kernels", note: "Toolchains and low-level runtimes", languages: ["C", "C++", "Rust", "Go", "Zig", "Ada", "Fortran", "Assembly"] },
  { label: "Web & frameworks", note: "Browser, server, and app surfaces", languages: ["JavaScript", "TypeScript", "HTML", "CSS", "React", "Vue.js", "PHP", "Ruby", "Dart", "Flutter"] },
  { label: "GPU accelerators", note: "Device runtime and driver-facing faults", languages: ["CUDA", "ROCm / HIP", "OpenCL", "Vulkan"] },
  { label: "Databases & infrastructure", note: "Data engines, containers, and deployment", languages: ["SQL", "PostgreSQL", "MongoDB", "Redis", "Docker", "Kubernetes", "Terraform", "GraphQL"] },
  { label: "Managed & mobile", note: "VMs, native mobile, and app platforms", languages: ["C#", "Java", "Kotlin", "Swift", "Scala", "F#"] },
  { label: "Data & configuration", note: "Scripting, analysis, and structured formats", languages: ["Python", "R", "Bash", "Shell / Bash", "JSON", "YAML", "TOML", "XML"] },
] as const;

function severityTone(severity: string) {
  const value = severity.toLowerCase();
  if (value.includes("fatal") || value.includes("undefined behavior")) return "fatal";
  if (value.includes("warning") || value.includes("linter")) return "warning";
  return "runtime";
}

function SeverityBadge({ severity }: { severity: string }) {
  return <span className={`severity severity-${severityTone(severity)}`}>{severity}</span>;
}

function SyntaxCode({ code }: { code: string }) {
  const pattern = /(\b(?:async|await|class|const|def|else|enum|fn|for|fun|function|if|impl|import|in|let|match|module|pub|return|struct|throw|try|type|var|while)\b|\b(?:true|false|null|None|nil)\b|(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|\/\/[^\n]*|#[^\n]*)/g;
  return <code>{code.split(pattern).map((part, index) => {
    if (!part) return null;
    const className = part.startsWith("//") || part.startsWith("#") ? "token-comment" : part.startsWith("\"") || part.startsWith("'") ? "token-string" : /^(true|false|null|None|nil)$/.test(part) ? "token-literal" : pattern.test(part) ? "token-keyword" : "";
    pattern.lastIndex = 0;
    return className ? <span className={className} key={`${index}-${part}`}>{part}</span> : part;
  })}</code>;
}

function DomainTree({ available, selected, onSelect }: { available: string[]; selected: string[]; onSelect: (language: string) => void }) {
  const [open, setOpen] = useState<string | null>("GPU accelerators");
  return <section className="domain-tree" aria-label="Ecosystem filters">
    <div className="tree-heading"><span>Explore by domain</span><small>hierarchical</small></div>
    {domainGroups.map((group) => {
      const languages = group.languages.filter((language) => available.includes(language));
      if (!languages.length) return null;
      const expanded = open === group.label;
      return <div className="domain-group" key={group.label}>
        <button className="domain-trigger" onClick={() => setOpen(expanded ? null : group.label)} aria-expanded={expanded}>
          <span><b>{group.label}</b><small>{group.note}</small></span><i>{expanded ? "−" : "+"}</i>
        </button>
        {expanded && <div className="domain-items">{languages.map((language) => <button className={selected.includes(language) ? "selected" : ""} onClick={() => onSelect(language)} key={language}>{language}</button>)}</div>}
      </div>;
    })}
  </section>;
}

function CoverageView({ profiles, onBrowse }: { profiles: CoverageProfile[]; onBrowse: (language: string) => void }) {
  const indexed = profiles.filter((profile) => profile.records > 0);
  return <section className="coverage-view">
    <header><div><div className="eyebrow">Data quality</div><h1>Coverage dashboard</h1><p>Counts and tiers are generated from the local database. Source attribution does not turn a draft explanation into a verified one.</p></div><span>{indexed.length} indexed ecosystems</span></header>
    <div className="coverage-scroll"><table className="coverage-table"><thead><tr><th>Language</th><th>Records</th><th>Progress</th><th>Tier</th><th>Verified</th><th>Sources</th><th /></tr></thead><tbody>{indexed.map((profile) => <tr key={profile.language_id}>
      <td><strong>{profile.language}</strong><small>{profile.tools} tool{profile.tools === 1 ? "" : "s"}</small></td>
      <td><b>{profile.records.toLocaleString()}</b><small>target {profile.target ? profile.target.toLocaleString() : "â€”"}</small></td>
      <td><div className="coverage-progress"><span style={{ width: `${Math.min(profile.progress, 100)}%` }} /></div><small>{profile.target ? `${profile.progress.toFixed(1)}%` : "No target"}</small></td>
      <td><span className={`coverage-tier tier-${profile.tier.toLowerCase()}`}>{profile.tier}</span></td>
      <td>{profile.quality.verified.toFixed(1)}%</td><td>{profile.quality.sources.toFixed(1)}%</td>
      <td><button onClick={() => onBrowse(profile.language)}>Browse</button></td>
    </tr>)}</tbody></table></div>
    <footer>Tier gates: Comprehensive requires target count plus strong verified explanation, example, fix, and source coverage. Current registry imports remain explicitly in review until curated.</footer>
  </section>;
}

function FilterGroup({ label, values, selected, onToggle }: {
  label: string; values: string[]; selected: string[]; onToggle: (value: string) => void;
}) {
  return <section className="filter-group">
    <h3>{label}</h3>
    {values.map((value) => <label className="filter-option" key={value}>
      <input type="checkbox" checked={selected.includes(value)} onChange={() => onToggle(value)} />
      <span>{value}</span>
    </label>)}
  </section>;
}

function CodePanel({ title, code, state }: { title: string; code: string; state: "bad" | "good" }) {
  return <section className={`code-panel ${state}`}>
    <header><span className="dot" />{title}</header>
    <pre><SyntaxCode code={code} /></pre>
  </section>;
}

function CommandPalette({ open, query, results, inputRef, onClose, onQuery, onSelect, onView, onClear }: {
  open: boolean; query: string; results: ErrorEntry[]; inputRef: RefObject<HTMLInputElement | null>; onClose: () => void;
  onQuery: (value: string) => void; onSelect: (entry: ErrorEntry) => void; onView: (view: "catalog" | "matrix" | "coverage") => void; onClear: () => void;
}) {
  if (!open) return null;
  return <div className="palette-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="command-palette" role="dialog" aria-modal="true" aria-label="Global diagnostic search" onMouseDown={(event) => event.stopPropagation()}>
      <div className="palette-search"><span aria-hidden="true">⌕</span><input ref={inputRef} value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Search every offline diagnostic…" /><kbd>Esc</kbd></div>
      <div className="palette-section"><span>Navigate</span><div className="palette-actions"><button onClick={() => onView("catalog")}><b>Catalog</b><small>Browse indexed diagnostics</small></button><button onClick={() => onView("matrix")}><b>Context matrix</b><small>Compare ecosystems</small></button><button onClick={() => onView("coverage")}><b>Coverage</b><small>Inspect source quality</small></button><button onClick={onClear}><b>Clear filters</b><small>Reset the current search scope</small></button></div></div>
      <div className="palette-section palette-results"><span>Matching diagnostics</span>{results.slice(0, 7).map((entry) => <button key={entry.id} onClick={() => onSelect(entry)}><div><code>{entry.code}</code><b>{entry.title}</b></div><span>{entry.language}</span></button>)}{!results.length && <p>No diagnostics match the current query.</p>}</div>
      <footer><span>↵ Open selection</span><span>⌘K / Ctrl K Toggle</span><span>Offline index only</span></footer>
    </section>
  </div>;
}

function StateInspector({ entry }: { entry: ErrorEntry }) {
  const snapshot = entry.state_snapshot;
  if (!snapshot) return <section className="state-inspector empty-state"><header>State inspector</header><p>No deterministic state snapshot has been curated for this diagnostic yet.</p></section>;
  return <section className="state-inspector"><header>State inspector <span>{snapshot.event}</span></header><div className="state-columns"><div><h3>Stack frames</h3>{snapshot.frames.map((frame, index) => <div className="frame" key={frame}><b>{index}</b>{frame}</div>)}</div><div><h3>Variables at failure</h3>{snapshot.variables.map((variable) => <div className="variable" key={variable.name}><code>{variable.name}</code><span>{variable.value}</span><em>{variable.status}</em></div>)}</div></div></section>;
}

function MatrixView({ cells, languages, categories, onSelect }: { cells: MatrixCell[]; languages: string[]; categories: string[]; onSelect: (language: string, category: string) => void }) {
  const lookup = new Map(cells.map((cell) => [`${cell.language}:${cell.category}`, cell]));
  return <section className="matrix-view"><header><div><div className="eyebrow">Comparative mapping</div><h1>Diagnostic matrix</h1><p>Frequency-coded cross-language coverage by failure domain.</p></div><span>{cells.reduce((sum, cell) => sum + cell.count, 0)} indexed</span></header><div className="matrix-scroll"><table className="matrix-table"><thead><tr><th>Domain / language</th>{languages.map((language) => <th key={language}>{language}</th>)}</tr></thead><tbody>{categories.map((category) => <tr key={category}><th>{category}</th>{languages.map((language) => { const cell = lookup.get(`${language}:${category}`); return <td key={`${category}-${language}`}><button className={`matrix-cell ${cell ? `frequency-${cell.frequency.toLowerCase()}` : "empty-cell"}`} disabled={!cell} onClick={() => onSelect(language, category)}>{cell && <><b>{cell.count}</b><span>{cell.frequency}</span></>}</button></td>; })}</tr>)}</tbody></table></div><footer><i className="common-key" /> Common <i className="uncommon-key" /> Uncommon <i className="situational-key" /> Situational</footer></section>;
}

export default function App() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [facets, setFacets] = useState<Facets>(fallbackFacets);
  const [results, setResults] = useState<ErrorEntry[]>([]);
  const [matrix, setMatrix] = useState<MatrixCell[]>([]);
  const [coverage, setCoverage] = useState<CoverageProfile[]>([]);
  const [view, setView] = useState<"catalog" | "matrix" | "coverage">("catalog");
  const [selected, setSelected] = useState<ErrorEntry | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>("overview");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [status, setStatus] = useState("Loading offline index…");
  const searchInput = useRef<HTMLInputElement>(null);
  const paletteInput = useRef<HTMLInputElement>(null);

  const runSearch = useCallback(async () => {
    try {
      let entries = await searchEntries(query, filters);
      const detection = query.trim().length >= 3 ? await detectError(query).catch(() => null) : null;
      if (!entries.length && detection?.matches[0]) entries = await searchEntries(detection.matches[0].code, filters);
      setResults(entries);
      setSelected((current) => entries.find((entry) => entry.id === current?.id) ?? entries[0] ?? null);
      const detected = detection?.matches[0];
      setStatus(detected ? `${detected.confidence_label}: ${detected.language} ${detected.code}${detection.redacted ? " (sensitive lines redacted)" : ""}` : `${entries.length} matching diagnostic${entries.length === 1 ? "" : "s"}`);
    } catch (error) {
      setStatus(`Search unavailable: ${String(error)}`);
    }
  }, [query, filters]);

  useEffect(() => {
    getFacets().then(setFacets).catch((error) => setStatus(`Index unavailable: ${String(error)}`));
    getCoverage().then(setCoverage).catch((error) => setStatus(`Coverage unavailable: ${String(error)}`));
  }, []);
  useEffect(() => { void runSearch(); }, [runSearch]);
  useEffect(() => { getMatrix(filters).then(setMatrix).catch((error) => setStatus(`Matrix unavailable: ${String(error)}`)); }, [filters]);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault(); setPaletteOpen((open) => !open);
      }
      if (event.key === "Escape") { setPaletteOpen(false); searchInput.current?.blur(); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
  useEffect(() => { if (paletteOpen) window.setTimeout(() => paletteInput.current?.focus(), 0); }, [paletteOpen]);

  const toggle = (key: keyof Filters, value: string) => {
    setFilters((current) => ({ ...current, [key]: current[key].includes(value)
      ? current[key].filter((item) => item !== value) : [...current[key], value] }));
  };
  const activeCount = useMemo(() => Object.values(filters).flat().length, [filters]);
  const chooseExport = async () => {
    const destination = await save({ defaultPath: "lexicon-error-backup.db", filters: [{ name: "SQLite database", extensions: ["db", "sqlite"] }] });
    if (!destination) return;
    try { setStatus(`Exported backup: ${await exportDatabase(destination)}`); } catch (error) { setStatus(`Export failed: ${String(error)}`); }
  };
  const chooseImport = async () => {
    const source = await open({ directory: true, multiple: false, title: "Choose contribution directory" });
    if (!source || Array.isArray(source)) return;
    try { const count = await importContributions(source); await getFacets().then(setFacets); await getCoverage().then(setCoverage); await runSearch(); setStatus(`Imported ${count} custom diagnostic${count === 1 ? "" : "s"}`); }
    catch (error) { setStatus(`Import failed: ${String(error)}`); }
  };
  const selectEntry = (entry: ErrorEntry) => { setSelected(entry); setDetailTab("overview"); setPaletteOpen(false); setView("catalog"); };
  const changeView = (nextView: "catalog" | "matrix" | "coverage") => { setView(nextView); setPaletteOpen(false); };

  return <main className="app-shell">
    <aside className="sidebar">
      <div className="brand"><img src={logoMark} alt="" /><div><strong>LexiconError</strong><small>Universal offline encyclopedia</small></div></div>
      <button className="sidebar-command" onClick={() => setPaletteOpen(true)}><span>Search all diagnostics</span><kbd>Ctrl K</kbd></button>
      <div className="index-note"><b>{facets.total.toLocaleString()}</b><span>records in the local index</span></div>
      <DomainTree available={facets.languages} selected={filters.languages} onSelect={(value) => toggle("languages", value)} />
      <FilterGroup label="Category" values={facets.categories} selected={filters.categories} onToggle={(value) => toggle("categories", value)} />
      <FilterGroup label="Severity" values={facets.severities} selected={filters.severities} onToggle={(value) => toggle("severities", value)} />
      <FilterGroup label="Frequency" values={facets.frequencies} selected={filters.frequencies} onToggle={(value) => toggle("frequencies", value)} />
      <FilterGroup label="Interaction" values={facets.interactions} selected={filters.interactions} onToggle={(value) => toggle("interactions", value)} />
      <div className="sidebar-actions"><button className={view === "catalog" ? "active" : ""} onClick={() => changeView("catalog")}>Diagnostic catalog</button><button className={view === "matrix" ? "active" : ""} onClick={() => changeView("matrix")}>Context matrix</button><button className={view === "coverage" ? "active" : ""} onClick={() => changeView("coverage")}>Coverage dashboard</button><button onClick={() => void chooseImport()}>Import contributions</button><button onClick={() => void chooseExport()}>Export database</button></div>
    </aside>
    {view === "matrix" ? <section className="matrix-pane"><MatrixView cells={matrix} languages={facets.languages} categories={facets.categories} onSelect={(language, category) => { setFilters((current) => ({ ...current, languages: [language], categories: [category] })); setView("catalog"); }} /></section> : view === "coverage" ? <section className="coverage-pane"><CoverageView profiles={coverage} onBrowse={(language) => { setFilters((current) => ({ ...current, languages: [language] })); setView("catalog"); }} /></section> : <section className="catalog-pane">
      <header className="search-header">
        <div className="catalog-title"><div><span className="eyebrow">Offline reference</span><h1>Diagnostic catalog</h1></div><button onClick={() => setPaletteOpen(true)}>Open command palette <kbd>Ctrl K</kbd></button></div>
        <div className="search-box"><span aria-hidden="true">⌕</span><input ref={searchInput} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search errors, exception names, descriptions…" aria-label="Search diagnostics" /><kbd>Ctrl K</kbd></div>
        <div className="result-meta"><span>{status}</span>{activeCount > 0 && <button className="clear" onClick={() => setFilters(emptyFilters)}>Clear {activeCount} filter{activeCount === 1 ? "" : "s"}</button>}</div>
      </header>
      <div className="results" aria-label="Diagnostic results"><div className="result-columns"><span>Diagnostic</span><span>Domain</span><span>Severity</span></div>
        {results.map((entry) => <button className={`result-row ${entry.id === selected?.id ? "selected" : ""}`} onClick={() => selectEntry(entry)} key={entry.id}>
          <div className="result-primary"><code>{entry.code}</code><strong>{entry.title}</strong><p>{entry.description}</p></div>
          <span className="language">{entry.language}</span><SeverityBadge severity={entry.severity} />
        </button>)}
        {!results.length && <div className="empty"><strong>No diagnostics found.</strong><span>Try a broader search or clear the current filters.</span></div>}
      </div>
    </section>}
    <section className="detail-pane">
      {selected ? <article className={`detail tab-${detailTab}`}>
        <header className="detail-header"><div><div className="eyebrow">{selected.language} · {selected.category}</div><h1>{selected.code}</h1><h2>{selected.title}</h2></div><span className="severity">{selected.severity}</span></header>
        <nav className="detail-tabs" aria-label="Diagnostic detail sections"><button className={detailTab === "overview" ? "active" : ""} onClick={() => setDetailTab("overview")}>Root cause</button><button className={detailTab === "diff" ? "active" : ""} onClick={() => setDetailTab("diff")}>Bad vs. good</button><button className={detailTab === "context" ? "active" : ""} onClick={() => setDetailTab("context")}>Context</button></nav>
        <p className="description">{selected.description}</p>
        <dl className="metadata"><div><dt>Identifier</dt><dd>{selected.id}</dd></div><div><dt>Diagnostic tier</dt><dd>Level {selected.tier}</dd></div><div><dt>Frequency</dt><dd>{selected.frequency}</dd></div><div><dt>Introduced</dt><dd>{selected.version_introduced ?? "—"}</dd></div>{selected.version_deprecated && <div><dt>Deprecated</dt><dd>{selected.version_deprecated}</dd></div>}</dl>
        {(selected.situational_context.length > 0 || selected.related_errors.length > 0) && <section className="context-strip"><div><h3>Situational context</h3><p>{selected.situational_context.join(" · ") || "Standard usage"}</p></div><div><h3>Conceptual equivalents</h3><p>{selected.related_errors.join(" · ") || "None mapped yet"}</p></div></section>}
        <div className="comparison"><CodePanel title="Broken" code={selected.bad_example} state="bad" /><CodePanel title="Fixed" code={selected.good_example} state="good" /></div>
        <StateInspector entry={selected} />
        {selected.source_url && <a className="source-link" href={selected.source_url} target="_blank" rel="noreferrer">Official documentation ↗</a>}
      </article> : <div className="detail-empty">Select a diagnostic to inspect its cause and repair.</div>}
    </section>
    <CommandPalette
      open={paletteOpen}
      query={query}
      results={results}
      inputRef={paletteInput}
      onClose={() => setPaletteOpen(false)}
      onQuery={setQuery}
      onSelect={selectEntry}
      onView={changeView}
      onClear={() => { setFilters(emptyFilters); setQuery(""); }}
    />
  </main>;
}
