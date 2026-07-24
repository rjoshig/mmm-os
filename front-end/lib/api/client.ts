// Typed API client for the mmm-os backend.
//
// - Base URL from NEXT_PUBLIC_API_BASE_URL (dev default: http://localhost:8000).
// - Every path is tenant-scoped via the tenant seam (lib/tenant.ts, CC-1).
// - Errors surface as ApiError; 503 (LLM disabled) is detectable via `.status`.

import type {
  AcceptResponse,
  AccessReviewRow,
  Assignment,
  AuditEntryRead,
  AutoMapResponse,
  AvailableConnector,
  BulkReviewResponse,
  Comment,
  ConfigLibraryItem,
  ConfigVersionItem,
  ConnectorConfig,
  ConnectorCredentialStatus,
  FeedTemplate,
  FeedTemplatePreview,
  FixedField,
  Customer,
  Notification,
  JobDetail,
  JobListItem,
  SyncRun,
  SyncRunListItem,
  CanonicalFieldsResponse,
  FileDetail,
  FileListItem,
  FlagRead,
  GenerateOutputResponse,
  IngestResponse,
  LoginResponse,
  OutputContract,
  OutputLineage,
  OutputListResponse,
  FilePipelineStatus,
  PipelineRunResponse,
  PreviewResponse,
  PrincipalRead,
  ProcessResponse,
  RetentionPolicy,
  RuleSetRead,
  RuleSpecIn,
  SaveMappingResponse,
  SheetDetail,
  SheetRowsResponse,
  SuggestionRead,
  SuggestMappingResponse,
  TenantSettings,
  UserRead,
  ValidateResponse,
  // Cycle 5 (phases 14–21)
  ActiveJobsResponse,
  CloneResponse,
  CustomerCloneResponse,
  DashboardResponse,
  ExportToDestinationResponse,
  HarmonizationSuggestionsResponse,
  IoProfile,
  OutputStatsResponse,
  PublishStackResponse,
  ResolvedSchemaResponse,
  RoleMatrixResponse,
  SandboxRunResponse,
  SchemaExtension,
  StackDetail,
  StackRead,
} from "@/lib/api/types";
import { clearSession, getToken } from "@/lib/session";
import { getActiveTenantId } from "@/lib/tenant";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }

  /** True when the backend reports the LLM is disabled (Phase 5 returns 503). */
  get isLlmDisabled(): boolean {
    return this.status === 503;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.body && !(init.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(0, `Cannot reach the API at ${BASE_URL}. Is the backend running?`);
  }

  if (!response.ok) {
    // An expired/invalid session on a non-login call: clear it and send the user
    // back to login (handled by the app shell on the next render).
    if (response.status === 401 && !path.startsWith("/api/v1/auth/")) {
      clearSession();
      if (typeof window !== "undefined") window.location.assign("/login");
    }
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body; keep statusText */
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function tenantPath(suffix: string): string {
  return `/api/v1/tenants/${getActiveTenantId()}${suffix}`;
}

export const api = {
  // --- Customers / workspaces (platform-level, not tenant-scoped; Cycle 7) ---
  listCustomers: () => request<Customer[]>("/api/v1/customers"),
  createCustomer: (input: { name: string; slug?: string; tier?: string; region?: string }) =>
    request<Customer>("/api/v1/customers", { method: "POST", body: JSON.stringify(input) }),
  setCustomerIsolation: (id: string, input: { mode: "pool" | "silo"; database_url?: string }) =>
    request<Customer>(`/api/v1/customers/${id}/isolation`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),

  // --- Auth (not tenant-scoped) ---
  login: (email: string, password: string) =>
    request<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<PrincipalRead>("/api/v1/auth/me"),
  logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),

  // --- Canonical schema (not tenant-scoped) ---
  canonicalFields: () => request<CanonicalFieldsResponse>("/api/v1/canonical/fields"),

  // --- Files / jobs (reads) ---
  listFiles: () => request<FileListItem[]>(tenantPath("/files")),
  getFile: (fileId: string) => request<FileDetail>(tenantPath(`/files/${fileId}`)),
  getSheet: (sheetId: string) => request<SheetDetail>(tenantPath(`/sheets/${sheetId}`)),
  getSheetRows: (sheetId: string, limit = 20) =>
    request<SheetRowsResponse>(tenantPath(`/sheets/${sheetId}/rows?limit=${limit}`)),

  // --- Ingest / process ---
  uploadFile: (file: File) => {
    const form = new FormData();
    form.append("upload", file);
    return request<IngestResponse>(tenantPath("/files"), { method: "POST", body: form });
  },
  processFile: (fileId: string) =>
    request<ProcessResponse>(tenantPath(`/files/${fileId}/process`), { method: "POST" }),
  // Ingest a large file the backend can reach by path (landing zone) — no upload.
  ingestByPath: (path: string) =>
    request<IngestResponse>(tenantPath("/files/ingest-by-path"), {
      method: "POST",
      body: JSON.stringify({ path }),
    }),

  // --- Mapping ---
  saveMapping: (sheetId: string, name: string, mapping: Record<string, string | null>) =>
    request<SaveMappingResponse>(tenantPath(`/sheets/${sheetId}/mapping`), {
      method: "POST",
      body: JSON.stringify({ name, mapping }),
    }),
  autoMap: (sheetId: string) =>
    request<AutoMapResponse>(tenantPath(`/sheets/${sheetId}/automap`), { method: "POST" }),

  // --- AI suggestions ---
  suggestMapping: (sheetId: string) =>
    request<SuggestMappingResponse>(tenantPath(`/sheets/${sheetId}/suggest-mapping`), {
      method: "POST",
    }),
  suggestTransforms: (sheetId: string, remediate = false) =>
    request<SuggestMappingResponse>(
      tenantPath(`/sheets/${sheetId}/suggest-transforms?remediate=${remediate}`),
      { method: "POST" }
    ),
  listSuggestions: (sheetId: string) =>
    request<SuggestionRead[]>(tenantPath(`/sheets/${sheetId}/suggestions`)),
  acceptSuggestion: (suggestionId: string) =>
    request<AcceptResponse>(tenantPath(`/suggestions/${suggestionId}/accept`), { method: "POST" }),
  rejectSuggestion: (suggestionId: string) =>
    request<SuggestionRead>(tenantPath(`/suggestions/${suggestionId}/reject`), { method: "POST" }),

  // --- Transform ---
  previewRules: (rows: Record<string, unknown>[], rules: RuleSpecIn[]) =>
    request<PreviewResponse>(tenantPath("/transform/preview"), {
      method: "POST",
      body: JSON.stringify({ rows, rules }),
    }),
  saveRuleSet: (name: string, rules: RuleSpecIn[]) =>
    request<RuleSetRead>(tenantPath("/rule-sets"), {
      method: "POST",
      body: JSON.stringify({ name, rules }),
    }),
  getRuleSet: (name: string) =>
    request<RuleSetRead>(tenantPath(`/rule-sets/${encodeURIComponent(name)}`)),
  // Signature-scoped rule set for a sheet: rules are keyed by the sheet's column
  // signature (not sheet_id), so they are reused by any file with identical headers
  // ("configure once, reuse forever"). The backend derives the name server-side.
  getSheetRuleSet: (sheetId: string) =>
    request<RuleSetRead>(tenantPath(`/sheets/${sheetId}/rule-set`)),
  saveSheetRuleSet: (sheetId: string, rules: RuleSpecIn[], draft = false) =>
    request<RuleSetRead>(tenantPath(`/sheets/${sheetId}/rule-set`), {
      method: "POST",
      body: JSON.stringify({ rules, draft }),
    }),

  // --- Validation ---
  getFlags: (jobId: string) => request<FlagRead[]>(tenantPath(`/jobs/${jobId}/validation-flags`)),
  validateJob: (jobId: string, rows: Record<string, unknown>[]) =>
    request<ValidateResponse>(tenantPath(`/jobs/${jobId}/validate`), {
      method: "POST",
      body: JSON.stringify({ rows }),
    }),
  // Validates a sheet's real data after applying its saved mapping + rule set
  // server-side (rather than raw, un-mapped columns).
  validateSheet: (jobId: string, sheetId: string) =>
    request<ValidateResponse>(tenantPath(`/jobs/${jobId}/sheets/${sheetId}/validate`), {
      method: "POST",
    }),

  // --- Output generation (final pipeline step) ---
  generateOutput: (jobId: string, sheetId: string, force = false) =>
    request<GenerateOutputResponse>(
      tenantPath(`/jobs/${jobId}/sheets/${sheetId}/generate-output?force=${force}`),
      { method: "POST" }
    ),
  getOutput: (jobId: string, limit = 50) =>
    request<OutputListResponse>(tenantPath(`/jobs/${jobId}/output?limit=${limit}`)),
  getOutputContract: (jobId: string) =>
    request<OutputContract>(tenantPath(`/jobs/${jobId}/output/contract`)),
  getOutputLineage: (jobId: string) => request<OutputLineage>(tenantPath(`/jobs/${jobId}/lineage`)),
  // Fetch the CSV export as a Blob (carries the auth header, unlike a plain link).
  fetchOutputCsv: async (jobId: string): Promise<Blob> => {
    const token = getToken();
    const response = await fetch(`${BASE_URL}${tenantPath(`/jobs/${jobId}/output.csv`)}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new ApiError(response.status, "Could not export CSV.");
    return response.blob();
  },

  // --- Full pipeline (map → transform → validate → output, one call) ---
  runPipeline: (fileId: string) =>
    request<PipelineRunResponse>(tenantPath(`/files/${fileId}/run-pipeline`), {
      method: "POST",
    }),
  getPipelineStatus: (fileId: string) =>
    request<FilePipelineStatus>(tenantPath(`/files/${fileId}/pipeline-status`)),
  reviewFlag: (flagId: string, status: string) =>
    request<FlagRead>(tenantPath(`/validation-flags/${flagId}/review`), {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
  // Apply one review decision to a whole cluster of a job's flags in one call.
  bulkReviewFlags: (jobId: string, flagIds: string[], status: string) =>
    request<BulkReviewResponse>(tenantPath(`/jobs/${jobId}/validation-flags/bulk-review`), {
      method: "POST",
      body: JSON.stringify({ flag_ids: flagIds, status }),
    }),

  // --- Assignments / review queue (Phase 13.4) ---
  createAssignment: (input: {
    target_type: string;
    target_id: string;
    assignee_user_id: string;
    note?: string;
  }) =>
    request<Assignment>(tenantPath("/assignments"), {
      method: "POST",
      body: JSON.stringify(input),
    }),
  listAssignments: (assignee?: string) =>
    request<Assignment[]>(tenantPath(`/assignments${assignee ? `?assignee=${assignee}` : ""}`)),
  resolveAssignment: (id: string) =>
    request<Assignment>(tenantPath(`/assignments/${id}/resolve`), { method: "POST" }),

  // --- Comments + notifications (Phase 13.5) ---
  listComments: (targetType: string, targetId: string) =>
    request<Comment[]>(tenantPath(`/comments?target_type=${targetType}&target_id=${targetId}`)),
  createComment: (input: {
    target_type: string;
    target_id: string;
    body: string;
    mentions?: string[];
  }) =>
    request<Comment>(tenantPath("/comments"), {
      method: "POST",
      body: JSON.stringify(input),
    }),
  listNotifications: (recipient?: string, unreadOnly = false) => {
    const q = new URLSearchParams();
    if (recipient) q.set("recipient", recipient);
    if (unreadOnly) q.set("unread_only", "true");
    return request<Notification[]>(tenantPath(`/notifications?${q.toString()}`));
  },
  markNotificationRead: (id: string) =>
    request<Notification>(tenantPath(`/notifications/${id}/read`), { method: "POST" }),

  // --- Config library / authorship (Phase 13) ---
  getConfigLibrary: () => request<{ items: ConfigLibraryItem[] }>(tenantPath("/config-library")),
  getConfigVersions: (kind: string, key: string) =>
    request<{ kind: string; key: string; versions: ConfigVersionItem[] }>(
      tenantPath(`/config-library/versions?kind=${kind}&key=${encodeURIComponent(key)}`)
    ),
  publishConfig: (kind: string, key: string, version: number, statusValue = "published") =>
    request<ConfigVersionItem>(tenantPath("/config-library/publish"), {
      method: "POST",
      body: JSON.stringify({ kind, key, version, status: statusValue }),
    }),

  // --- Tenant reporting settings (Cycle 2) ---
  getSettings: () => request<TenantSettings>(tenantPath("/settings")),
  updateSettings: (patch: Partial<TenantSettings>) =>
    request<TenantSettings>(tenantPath("/settings"), {
      method: "PUT",
      body: JSON.stringify(patch),
    }),

  // --- Sources / connectors (Cycle 3; admin-gated on the backend) ---
  availableConnectors: () =>
    request<{ connectors: AvailableConnector[] }>("/api/v1/connectors/available"),
  listConnectorConfigs: () => request<ConnectorConfig[]>(tenantPath("/connector-configs")),
  createConnectorConfig: (input: {
    connector_key: string;
    name: string;
    account_ids: string[];
    settings?: Record<string, unknown>;
  }) =>
    request<ConnectorConfig>(tenantPath("/connector-configs"), {
      method: "POST",
      body: JSON.stringify({ settings: {}, ...input }),
    }),
  triggerSync: (configId: string) =>
    request<SyncRun>(tenantPath(`/connector-configs/${configId}/sync`), { method: "POST" }),
  setConnectorCredential: (
    configId: string,
    input: { token: string; scopes?: string[] | null; expires_at?: string | null }
  ) =>
    request<ConnectorCredentialStatus>(tenantPath(`/connector-configs/${configId}/credential`), {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  deleteConnectorCredential: (configId: string) =>
    request<void>(tenantPath(`/connector-configs/${configId}/credential`), {
      method: "DELETE",
    }),
  setConnectorSchedule: (configId: string, intervalMinutes: number | null) =>
    request<ConnectorConfig>(tenantPath(`/connector-configs/${configId}/schedule`), {
      method: "PUT",
      body: JSON.stringify({ interval_minutes: intervalMinutes }),
    }),
  runDueSyncs: () =>
    request<{ ran: SyncRun[] }>(tenantPath("/scheduler/run-due"), { method: "POST" }),
  listSyncRuns: (configId: string) =>
    request<SyncRun[]>(tenantPath(`/connector-configs/${configId}/sync-runs`)),
  listAllSyncRuns: (limit = 100) =>
    request<SyncRunListItem[]>(tenantPath(`/sync-runs?limit=${limit}`)),

  // --- Feed templates (per-customer recurring file layouts; Slice 7.4) ---
  listFeedTemplates: () => request<FeedTemplate[]>(tenantPath("/feed-templates")),
  createFeedTemplate: (input: {
    name: string;
    fmt: string;
    delimiter?: string | null;
    has_header?: boolean;
    fixed_fields?: FixedField[];
    expected_columns?: string[];
    filename_glob?: string | null;
  }) =>
    request<FeedTemplate>(tenantPath("/feed-templates"), {
      method: "POST",
      body: JSON.stringify(input),
    }),
  deleteFeedTemplate: (templateId: string) =>
    request<void>(tenantPath(`/feed-templates/${templateId}`), { method: "DELETE" }),
  previewFeedTemplate: (templateId: string, file: File) => {
    const form = new FormData();
    form.append("upload", file);
    return request<FeedTemplatePreview>(tenantPath(`/feed-templates/${templateId}/preview`), {
      method: "POST",
      body: form,
    });
  },

  // --- Runs / jobs history (Cycle 3) ---
  listJobs: () => request<JobListItem[]>(tenantPath("/jobs")),
  getJob: (jobId: string) => request<JobDetail>(tenantPath(`/jobs/${jobId}`)),

  // --- Governance / admin (admin-only; backend enforces Permission.ADMIN) ---
  listUsers: () => request<UserRead[]>(tenantPath("/users")),
  getRetentionPolicy: () => request<RetentionPolicy>(tenantPath("/retention/policy")),
  runRetention: () =>
    request<{ purged: Record<string, number> }>(tenantPath("/retention/run"), { method: "POST" }),
  auditLog: (limit = 100) => request<AuditEntryRead[]>(tenantPath(`/audit-log?limit=${limit}`)),
  accessReview: () => request<AccessReviewRow[]>(tenantPath("/access-review")),

  // ==========================================================================
  // Cycle 5 — Usability, Reuse & Model-Readiness (phases 14–21)
  // ==========================================================================

  // --- Phase 17: output statistics ---
  getOutputStats: (jobId: string) =>
    request<OutputStatsResponse>(tenantPath(`/jobs/${jobId}/output/stats`)),

  // --- Phase 16: Stacks (Gold layer) ---
  listStacks: () => request<StackRead[]>(tenantPath("/stacks")),
  getStack: (stackId: string) => request<StackDetail>(tenantPath(`/stacks/${stackId}`)),
  createStack: (input: {
    name: string;
    description?: string | null;
    source_job_ids: string[];
    harmonization?: {
      field_map?: Record<string, string>;
      value_map?: Record<string, Record<string, string>>;
    };
    grain?: string | null;
  }) =>
    request<StackDetail>(tenantPath("/stacks"), {
      method: "POST",
      body: JSON.stringify(input),
    }),
  publishStack: (stackId: string, force = false) =>
    request<PublishStackResponse>(tenantPath(`/stacks/${stackId}/publish?force=${force}`), {
      method: "POST",
    }),
  harmonizationSuggestions: (sourceJobIds: string[], field = "channel") =>
    request<HarmonizationSuggestionsResponse>(
      tenantPath(`/stacks/harmonization-suggestions?field=${field}`),
      { method: "POST", body: JSON.stringify(sourceJobIds) }
    ),
  fetchStackCsv: async (stackId: string): Promise<Blob> => {
    const token = getToken();
    const response = await fetch(`${BASE_URL}${tenantPath(`/stacks/${stackId}.csv`)}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new ApiError(response.status, "Could not export the stack CSV.");
    return response.blob();
  },

  // --- Phase 21: tenant schema extensions ---
  listSchemaExtensions: () => request<SchemaExtension[]>(tenantPath("/schema-extensions")),
  createSchemaExtension: (input: {
    kind: string;
    name: string;
    data_type?: string;
    taxonomy_ref?: string | null;
    validation?: string | null;
  }) =>
    request<SchemaExtension>(tenantPath("/schema-extensions"), {
      method: "POST",
      body: JSON.stringify(input),
    }),
  deleteSchemaExtension: (extId: string) =>
    request<void>(tenantPath(`/schema-extensions/${extId}`), { method: "DELETE" }),
  getResolvedSchema: () => request<ResolvedSchemaResponse>(tenantPath("/resolved-schema")),

  // --- Phase 14: config-driven I/O ---
  getIoProfile: () => request<IoProfile>(tenantPath("/io-profile")),
  updateIoProfile: (patch: Partial<Record<keyof IoProfile, string>>) =>
    request<IoProfile>(tenantPath("/io-profile"), {
      method: "PUT",
      body: JSON.stringify({
        input_path: patch.input,
        output_path: patch.output,
        temp_path: patch.temp,
        archive_path: patch.archive,
        error_path: patch.error,
        reject_path: patch.reject,
      }),
    }),
  exportToDestination: (jobId: string) =>
    request<ExportToDestinationResponse>(tenantPath(`/jobs/${jobId}/export-to-destination`), {
      method: "POST",
    }),

  // --- Phase 18: sandbox ---
  sandboxRun: (sheetId: string, sample = 20) =>
    request<SandboxRunResponse>(tenantPath(`/sheets/${sheetId}/sandbox-run?sample=${sample}`), {
      method: "POST",
    }),

  // --- Phase 19: RBAC role management ---
  getRoleMatrix: () => request<RoleMatrixResponse>("/api/v1/rbac/roles"),
  setUserRole: (userId: string, role: string) =>
    request<UserRead>(tenantPath(`/users/${userId}/role`), {
      method: "PUT",
      body: JSON.stringify({ role }),
    }),

  // --- Phase 15: universal clone / duplicate ---
  cloneRuleSet: (id: string, input: { new_name?: string; target_tenant_id?: string }) =>
    request<CloneResponse>(tenantPath(`/rule-sets/${id}/clone`), {
      method: "POST",
      body: JSON.stringify(input),
    }),
  cloneMappingConfig: (id: string, input: { new_name?: string; target_tenant_id?: string }) =>
    request<CloneResponse>(tenantPath(`/mapping-configs/${id}/clone`), {
      method: "POST",
      body: JSON.stringify(input),
    }),
  cloneFeedTemplate: (id: string, input: { new_name?: string; target_tenant_id?: string }) =>
    request<CloneResponse>(tenantPath(`/feed-templates/${id}/clone`), {
      method: "POST",
      body: JSON.stringify(input),
    }),
  cloneConnectorConfig: (id: string, input: { new_name?: string; target_tenant_id?: string }) =>
    request<CloneResponse>(tenantPath(`/connector-configs/${id}/clone`), {
      method: "POST",
      body: JSON.stringify(input),
    }),
  cloneStack: (id: string, input: { new_name?: string }) =>
    request<CloneResponse>(tenantPath(`/stacks/${id}/clone`), {
      method: "POST",
      body: JSON.stringify(input),
    }),
  cloneCustomerConfigs: (targetTenantId: string) =>
    request<CustomerCloneResponse>(tenantPath(`/clone-configs-to/${targetTenantId}`), {
      method: "POST",
    }),

  // --- Phase 20: dashboard + live monitoring ---
  getDashboard: () => request<DashboardResponse>(tenantPath("/dashboard")),
  getActiveJobs: () => request<ActiveJobsResponse>(tenantPath("/active-jobs")),
};
