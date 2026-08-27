import { open, save } from "@tauri-apps/plugin-dialog";
import { getVersion } from "@tauri-apps/api/app";
import { useCallback, useEffect, useMemo, useRef, useState, type RefObject } from "react";
import {
  detectError,
  exportDatabase,
  getCoverage,
  getEntryInsights,
  getErrorMetadata,
  getFacets,
  getMatrix,
  importContributions,
  searchEntries,
} from "./lib/api";
import type {
  CoverageProfile,
  EntryInsights,
  ErrorEntry,
  ErrorMetadata,
  Facets,
  Filters,
  MatrixCell,
  RelatedEntry,
} from "./types";
import logoMark from "./assets/lexiconerror-mark.svg";

const emptyFilters: Filters = { languages: [], categories: [], severities: [], frequencies: [], interactions: [] };
const fallbackFacets: Facets = { languages: [], categories: [], severities: [], frequencies: [], interactions: [], total: 0 };
const frequencyOrder = ["Common", "Uncommon", "Rare", "Situational"] as const;
type DetailTab = "overview" | "repair" | "context" | "state";
type AppView = "catalog" | "matrix" | "coverage";

const domainGroups = [
  { label: "Systems & kernels", note: "Toolchains and low-level runtimes", languages: ["C", "C++", "Rust", "Go", "Zig", "Ada", "Fortran", "Assembly"] },
  { label: "Web & frameworks", note: "Browser, server, and app surfaces", languages: ["JavaScript", "TypeScript", "HTML", "CSS", "React", "Vue.js", "PHP", "Ruby", "Dart", "Flutter"] },
  { label: "GPU accelerators", note: "Device runtime and driver-facing faults", languages: ["CUDA", "ROCm / HIP", "OpenCL", "Vulkan"] },
  { label: "Databases & infrastructure", note: "Data engines, containers, and deployment", languages: ["SQL", "PostgreSQL", "MongoDB", "Redis", "Docker", "Kubernetes", "Terraform", "GraphQL"] },
  { label: "Managed & mobile", note: "VMs, native mobile, and app platforms", languages: ["C#", "Java", "Kotlin", "Swift", "Scala", "F#"] },
  { label: "Data & configuration", note: "Scripting, analysis, and structured formats", languages: ["Python", "R", "Bash", "Shell / Bash", "JSON", "YAML", "TOML", "XML"] },
] as const;

const frequencyCopy: Record<string, { title: string; description: string }> = {
  Common: { title: "Expected in everyday development", description: "A recurring failure mode in ordinary code and common workflows." },
  Uncommon: { title: "Occasional in normal projects", description: "Usually requires a particular API, state, or language feature." },
  Rare: { title: "Infrequent in typical projects", description: "Often tied to unusual combinations or less-traveled toolchain paths." },
  Situational: { title: "Environment or condition dependent", description: "Manifests under specific flags, architectures, loads, or runtime states." },
};

function severityTone(severity: string) {
  const value = severity.toLowerCase();
  if (value.includes("fatal") || value.includes("undefined behavior")) return "fatal";
  if (value.includes("warning") || value.includes("linter")) return "warning";
  return "runtime";
}

function formatLabel(value: string) {
  return value.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
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
  const [expandedGroup, setExpandedGroup] = useState<string | null>("Systems & kernels");
  return <section className="domain-tree" aria-label="Ecosystem filters">
    <div className="tree-heading"><span>Explore by domain</span><small>{available.length} ecosystems</small></div>
    {domainGroups.map((group) => {
      const languages = group.languages.filter((language) => available.includes(language));
      if (!languages.length) return null;
      const expanded = expandedGroup === group.label;
      const selectedCount = languages.filter((language) => selected.includes(language)).length;
      return <div className="domain-group" key={group.label}>
        <button className="domain-trigger" onClick={() => setExpandedGroup(expanded ? null : group.label)} aria-expanded={expanded}>
          <span><b>{group.label}</b><small>{selectedCount ? `${selectedCount} selected` : group.note}</small></span><i>{expanded ? "-" : "+"}</i>
        </button>
        {expanded && <div className="domain-items">{languages.map((language) => <button className={selected.includes(language) ? "selected" : ""} onClick={() => onSelect(language)} key={language}>{language}</button>)}</div>}
      </div>;
    })}
  </section>;
}

