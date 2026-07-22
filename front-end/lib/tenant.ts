// Tenant / auth seam (interim).
//
// Phase 6 ships before Phase 00.5 (Authentication), so there is no real session
// yet. Every API call is tenant-scoped (CC-1), so the UI needs an active
// tenant_id from somewhere. This module is that single seam: when 00.5 lands it
// replaces `getActiveTenantId()`'s source with the authenticated session's
// tenant — WITHOUT any screen changing, since screens only call this function.

// A stable dev tenant UUID so a single browser session sees a consistent tenant.
// Override with NEXT_PUBLIC_DEV_TENANT_ID. (SQLite dev DB does not enforce FKs,
// so any UUID works for local exploration.)
const DEFAULT_DEV_TENANT = "00000000-0000-4000-8000-000000000001";

/** Return the active tenant id. Replaced by a real session in Phase 00.5. */
export function getActiveTenantId(): string {
  return process.env.NEXT_PUBLIC_DEV_TENANT_ID || DEFAULT_DEV_TENANT;
}
