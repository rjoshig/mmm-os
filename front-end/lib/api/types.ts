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
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
}

export interface JobEventRead {
  stage: string;
  status: string;
  message: string | null;
  duration_ms: number | null;
  created_at: string;
}

export interface JobDetail {
  job: JobRead;
  filename: string | null;
  events: JobEventRead[];
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

export interface SheetRowsResponse {
  columns: string[];
  rows: Record<string, unknown>[];
}

export interface IngestResponse {
  file: FileRead;
  job: JobRead;
}

export interface ProcessResponse {
  job: JobRead;
  sheets: SheetRead[];
}

// --- Auth ---
export interface PrincipalRead {
  user_id: Uuid;
  tenant_id: Uuid;
  email: string;
  role: string;
}

export interface LoginResponse {
  token: string;
  principal: PrincipalRead;
}

// --- Canonical schema ---
export interface CanonicalFieldRead {
  name: string;
  type: string;
  required: boolean;
  kind: "dimension" | "measure" | "factor";
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

// --- Governance / admin (Phase 8 / 08.1) ---
export interface UserRead {
  id: Uuid;
  email: string;
  display_name: string | null;
  role: string;
  status: string;
}

export interface AuditEntryRead {
  id: Uuid;
  actor_user_id: Uuid | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: string;
}

export interface AccessReviewRow {
  user_id: Uuid;
  email: string;
  role: string;
  permissions: string[];
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

export interface BulkReviewResponse {
  updated: FlagRead[];
}

// --- Tenant reporting settings (Cycle 2) ---
export interface TenantSettings {
  reporting_currency: string;
  reporting_timezone: string;
  fx_rates: Record<string, number>;
}

// --- Sources / connectors (Cycle 3) ---
export interface AvailableConnector {
  key: string;
  is_partner: boolean;
}

export interface ConnectorConfig {
  id: Uuid;
  tenant_id: Uuid;
  connector_key: string;
  name: string;
  account_ids: string[];
  settings: Record<string, unknown>;
  enabled: boolean;
}

export interface SyncRun {
  id: Uuid;
  connector_config_id: Uuid;
  window_start: string;
  window_end: string;
  status: string;
  row_count: number | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface SyncRunListItem {
  run: SyncRun;
  connector_key: string;
  connector_name: string;
}

// --- Output export / MMM contract (Cycle 3) ---
export interface ContractField {
  name: string;
  type: string;
  kind: "dimension" | "measure" | "factor";
}

export interface OutputContract {
  file_id: Uuid;
  filename: string;
  row_count: number;
  columns: ContractField[];
  mapping_config_version: number | null;
  rule_set_version: number | null;
  sample: Record<string, unknown>[];
}

export interface LineageSource {
  source_sheet: string | null;
  row_count: number;
}

export interface OutputLineage {
  file_id: Uuid;
  filename: string;
  output_row_count: number;
  mapping_config_version: number | null;
  rule_set_version: number | null;
  sources: LineageSource[];
}

// --- Config library / authorship (Phase 13) ---
export interface ConfigLibraryItem {
  kind: "mapping" | "rule_set";
  key: string;
  name: string;
  layer: string;
  latest_version: number;
  version_count: number;
  updated_at: string;
  created_by_email: string | null;
}

export interface ConfigVersionItem {
  version: number;
  layer: string;
  created_at: string;
  created_by_email: string | null;
  summary: string;
}

export interface GenerateOutputResponse {
  job_id: Uuid;
  file_id: Uuid;
  sheet_id: Uuid;
  rows_written: number;
  mapping_config_version: number | null;
  rule_set_version: number | null;
}

export interface OutputRowRead {
  id: Uuid;
  source_file_id: Uuid | null;
  source_sheet: string | null;
  source_row: number | null;
  mapping_config_version: number | null;
  rule_set_version: number | null;
  ingested_at: string | null;
  data: Record<string, unknown>;
}

export interface OutputListResponse {
  file_id: Uuid;
  filename: string;
  rows: OutputRowRead[];
}

export interface SheetPipelineRead {
  sheet_id: Uuid;
  sheet_name: string | null;
  needs_mapping: boolean;
  mapping_config_version: number | null;
  missing_required: string[];
  flag_count: number;
  blocked: boolean;
  output_rows_written: number | null;
  rule_set_version: number | null;
}

export interface PipelineRunResponse {
  file_id: Uuid;
  job_id: Uuid;
  rows_written: number;
  sheets: SheetPipelineRead[];
}

export interface SheetPipelineStatus {
  sheet_id: Uuid;
  sheet_name: string | null;
  has_mapping: boolean;
  has_rule_set: boolean;
}

export interface FilePipelineStatus {
  file_id: Uuid;
  validated: boolean;
  blocking_open: number;
  has_output: boolean;
  sheets: SheetPipelineStatus[];
}
