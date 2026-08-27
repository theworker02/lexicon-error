import { invoke } from "@tauri-apps/api/core";
import type { CoverageProfile, DetectionResult, EntryInsights, ErrorEntry, ErrorMetadata, Facets, Filters, MatrixCell } from "../types";

export function searchEntries(query: string, filters: Filters): Promise<ErrorEntry[]> {
  return invoke("search_entries", { query, filters });
}

export function getFacets(): Promise<Facets> {
  return invoke("get_facets");
}

export function getMatrix(filters: Filters): Promise<MatrixCell[]> {
  return invoke("get_matrix", { filters });
}

export function getCoverage(): Promise<CoverageProfile[]> {
  return invoke("get_coverage");
}

export function detectError(message: string): Promise<DetectionResult> {
  return invoke("detect_error", { message });
}

export function getErrorMetadata(entryId: string): Promise<ErrorMetadata> {
  return invoke("get_error_metadata", { entryId });
}

export function getEntryInsights(entryId: string): Promise<EntryInsights> {
  return invoke("get_entry_insights", { entryId });
}

export function exportDatabase(destination: string): Promise<string> {
  return invoke("export_database", { destination });
}

export function importContributions(source: string): Promise<number> {
  return invoke("import_contributions", { source });
}
