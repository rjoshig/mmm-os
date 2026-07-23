"use client";

import { ScrollText, ShieldCheck, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { EmptyState, ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api/client";
import type { AccessReviewRow, AuditEntryRead, UserRead } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { getStoredPrincipal } from "@/lib/session";
import { cn } from "@/lib/utils";

type Tab = "users" | "audit" | "access";

const TABS: { id: Tab; label: string; icon: typeof Users }[] = [
  { id: "users", label: "Users", icon: Users },
  { id: "audit", label: "Audit log", icon: ScrollText },
  { id: "access", label: "Access review", icon: ShieldCheck },
];

/**
 * Admin console (Phase 8 / 08.1). Admin-gated in the sidebar and re-checked here;
 * the backend still enforces Permission.ADMIN on every call, so a non-admin who
 * reaches this route sees a permission notice rather than data.
 */
export default function AdminPage() {
  const principal = getStoredPrincipal();
  const [tab, setTab] = useState<Tab>("users");

  if (principal && principal.role !== "admin") {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Governance" title="Admin" />
        <EmptyState
          icon={<ShieldCheck className="h-6 w-6" />}
          title="Admin access required"
          description="Your account does not have the admin role for this tenant."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Governance"
        title="Admin"
        description="Manage users, review the tenant audit trail, and run an access review (RBAC, Phase 8 / 08.1)."
      />

      <div className="flex gap-1 border-b border-border">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={cn(
              "-mb-px flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
              tab === id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "users" ? <UsersTab /> : null}
      {tab === "audit" ? <AuditTab /> : null}
      {tab === "access" ? <AccessTab /> : null}
    </div>
  );
}

/** Load helper: runs `fetcher`, tracking data + error the same way across tabs. */
function useAdminData<T>(fetcher: () => Promise<T>, fallback: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await fetcher());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fallback);
    }
    // fetcher is a stable per-tab closure; intentionally not a dep.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fallback]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, error };
}

function UsersTab() {
  const { data, error } = useAdminData<UserRead[]>(() => api.listUsers(), "Failed to load users.");

  if (error) return <ErrorBanner message={error} />;
  if (data === null) return <Loading label="Loading users…" />;
  if (data.length === 0)
    return (
      <EmptyState
        icon={<Users className="h-6 w-6" />}
        title="No users"
        description="This tenant has no users yet."
      />
    );

  return (
    <Table>
      <THead>
        <TR>
          <TH>Email</TH>
          <TH>Name</TH>
          <TH>Role</TH>
          <TH>Status</TH>
        </TR>
      </THead>
      <tbody>
        {data.map((u) => (
          <TR key={u.id} className="hover:bg-muted/40">
            <TD className="font-medium text-foreground">{u.email}</TD>
            <TD className="text-muted-foreground">{u.display_name ?? "—"}</TD>
            <TD>
              <Badge variant={u.role === "admin" ? "default" : "secondary"}>{u.role}</Badge>
            </TD>
            <TD>
              <Badge variant={statusVariant(u.status)}>{u.status}</Badge>
            </TD>
          </TR>
        ))}
      </tbody>
    </Table>
  );
}

function AuditTab() {
  const { data, error } = useAdminData<AuditEntryRead[]>(
    () => api.auditLog(100),
    "Failed to load the audit log."
  );

  if (error) return <ErrorBanner message={error} />;
  if (data === null) return <Loading label="Loading audit log…" />;
  if (data.length === 0)
    return (
      <EmptyState
        icon={<ScrollText className="h-6 w-6" />}
        title="No audit entries"
        description="Admin and review actions are recorded here as they happen."
      />
    );

  return (
    <Table>
      <THead>
        <TR>
          <TH>When</TH>
          <TH>Action</TH>
          <TH>Target</TH>
          <TH>Actor</TH>
        </TR>
      </THead>
      <tbody>
        {data.map((e) => (
          <TR key={e.id} className="hover:bg-muted/40">
            <TD className="whitespace-nowrap text-muted-foreground">
              {formatDateTime(e.created_at)}
            </TD>
            <TD className="font-medium text-foreground">{e.action}</TD>
            <TD className="text-muted-foreground">
              {e.target_type ? `${e.target_type}${e.target_id ? `:${e.target_id}` : ""}` : "—"}
            </TD>
            <TD className="mono text-xs text-muted-foreground">{e.actor_user_id ?? "system"}</TD>
          </TR>
        ))}
      </tbody>
    </Table>
  );
}

function AccessTab() {
  const { data, error } = useAdminData<AccessReviewRow[]>(
    () => api.accessReview(),
    "Failed to run the access review."
  );

  if (error) return <ErrorBanner message={error} />;
  if (data === null) return <Loading label="Running access review…" />;
  if (data.length === 0)
    return (
      <EmptyState
        icon={<ShieldCheck className="h-6 w-6" />}
        title="Nothing to review"
        description="No users are provisioned for this tenant."
      />
    );

  return (
    <Table>
      <THead>
        <TR>
          <TH>Email</TH>
          <TH>Role</TH>
          <TH>Effective permissions</TH>
        </TR>
      </THead>
      <tbody>
        {data.map((r) => (
          <TR key={r.user_id} className="hover:bg-muted/40">
            <TD className="font-medium text-foreground">{r.email}</TD>
            <TD>
              <Badge variant={r.role === "admin" ? "default" : "secondary"}>{r.role}</Badge>
            </TD>
            <TD>
              <div className="flex flex-wrap gap-1">
                {r.permissions.length === 0 ? (
                  <span className="text-muted-foreground">none</span>
                ) : (
                  r.permissions.map((p) => (
                    <Badge key={p} variant="outline">
                      {p}
                    </Badge>
                  ))
                )}
              </div>
            </TD>
          </TR>
        ))}
      </tbody>
    </Table>
  );
}
