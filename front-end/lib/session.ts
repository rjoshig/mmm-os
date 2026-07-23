// Client-side session storage for the Review UI (Phase 00.5).
//
// The backend issues a Bearer token on login; we keep it (and the principal) in
// localStorage. This replaces the interim tenant seam — the active tenant now
// comes from the authenticated principal, not a hardcoded default.

export interface StoredPrincipal {
  user_id: string;
  tenant_id: string;
  email: string;
  role: string;
}

const TOKEN_KEY = "mmm_os_token";
const PRINCIPAL_KEY = "mmm_os_principal";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getStoredPrincipal(): StoredPrincipal | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(PRINCIPAL_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredPrincipal;
  } catch {
    return null;
  }
}

export function setSession(token: string, principal: StoredPrincipal): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(PRINCIPAL_KEY, JSON.stringify(principal));
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(PRINCIPAL_KEY);
}
