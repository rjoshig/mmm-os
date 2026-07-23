"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { getToken } from "@/lib/session";

// Mirrors the backend's AUTH_ENABLED flag (root .env). Keep the two in sync:
// when the backend requires auth, gate the UI too; when it doesn't, skip the
// redirect so the dashboard is reachable without logging in.
const AUTH_ENABLED = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";

/**
 * App chrome + auth guard. Unauthenticated users are sent to /login; the login
 * route renders without the sidebar. The token check is client-side only (the
 * backend is the real authority — it rejects unauthenticated calls when
 * AUTH_ENABLED=true, and the API client redirects here on a 401).
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLogin = pathname === "/login";
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (AUTH_ENABLED && !isLogin && !getToken()) {
      router.replace("/login");
      return;
    }
    setChecked(true);
  }, [isLogin, pathname, router]);

  if (isLogin) {
    return (
      <main className="min-h-screen">
        <div className="mx-auto max-w-7xl px-6 py-5">{children}</div>
      </main>
    );
  }

  return (
    <div className="flex">
      <Sidebar />
      <main className="h-screen flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl px-6 py-5">{checked ? children : null}</div>
      </main>
    </div>
  );
}
