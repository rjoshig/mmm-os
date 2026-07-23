"use client";

import { Building2, ChevronsUpDown } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import type { Customer } from "@/lib/api/types";
import { getActiveTenantId, setSelectedWorkspaceId } from "@/lib/tenant";

/**
 * Workspace (customer) switcher for the sidebar. Every screen scopes its data to
 * the active workspace via getActiveTenantId(); switching sets the selection and
 * hard-reloads so all data refetches for the new customer.
 */
export function WorkspaceSwitcher() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [active, setActive] = useState<string>("");

  useEffect(() => {
    setActive(getActiveTenantId());
    api
      .listCustomers()
      .then(setCustomers)
      .catch(() => setCustomers([]));
  }, []);

  function onSelect(id: string) {
    if (id === active) return;
    setSelectedWorkspaceId(id);
    // Hard reload so every screen refetches against the new workspace.
    window.location.assign("/");
  }

  const current = customers.find((c) => c.id === active);

  return (
    <div className="px-2 pb-2">
      <div className="relative">
        <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground">
          <Building2 className="h-3.5 w-3.5" />
        </span>
        <select
          value={active}
          onChange={(e) => onSelect(e.target.value)}
          aria-label="Active workspace"
          className="h-9 w-full appearance-none rounded-md border border-border bg-background pl-7 pr-7 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {current === undefined ? (
            <option value={active}>Default workspace</option>
          ) : null}
          {customers.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
              {c.tier === "enterprise" ? " ★" : ""}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground">
          <ChevronsUpDown className="h-3.5 w-3.5" />
        </span>
      </div>
    </div>
  );
}
