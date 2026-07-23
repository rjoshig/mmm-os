// Tenant resolution (Phase 00.5).
//
// The active tenant comes from the authenticated session principal (set at login,
// stored in localStorage). Before login — or if auth is disabled on the backend —
// it falls back to a dev default so the UI still renders. Screens only ever call
// `getActiveTenantId()`, so this is the single place tenant resolution lives.

import { getStoredPrincipal } from "@/lib/session";

// Fallback dev tenant UUID (used only when no session is present). Override with
// NEXT_PUBLIC_DEV_TENANT_ID.
const DEFAULT_DEV_TENANT = "00000000-0000-4000-8000-000000000001";

/** Return the active tenant id — the session's tenant, or a dev fallback. */
export function getActiveTenantId(): string {
  return (
    getStoredPrincipal()?.tenant_id || process.env.NEXT_PUBLIC_DEV_TENANT_ID || DEFAULT_DEV_TENANT
  );
}
