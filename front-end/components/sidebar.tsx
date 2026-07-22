"use client";

import { LayoutDashboard, Layers } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/theme-toggle";
import { getActiveTenantId } from "@/lib/tenant";
import { cn } from "@/lib/utils";

const NAV = [{ href: "/", label: "Dashboard", icon: LayoutDashboard }];

/** App shell sidebar: brand, primary nav, tenant indicator + theme toggle. */
export function Sidebar() {
  const pathname = usePathname();
  const tenant = getActiveTenantId();

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
        {NAV.map(({ href, label, icon: Icon }) => {
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

      <div className="flex items-center justify-between border-t border-border px-3 py-3">
        <div className="min-w-0">
          <div className="text-[11px] text-muted-foreground">Tenant</div>
          <div className="truncate font-mono text-[11px]" title={tenant}>
            {tenant.slice(0, 8)}…
          </div>
        </div>
        <ThemeToggle />
      </div>
    </aside>
  );
}