function FilterGroup({ label, values, selected, onToggle }: { label: string; values: string[]; selected: string[]; onToggle: (value: string) => void }) {
  return <section className="filter-group">
    <h3>{label}<span>{selected.length || ""}</span></h3>
    {values.map((value) => <label className="filter-option" key={value}>
      <input type="checkbox" checked={selected.includes(value)} onChange={() => onToggle(value)} /><span>{value}</span>
    </label>)}
  </section>;
}

function CodePanel({ title, code, state }: { title: string; code: string; state: "bad" | "good" }) {
  return <section className={`code-panel ${state}`}>
    <header><span className="dot" />{title}<small>{state === "bad" ? "Trigger state" : "Hardened state"}</small></header>
    <pre><SyntaxCode code={code} /></pre>
  </section>;
}

function FrequencyProfile({ entry, insights, onFilter }: { entry: ErrorEntry; insights: EntryInsights | null; onFilter: (frequency: string) => void }) {
  const copy = frequencyCopy[entry.frequency] ?? frequencyCopy.Common;
  const maxCount = Math.max(...(insights?.frequency_distribution.map((bucket) => bucket.count) ?? [1]), 1);
  return <section className="analytics-card frequency-profile">
    <header><div><span className="section-kicker">Experience profile</span><h3>{copy.title}</h3></div><span className={`frequency-badge frequency-${entry.frequency.toLowerCase()}`}>{entry.frequency}</span></header>
    <p>{copy.description}</p>
    <div className="likelihood-scale" aria-label={`Curated experience likelihood: ${entry.frequency}`}>
      {frequencyOrder.map((level) => <button key={level} className={level === entry.frequency ? "active" : ""} onClick={() => onFilter(level)} aria-pressed={level === entry.frequency}><span /><small>{level}</small></button>)}
    </div>
    <div className="frequency-bars" aria-label={`${entry.language} catalog frequency distribution`}>
      {(insights?.frequency_distribution ?? []).map((bucket) => <button key={bucket.label} onClick={() => onFilter(bucket.label)} title={`Show ${bucket.label.toLowerCase()} ${entry.language} diagnostics`}>
        <span className="bar-value">{bucket.count.toLocaleString()}</span><i style={{ height: `${Math.max((bucket.count / maxCount) * 100, bucket.count ? 8 : 2)}%` }} /><small>{bucket.label}</small>
      </button>)}
    </div>
    <footer>Bars show indexed {entry.language} diagnostics by curated frequency, not measured incident probability.</footer>
  </section>;
}

function CategoryDistribution({ entry, insights, onFilter }: { entry: ErrorEntry; insights: EntryInsights | null; onFilter: (category: string) => void }) {
  const maxCount = Math.max(...(insights?.category_distribution.map((bucket) => bucket.count) ?? [1]), 1);
  return <section className="analytics-card category-profile">
    <header><div><span className="section-kicker">Ecosystem context</span><h3>{entry.language} failure domains</h3></div><span>{insights?.language_total.toLocaleString() ?? "-"} records</span></header>
    <div className="horizontal-bars">
      {(insights?.category_distribution ?? []).map((bucket) => <button key={bucket.label} className={bucket.label === entry.category ? "active" : ""} onClick={() => onFilter(bucket.label)}>
        <span>{bucket.label}</span><i><b style={{ width: `${Math.max((bucket.count / maxCount) * 100, 3)}%` }} /></i><strong>{bucket.count.toLocaleString()}</strong>
      </button>)}
    </div>
  </section>;
}

