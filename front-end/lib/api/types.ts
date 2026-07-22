// TypeScript mirrors of the backend Pydantic schemas (src/mmm_os/schemas/*).
// Kept in sync by hand; the backend is the source of truth.

export type Uuid = string;

export interface FileRead {
  id: Uuid;
  tenant_id: Uuid;
  filename: string;
  content_type: string | null;
  byte_size: number | null;
  checksum_sha256: string | null;
  storage_uri: string | null;
  created_at: string;
}

export interface JobRead {
  id: Uuid;
  tenant_id: Uuid;
  file_id: Uuid | null;
  status: string;
  created_at: string;
}

export interface ColumnStructure {
  index: number;
  name: string;
  type: string;
  date_format: string | null;
}

export interface SheetRead {
  id: Uuid;
  file_id: Uuid;
  sheet_name: string | null;
  sheet_index: number;
  header_row_index: number | null;
  status: string;
  columns: ColumnStructure[];
}

export interface FileListItem {
  file: FileRead;
  latest_job_status: string | null;
  sheet_count: number;
  needs_review_sheets: number;
}

export interface FileDetail {
  file: FileRead;
  latest_job: JobRead | null;
  sheets: SheetRead[];
}

export interface ProfileRead {
  id: Uuid;
  sheet_id: Uuid;
  row_count: number | null;
  column_stats: { columns?: ColumnProfile[] };
}

export interface ColumnProfile {
  name: string;
  index?: number;
  type?: string;
  null_rate?: number;
  null_count?: number;
  distinct_count?: number;
  distinct_capped?: boolean;
  sample_values?: (string | null)[];
  min?: unknown;
  max?: unknown;
  [key: string]: unknown;
}

export interface SheetDetail {
  sheet: SheetRead;
  profile: ProfileRead | null;
}

export interface IngestResponse {
  file: FileRead;
  job: JobRead;
}

export interface ProcessResponse {
  job: JobRead;
  sheets: SheetRead[];
}

// --- Canonical schema ---
export interface CanonicalFieldRead {
  name: string;
  type: string;
  required: boolean;
  kind: "dimension" | "measure";
  taxonomy: string | null;
}

export interface CanonicalFieldsResponse {
  version: number;
  fields: CanonicalFieldRead[];
  min_measures_required: number;
}

// --- Mapping ---
export interface MappedColumnRead {
  source_name: string;
  canonical_field: string;
}

export interface MappingValidation {
  mapped: MappedColumnRead[];
  ignored: string[];
  invalid: string[];
  missing_required: string[];
  is_complete: boolean;
}

export interface MappingConfigRead {
  id: Uuid;
  tenant_id: Uuid;
  name: string;
  file_signature: string;
  version: number;
  layer: string;
  mapping: Record<string, string | null>;
}

export interface SaveMappingResponse {
  config: MappingConfigRead;
  validation: MappingValidation;
}

export interface AutoMapResponse {
  signature: string;
  matched: boolean;
  mapping: Record<string, string | null>;
  validation: MappingValidation | null;
}

// --- AI ---
export interface SuggestionRead {
  id: Uuid;
  tenant_id: Uuid;
  kind: string;
  payload: Record<string, unknown>;
  confidence: number | null;
  rationale: string | null;
  state: string;
}

export interface SuggestMappingResponse {
  suggestions: SuggestionRead[];
}

export interface AcceptResponse {
  suggestion: SuggestionRead;
  mapping_config_version: number | null;
}

// --- Transform ---
export interface RuleSpecIn {
  target_field?: string;
  operation: string;
  params?: Record<string, unknown>;
  condition?: Record<string, unknown> | null;
  order?: number;
  layer?: string;
}

export interface PreviewResponse {
  before: Record<string, unknown>[];
  after: Record<string, unknown>[];
}

export interface RuleSetRead {
  id: Uuid;
  tenant_id: Uuid;
  name: string;
  version: number;
  layer: string;
  rules: RuleSpecIn[];
}

// --- Validation ---
export interface FlagRead {
  id: Uuid;
  job_id: Uuid;
  severity: string;
  description: string;
  location: Record<string, unknown>;
  review_status: string;
  resolved_by: Uuid | null;
  resolved_at: string | null;
}

export interface ValidateResponse {
  blocked: boolean;
  flags: FlagRead[];
}
