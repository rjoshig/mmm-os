"use client";

import { LayoutDashboard, Layers, LogOut, Settings, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ThemeToggle } from "@/components/theme-toggle";
import { api } from "@/lib/api/client";
import { clearSession, getStoredPrincipal } from "@/lib/session";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/settings", label: "Settings", icon: Settings },
];

// Admin-only nav; the backend still enforces Permission.ADMIN on every call.
const ADMIN_NAV = [{ href: "/admin", label: "Admin", icon: ShieldCheck }];

/** App shell sidebar: brand, primary nav, signed-in user + logout, theme toggle. */
export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const principal = getStoredPrincipal();
  const nav = principal?.role === "admin" ? [...NAV, ...ADMIN_NAV] : NAV;

  async function onLogout() {
    try {
      await api.logout();
    } catch {
      /* best-effort; clear locally regardless */
    }
    clearSession();
    router.replace("/login");
  }

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-border bg-card">
      <div className="flex items-center gap-2 px-4 py-4">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Layers className="h-4 w-4" />
        </span>
        <div className="leading-tight">
          <div className="text-sm font-semibold">mmm-os</div>
          <div className="text-[11px] text-muted-foreground">Data Ingestion</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-2 py-2">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center justify-between gap-2 border-t border-border px-3 py-3">
        <div className="min-w-0">
          <div className="truncate text-xs font-medium" title={principal?.email}>
            {principal?.email ?? "—"}
          </div>
          <div className="text-[11px] capitalize text-muted-foreground">
            {principal?.role ?? "guest"}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <button
            type="button"
            aria-label="Sign out"
            onClick={onLogout}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