function StateInspector({ entry }: { entry: ErrorEntry }) {
  const snapshot = entry.state_snapshot;
  if (!snapshot) return <section className="state-inspector empty-state"><header>Failure state</header><p>No deterministic state snapshot has been curated for this diagnostic yet.</p></section>;
  return <section className="state-inspector"><header>Failure state <span>{snapshot.event}</span></header><div className="state-columns"><div><h3>Stack frames</h3>{snapshot.frames.map((frame, index) => <div className="frame" key={frame}><b>{index}</b>{frame}</div>)}</div><div><h3>Variables at failure</h3>{snapshot.variables.map((variable) => <div className="variable" key={variable.name}><code>{variable.name}</code><span>{variable.value}</span><em>{variable.status}</em></div>)}</div></div></section>;
}

function RelatedDiagnostics({ entries, onSelect }: { entries: RelatedEntry[]; onSelect: (entry: RelatedEntry) => void }) {
  return <section className="related-section"><header><span className="section-kicker">Cross-language mapping</span><h3>Related diagnostics</h3></header>
    {entries.length ? <div className="related-list">{entries.map((entry) => <button key={entry.id} onClick={() => onSelect(entry)}>
      <span className="related-language">{entry.language}</span><code>{entry.code}</code><strong>{entry.title}</strong><small>{entry.category} / {entry.frequency}</small>
    </button>)}</div> : <p className="muted-empty">No resolvable related diagnostics are mapped yet.</p>}
  </section>;
}

function CommandPalette({ open, query, results, inputRef, onClose, onQuery, onSelect, onView, onClear }: {
  open: boolean; query: string; results: ErrorEntry[]; inputRef: RefObject<HTMLInputElement | null>; onClose: () => void;
  onQuery: (value: string) => void; onSelect: (entry: ErrorEntry) => void; onView: (view: AppView) => void; onClear: () => void;
}) {
  if (!open) return null;
  return <div className="palette-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="command-palette" role="dialog" aria-modal="true" aria-label="Global diagnostic search" onMouseDown={(event) => event.stopPropagation()}>
      <div className="palette-search"><span aria-hidden="true">Search</span><input ref={inputRef} value={query} onChange={(event) => onQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && results[0]) { event.preventDefault(); onSelect(results[0]); } }} placeholder="Search every offline diagnostic..." /><kbd>Esc</kbd></div>
      <div className="palette-section"><span>Navigate</span><div className="palette-actions"><button onClick={() => onView("catalog")}><b>Catalog</b><small>Browse indexed diagnostics</small></button><button onClick={() => onView("matrix")}><b>Context matrix</b><small>Compare ecosystems</small></button><button onClick={() => onView("coverage")}><b>Coverage</b><small>Inspect source quality</small></button><button onClick={onClear}><b>Clear filters</b><small>Reset the current search scope</small></button></div></div>
      <div className="palette-section palette-results"><span>Matching diagnostics</span>{results.slice(0, 7).map((entry) => <button key={entry.id} onClick={() => onSelect(entry)}><div><code>{entry.code}</code><b>{entry.title}</b></div><span>{entry.language}</span></button>)}{!results.length && <p>No diagnostics match the current query.</p>}</div>
      <footer><span>Enter opens selection</span><span>Ctrl K toggles</span><span>Offline index only</span></footer>
    </section>
  </div>;
}

