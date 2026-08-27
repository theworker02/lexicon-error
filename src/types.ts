export type ErrorEntry = {
  id: string;
  language: string;
  code: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  bad_example: string;
  good_example: string;
  version_introduced?: string | null;
  version_deprecated?: string | null;
  source_url?: string | null;
  tier: number;
  frequency: "Common" | "Uncommon" | "Rare" | "Situational";
  situational_context: string[];
  interaction_types: string[];
  related_errors: string[];
  state_snapshot?: StateSnapshot | null;
  score?: number;
};

export type StateSnapshot = { event: string; frames: string[]; variables: Array<{ name: string; value: string; status: string }> };

export type MatrixCell = { language: string; category: string; frequency: string; count: number };

export type Filters = {
  languages: string[];
  categories: string[];
  severities: string[];
  frequencies: string[];
  interactions: string[];
};

export type Facets = {
  languages: string[];
  categories: string[];
  severities: string[];
  frequencies: string[];
  interactions: string[];
  total: number;
};

export type CoverageQuality = { verified: number; explanations: number; examples: number; fixes: number; sources: number; versions: number; relationships: number };

export type CoverageProfile = { language_id: string; language: string; records: number; target: number; progress: number; tools: number; quality: CoverageQuality; tier: "Comprehensive" | "Broad" | "Developing" | "Experimental" };

export type DetectionResult = { normalized_message: string; redacted: boolean; matches: Array<{ entry_id: string; canonical_id: string; language: string; tool_id: string; code: string; confidence: number; confidence_label: string }> };

export type ErrorMetadata = {
  entry_id: string;
  canonical_id: string;
  language_id: string;
  tool_id: string;
  classifications: string[];
  normalized_severity: string;
  canonical_message: string;
  summary: string;
  when_it_occurs: string[];
  causes: Array<{ id?: string; likelihood?: string }>;
  fixes: unknown[];
  prevention?: string | null;
  explanation_of_example?: string | null;
  tags: string[];
  aliases: string[];
  fingerprint: string;
  signature_kind: string;
  signature_pattern?: string | null;
  platforms: string[];
  provenance: { source_type?: string; source_authority?: string; review_state?: string; dataset_version?: string } | null;
  verification_status: string;
  updated_at: string;
};

export type CountBucket = { label: string; count: number };

export type RelatedEntry = Pick<ErrorEntry, "id" | "language" | "code" | "title" | "category" | "severity" | "frequency">;

export type EntryInsights = {
  language_total: number;
  category_total: number;
  frequency_distribution: CountBucket[];
  category_distribution: CountBucket[];
  related_entries: RelatedEntry[];
};
