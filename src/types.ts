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