function MatrixView({ cells, languages, categories, onSelect }: { cells: MatrixCell[]; languages: string[]; categories: string[]; onSelect: (language: string, category: string) => void }) {
  const lookup = new Map(cells.map((cell) => [`${cell.language}:${cell.category}`, cell]));
  return <section className="matrix-view"><header><div><div className="eyebrow">Comparative mapping</div><h1>Diagnostic matrix</h1><p>Explore frequency-coded coverage across languages and failure domains.</p></div><span>{cells.reduce((sum, cell) => sum + cell.count, 0).toLocaleString()} indexed</span></header><div className="matrix-scroll"><table className="matrix-table"><thead><tr><th>Domain / language</th>{languages.map((language) => <th key={language}>{language}</th>)}</tr></thead><tbody>{categories.map((category) => <tr key={category}><th>{category}</th>{languages.map((language) => { const cell = lookup.get(`${language}:${category}`); return <td key={`${category}-${language}`}><button className={`matrix-cell ${cell ? `frequency-${cell.frequency.toLowerCase()}` : "empty-cell"}`} disabled={!cell} onClick={() => onSelect(language, category)}>{cell && <><b>{cell.count}</b><span>{cell.frequency}</span></>}</button></td>; })}</tr>)}</tbody></table></div><footer><i className="common-key" /> Common <i className="uncommon-key" /> Uncommon <i className="rare-key" /> Rare <i className="situational-key" /> Situational</footer></section>;
}

function CoverageView({ profiles, onBrowse }: { profiles: CoverageProfile[]; onBrowse: (language: string) => void }) {
  const indexed = profiles.filter((profile) => profile.records > 0);
  return <section className="coverage-view"><header><div><div className="eyebrow">Data quality</div><h1>Coverage dashboard</h1><p>Inspect catalog breadth, verification state, and source completeness before relying on a record.</p></div><span>{indexed.length} indexed ecosystems</span></header><div className="coverage-scroll"><table className="coverage-table"><thead><tr><th>Language</th><th>Records</th><th>Progress</th><th>Tier</th><th>Verified</th><th>Sources</th><th /></tr></thead><tbody>{indexed.map((profile) => <tr key={profile.language_id}><td><strong>{profile.language}</strong><small>{profile.tools} tool{profile.tools === 1 ? "" : "s"}</small></td><td><b>{profile.records.toLocaleString()}</b><small>target {profile.target ? profile.target.toLocaleString() : "-"}</small></td><td><div className="coverage-progress"><span style={{ width: `${Math.min(profile.progress, 100)}%` }} /></div><small>{profile.target ? `${profile.progress.toFixed(1)}%` : "No target"}</small></td><td><span className={`coverage-tier tier-${profile.tier.toLowerCase()}`}>{profile.tier}</span></td><td>{profile.quality.verified.toFixed(1)}%</td><td>{profile.quality.sources.toFixed(1)}%</td><td><button onClick={() => onBrowse(profile.language)}>Browse</button></td></tr>)}</tbody></table></div><footer>Registry imports remain marked for review until their explanations and examples are curated.</footer></section>;
}

