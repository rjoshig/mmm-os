// Typed API client for the mmm-os backend.
//
// - Base URL from NEXT_PUBLIC_API_BASE_URL (dev default: http://localhost:8000).
// - Every path is tenant-scoped via the tenant seam (lib/tenant.ts, CC-1).
// - Errors surface as ApiError; 503 (LLM disabled) is detectable via `.status`.

import { getActiveTenantId } from "@/lib/tenant";
import type {
  AcceptResponse,
  AutoMapResponse,
  FileDetail,
  FileListItem,
  IngestResponse,
  PreviewResponse,
  ProcessResponse,
  RuleSetRead,
  RuleSpecIn,
  SaveMappingResponse,
  SheetDetail,
  SuggestionRead,
  SuggestMappingResponse,
  ValidateResponse,
} from "@/lib/api/types";

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
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
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
  // --- Files / jobs (reads) ---
  listFiles: () => request<FileListItem[]>(tenantPath("/files")),
  getFile: (fileId: string) => request<FileDetail>(tenantPath(`/files/${fileId}`)),
  getSheet: (sheetId: string) => request<SheetDetail>(tenantPath(`/sheets/${sheetId}`)),

  // --- Ingest / process ---
  uploadFile: (file: File) => {
    const form = new FormData();
    form.append("upload", file);
    return request<IngestResponse>(tenantPath("/files"), { method: "POST", body: form });
  },
  processFile: (fileId: string) =>
    request<ProcessResponse>(tenantPath(`/files/${fileId}/process`), { method: "POST" }),

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

  // --- Validation ---
  validateJob: (jobId: string, rows: Record<string, unknown>[]) =>
    request<ValidateResponse>(tenantPath(`/jobs/${jobId}/validate`), {
      method: "POST",
      body: JSON.stringify({ rows }),
    }),
  reviewFlag: (flagId: string, status: string) =>
    request<unknown>(tenantPath(`/validation-flags/${flagId}/review`), {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
};
