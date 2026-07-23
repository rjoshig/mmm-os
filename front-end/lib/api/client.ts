// Typed API client for the mmm-os backend.
//
// - Base URL from NEXT_PUBLIC_API_BASE_URL (dev default: http://localhost:8000).
// - Every path is tenant-scoped via the tenant seam (lib/tenant.ts, CC-1).
// - Errors surface as ApiError; 503 (LLM disabled) is detectable via `.status`.

import type {
  AcceptResponse,
  AccessReviewRow,
  AuditEntryRead,
  AutoMapResponse,
  AvailableConnector,
  BulkReviewResponse,
  ConnectorConfig,
  SyncRun,
  CanonicalFieldsResponse,
  FileDetail,
  FileListItem,
  FlagRead,
  GenerateOutputResponse,
  IngestResponse,
  LoginResponse,
  OutputListResponse,
  FilePipelineStatus,
  PipelineRunResponse,
  PreviewResponse,
  PrincipalRead,
  ProcessResponse,
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
  saveSheetRuleSet: (sheetId: string, rules: RuleSpecIn[]) =>
    request<RuleSetRead>(tenantPath(`/sheets/${sheetId}/rule-set`), {
      method: "POST",
      body: JSON.stringify({ rules }),
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
  listSyncRuns: (configId: string) =>
    request<SyncRun[]>(tenantPath(`/connector-configs/${configId}/sync-runs`)),

  // --- Governance / admin (admin-only; backend enforces Permission.ADMIN) ---
  listUsers: () => request<UserRead[]>(tenantPath("/users")),
  auditLog: (limit = 100) => request<AuditEntryRead[]>(tenantPath(`/audit-log?limit=${limit}`)),
  accessReview: () => request<AccessReviewRow[]>(tenantPath("/access-review")),
};