export default function App() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [facets, setFacets] = useState<Facets>(fallbackFacets);
  const [results, setResults] = useState<ErrorEntry[]>([]);
  const [matrix, setMatrix] = useState<MatrixCell[]>([]);
  const [coverage, setCoverage] = useState<CoverageProfile[]>([]);
  const [view, setView] = useState<AppView>("catalog");
  const [selected, setSelected] = useState<ErrorEntry | null>(null);
  const [metadata, setMetadata] = useState<ErrorMetadata | null>(null);
  const [insights, setInsights] = useState<EntryInsights | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>("overview");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [status, setStatus] = useState("Loading offline index...");
  const [appVersion, setAppVersion] = useState("1.0.0");
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
    } catch (error) { setStatus(`Search unavailable: ${String(error)}`); }
  }, [query, filters]);

  useEffect(() => {
    getFacets().then(setFacets).catch((error) => setStatus(`Index unavailable: ${String(error)}`));
    getCoverage().then(setCoverage).catch((error) => setStatus(`Coverage unavailable: ${String(error)}`));
    getVersion().then(setAppVersion).catch(() => undefined);
  }, []);
  useEffect(() => { void runSearch(); }, [runSearch]);
  useEffect(() => { getMatrix(filters).then(setMatrix).catch((error) => setStatus(`Matrix unavailable: ${String(error)}`)); }, [filters]);
  useEffect(() => {
    let active = true;
    if (!selected) { setMetadata(null); setInsights(null); return; }
    setMetadata(null); setInsights(null);
    void Promise.all([getErrorMetadata(selected.id), getEntryInsights(selected.id)]).then(([nextMetadata, nextInsights]) => {
      if (active) { setMetadata(nextMetadata); setInsights(nextInsights); }
    }).catch((error) => { if (active) setStatus(`Diagnostic context unavailable: ${String(error)}`); });
    return () => { active = false; };
  }, [selected?.id]);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setPaletteOpen((open) => !open); }
      if (event.key === "Escape") { setPaletteOpen(false); searchInput.current?.blur(); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
  useEffect(() => { if (paletteOpen) window.setTimeout(() => paletteInput.current?.focus(), 0); }, [paletteOpen]);

  const activeCount = useMemo(() => Object.values(filters).flat().length, [filters]);
  const selectedCoverage = useMemo(() => coverage.find((profile) => profile.language === selected?.language) ?? null, [coverage, selected?.language]);
  const toggle = (key: keyof Filters, value: string) => setFilters((current) => ({ ...current, [key]: current[key].includes(value) ? current[key].filter((item) => item !== value) : [...current[key], value] }));
  const changeView = (nextView: AppView) => { setView(nextView); setPaletteOpen(false); };
  const selectEntry = (entry: ErrorEntry) => { setSelected(entry); setDetailTab("overview"); setPaletteOpen(false); setView("catalog"); };
  const applyCatalogFilter = (key: keyof Filters, value: string, language?: string) => {
    setQuery("");
    setFilters({ ...emptyFilters, languages: key === "languages" ? [value] : language ? [language] : [], [key]: [value] });
    setView("catalog");
  };
  const openRelated = async (related: RelatedEntry) => {
    try {
      const entries = await searchEntries(related.code, { ...emptyFilters, languages: [related.language] });
      const target = entries.find((entry) => entry.id === related.id);
      if (!target) throw new Error("Related diagnostic is no longer in the local index");
      setQuery(related.code); setFilters({ ...emptyFilters, languages: [related.language] }); selectEntry(target);
    } catch (error) { setStatus(`Related diagnostic unavailable: ${String(error)}`); }
  };
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

  return <main className="app-shell">
    <aside className="sidebar">
      <div className="brand"><img src={logoMark} alt="" /><div><strong>LexiconError <em>v{appVersion}</em></strong><small>Offline diagnostic intelligence</small></div></div>
      <button className="sidebar-command" onClick={() => setPaletteOpen(true)}><span>Search everything</span><kbd>Ctrl K</kbd></button>
      <nav className="primary-navigation" aria-label="Primary views">
        <button className={view === "catalog" ? "active" : ""} onClick={() => changeView("catalog")}><span>Catalog</span><small>Search and diagnose</small></button>
        <button className={view === "matrix" ? "active" : ""} onClick={() => changeView("matrix")}><span>Context matrix</span><small>Compare ecosystems</small></button>
        <button className={view === "coverage" ? "active" : ""} onClick={() => changeView("coverage")}><span>Coverage</span><small>Review data quality</small></button>
      </nav>
      <div className="index-note"><b>{facets.total.toLocaleString()}</b><span>records indexed locally</span><small>Zero network latency</small></div>
      <DomainTree available={facets.languages} selected={filters.languages} onSelect={(value) => toggle("languages", value)} />
      <FilterGroup label="Category" values={facets.categories} selected={filters.categories} onToggle={(value) => toggle("categories", value)} />
      <FilterGroup label="Severity" values={facets.severities} selected={filters.severities} onToggle={(value) => toggle("severities", value)} />
      <FilterGroup label="Frequency" values={facets.frequencies} selected={filters.frequencies} onToggle={(value) => toggle("frequencies", value)} />
      <FilterGroup label="Interaction" values={facets.interactions} selected={filters.interactions} onToggle={(value) => toggle("interactions", value)} />
      <div className="sidebar-actions"><button onClick={() => void chooseImport()}>Import contributions</button><button onClick={() => void chooseExport()}>Export database</button></div>
    </aside>

    {view === "matrix" ? <section className="matrix-pane"><MatrixView cells={matrix} languages={facets.languages} categories={facets.categories} onSelect={(language, category) => { setFilters({ ...emptyFilters, languages: [language], categories: [category] }); setView("catalog"); }} /></section>
      : view === "coverage" ? <section className="coverage-pane"><CoverageView profiles={coverage} onBrowse={(language) => applyCatalogFilter("languages", language)} /></section>
      : <section className="catalog-pane">
        <header className="search-header">
          <div className="catalog-title"><div><span className="eyebrow">Universal error index</span><h1>Diagnostic catalog</h1></div><button onClick={() => setPaletteOpen(true)}>Command palette <kbd>Ctrl K</kbd></button></div>
          <div className="search-box"><span aria-hidden="true">Search</span><input ref={searchInput} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Paste an error or search by code, message, or cause..." aria-label="Search diagnostics" /><kbd>Ctrl K</kbd></div>
          <div className="result-meta"><span>{status}</span>{activeCount > 0 && <button className="clear" onClick={() => setFilters(emptyFilters)}>Clear {activeCount} filter{activeCount === 1 ? "" : "s"}</button>}</div>
        </header>
        <div className="results" aria-label="Diagnostic results"><div className="result-columns"><span>Diagnostic</span><span>Frequency</span><span>Language</span></div>
          {results.map((entry) => <button className={`result-row ${entry.id === selected?.id ? "selected" : ""}`} onClick={() => selectEntry(entry)} key={entry.id}>
            <div className="result-primary"><div><code>{entry.code}</code><SeverityBadge severity={entry.severity} /></div><strong>{entry.title}</strong><p>{entry.description}</p></div>
            <span className={`result-frequency frequency-${entry.frequency.toLowerCase()}`}><i />{entry.frequency}</span><span className="language">{entry.language}<small>{entry.category}</small></span>
          </button>)}
          {!results.length && <div className="empty"><strong>No diagnostics found.</strong><span>Try a broader search or clear the current filters.</span></div>}
        </div>
      </section>}

    <section className="detail-pane">
      {selected ? <article className="detail">
        <header className="detail-header"><div className="detail-identity"><div className="eyebrow">{selected.language} / {selected.category}</div><div className="code-line"><h1>{selected.code}</h1><span className={`verification verification-${metadata?.verification_status.toLowerCase().replaceAll(" ", "-") ?? "loading"}`}>{metadata?.verification_status ?? "Loading context"}</span></div><h2>{selected.title}</h2><p>{metadata?.canonical_message ?? "Loading canonical diagnostic signature..."}</p></div><SeverityBadge severity={selected.severity} /></header>
        <div className="quick-facts">
          <div><span>Experience</span><strong>{selected.frequency}</strong><small>curated likelihood</small></div>
          <div><span>Failure layer</span><strong>Level {selected.tier}</strong><small>{selected.tier === 1 ? "surface" : selected.tier === 2 ? "runtime" : selected.tier === 3 ? "toolchain" : "situational"}</small></div>
          <div><span>Ecosystem cohort</span><strong>{insights?.category_total.toLocaleString() ?? "-"}</strong><small>{selected.category.toLowerCase()} records</small></div>
          <div><span>Coverage tier</span><strong>{selectedCoverage?.tier ?? "-"}</strong><small>{selectedCoverage ? `${selectedCoverage.quality.sources.toFixed(0)}% sourced` : "loading"}</small></div>
        </div>
        <nav className="detail-tabs" aria-label="Diagnostic detail sections">
          {(["overview", "repair", "context", "state"] as DetailTab[]).map((tab) => <button key={tab} className={detailTab === tab ? "active" : ""} onClick={() => setDetailTab(tab)}>{tab === "overview" ? "Overview" : tab === "repair" ? "Trigger vs. fix" : tab === "context" ? "Context & relations" : "Failure state"}</button>)}
        </nav>

        {detailTab === "overview" && <div className="detail-section overview-section">
          <section className="root-cause"><span className="section-kicker">Root cause</span><h3>Why this happens</h3><p>{selected.description}</p>{metadata?.causes.length ? <div className="cause-list">{metadata.causes.map((cause) => cause.id && <span key={cause.id}>{formatLabel(cause.id)}<small>{cause.likelihood}</small></span>)}</div> : null}</section>
          <div className="analytics-grid"><FrequencyProfile entry={selected} insights={insights} onFilter={(value) => applyCatalogFilter("frequencies", value, selected.language)} /><CategoryDistribution entry={selected} insights={insights} onFilter={(value) => applyCatalogFilter("categories", value, selected.language)} /></div>
        </div>}

        {detailTab === "repair" && <div className="detail-section repair-section">
          <div className="section-intro"><span className="section-kicker">Remediation diff</span><h3>Compare the failing and hardened states</h3><p>The examples are stored with the diagnostic and remain available offline.</p></div>
          <div className="comparison"><CodePanel title="Broken example" code={selected.bad_example} state="bad" /><CodePanel title="Fixed example" code={selected.good_example} state="good" /></div>
          {metadata?.explanation_of_example && <p className="example-explanation">{metadata.explanation_of_example}</p>}
        </div>}

        {detailTab === "context" && <div className="detail-section context-section">
          <div className="context-grid"><section><span className="section-kicker">Trigger conditions</span><h3>When it appears</h3><div className="tag-list">{(metadata?.when_it_occurs.length ? metadata.when_it_occurs : selected.situational_context).map((item) => <span key={item}>{item}</span>)}{!selected.situational_context.length && !metadata?.when_it_occurs.length && <p className="muted-empty">No situational triggers have been curated.</p>}</div></section><section><span className="section-kicker">Interaction types</span><h3>Systems involved</h3><div className="tag-list interactive-tags">{selected.interaction_types.map((item) => <button key={item} onClick={() => applyCatalogFilter("interactions", item, selected.language)}>{item}</button>)}{!selected.interaction_types.length && <p className="muted-empty">No cross-system interactions are tagged.</p>}</div></section></div>
          <RelatedDiagnostics entries={insights?.related_entries ?? []} onSelect={(entry) => void openRelated(entry)} />
        </div>}

        {detailTab === "state" && <div className="detail-section state-section">
          <StateInspector entry={selected} />
          <section className="record-details"><span className="section-kicker">Record provenance</span><h3>Diagnostic evidence</h3><dl><div><dt>Canonical ID</dt><dd>{metadata?.canonical_id ?? selected.id}</dd></div><div><dt>Toolchain</dt><dd>{metadata?.tool_id ?? "-"}</dd></div><div><dt>Introduced</dt><dd>{selected.version_introduced ?? "Not specified"}</dd></div><div><dt>Deprecated</dt><dd>{selected.version_deprecated ?? "Active / not specified"}</dd></div><div><dt>Dataset</dt><dd>{metadata?.provenance?.dataset_version ?? "Local contribution"}</dd></div><div><dt>Updated</dt><dd>{metadata?.updated_at ?? "-"}</dd></div></dl>{metadata?.classifications.length ? <div className="classification-list">{metadata.classifications.map((item) => <span key={item}>{formatLabel(item)}</span>)}</div> : null}</section>
        </div>}
        {selected.source_url && <a className="source-link" href={selected.source_url} target="_blank" rel="noreferrer">Open official documentation</a>}
      </article> : <div className="detail-empty">Select a diagnostic to inspect its cause, likelihood, context, and repair.</div>}
    </section>

    <CommandPalette open={paletteOpen} query={query} results={results} inputRef={paletteInput} onClose={() => setPaletteOpen(false)} onQuery={setQuery} onSelect={selectEntry} onView={changeView} onClear={() => { setFilters(emptyFilters); setQuery(""); }} />
  </main>;
}
