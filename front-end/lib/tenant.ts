// Tenant / workspace resolution (Phase 00.5 + Cycle 7).
//
// A "tenant" is surfaced as a Customer/Workspace. The active workspace is, in order:
//   1. an explicit user selection (the workspace switcher, stored in localStorage),
//   2. the authenticated session principal's tenant,
//   3. a dev fallback so the UI renders before login / with auth disabled.
// Screens only ever call `getActiveTenantId()`, so this is the single place tenant
// resolution lives.

import { getStoredPrincipal } from "@/lib/session";

// Fallback dev tenant UUID (used only when nothing else resolves). Override with
// NEXT_PUBLIC_DEV_TENANT_ID.
const DEFAULT_DEV_TENANT = "00000000-0000-4000-8000-000000000001";

const ACTIVE_KEY = "active_workspace_id";

/** Return the user-selected active workspace id, if any (client-only). */
export function getSelectedWorkspaceId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACTIVE_KEY);
}

/** Select the active workspace (persisted). Pass null to clear the selection. */
export function setSelectedWorkspaceId(id: string | null): void {
  if (typeof window === "undefined") return;
  if (id) window.localStorage.setItem(ACTIVE_KEY, id);
  else window.localStorage.removeItem(ACTIVE_KEY);
}

/** Return the active tenant/workspace id — selection, then session, then dev fallback. */
export function getActiveTenantId(): string {
  return (
    getSelectedWorkspaceId() ||
    getStoredPrincipal()?.tenant_id ||
    process.env.NEXT_PUBLIC_DEV_TENANT_ID ||
    DEFAULT_DEV_TENANT
  );
}
